"""
bb-scoreboard-max — Blood Bowl scoreboard on ESP32-WROOM-32 DevKit + SPI TFT touchscreen.

Hardware:
  - ESP32 DevKit V1 / ESP-WROOM-32 development board with CP2102 USB-UART
  - SPI TFT touchscreen module with XPT2046 touch controller

This file is wired for a classic ESP32-WROOM-32 development board.
It keeps the existing 320x240 UI layout and the current `ili9341`-style
display driver API. If your specific 4.0" ST7796S module needs a different
display driver module or a 480x320 layout, adjust that separately.
"""

from machine import Pin, SPI, PWM
from time import sleep, ticks_ms, ticks_diff

import ili9341
import xpt2046

# ---------------------------------------------------------------------------
# Pin assignments — classic ESP32-WROOM-32 DevKit V1
# ---------------------------------------------------------------------------
# The TFT and touch controller share the same SPI bus.
# These pins follow the common VSPI mapping on ESP32 DevKit V1 boards.
TFT_MOSI = 23
TFT_MISO = 19
TFT_SCLK = 18
TFT_CS = 5
TFT_DC = 27
TFT_RST = 26
TFT_BL = 25  # backlight control, optional

# Separate chip-select for the touch controller on the shared SPI bus.
TOUCH_CS = 33

# ---------------------------------------------------------------------------
# Display and touch setup
# ---------------------------------------------------------------------------
spi = SPI(
    2,
    baudrate=40_000_000,
    polarity=0,
    phase=0,
    sck=Pin(TFT_SCLK),
    mosi=Pin(TFT_MOSI),
    miso=Pin(TFT_MISO),
)

tft = ili9341.ILI9341(
    spi,
    cs=Pin(TFT_CS, Pin.OUT),
    dc=Pin(TFT_DC, Pin.OUT),
    rst=Pin(TFT_RST, Pin.OUT),
    w=320,
    h=240,
    r=1,
)  # r=1 -> landscape

touch = xpt2046.XPT2046(
    spi,
    cs=Pin(TOUCH_CS, Pin.OUT),
    int_pin=None,
    width=320,
    height=240,
    x_min=200,
    x_max=3900,
    y_min=200,
    y_max=3900,
    r=1,
)

# Optional backlight
try:
    bl = PWM(Pin(TFT_BL), freq=1000, duty=1023)
except Exception:
    bl = None

# ---------------------------------------------------------------------------
# Colors (RGB565)
# ---------------------------------------------------------------------------
BLACK = 0x0000
WHITE = 0xFFFF
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
YELLOW = 0xFFE0
GREY = 0x7BEF
DKGREY = 0x39E7
CYAN = 0x07FF
ORANGE = 0xFD20

# Team colors
HOME_COLOR = RED
HOME_BG = 0x4000  # dark red
AWAY_COLOR = BLUE
AWAY_BG = 0x0010  # dark blue
ACTIVE_MARK = YELLOW
TURN_BG = DKGREY

# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------
TURN_MIN = 1
TURN_MAX = 8
HALF_TURN = 8  # turns per half

home_score = 0
away_score = 0
current_turn = 1
active_team = "HOME"  # HOME or AWAY

# Touch debounce
DEBOUNCE_MS = 300
last_touch_time = 0

# ---------------------------------------------------------------------------
# Layout constants (320x240 landscape)
# ---------------------------------------------------------------------------
HEADER_H = 40
SCORE_Y = 45
SCORE_H = 120
HOME_SCORE_X = 40
AWAY_SCORE_X = 210
DIVIDER_X = 160
TURN_Y = 178
TURN_H = 32
TURN_BOX_W = 32
TURN_START_X = 16
TURN_SPACING = 38
BOTTOM_Y = 215
BOTTOM_H = 25

# Touch zones
ZONE_HOME_SCORE = (0, HEADER_H, DIVIDER_X, TURN_Y)
ZONE_AWAY_SCORE = (DIVIDER_X, HEADER_H, 320, TURN_Y)
ZONE_HOME_HEADER = (0, 0, DIVIDER_X, HEADER_H)
ZONE_AWAY_HEADER = (DIVIDER_X, 0, 320, HEADER_H)
ZONE_TURN = (0, TURN_Y, 320, BOTTOM_Y)
ZONE_RESET = (0, BOTTOM_Y, 320, 240)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def fill_rect(x, y, w, h, color):
    tft.fill_rect(x, y, w, h, color)


def draw_text(text, x, y, color=WHITE, scale=1):
    """Draw text using the built-in 8x8 font."""
    tft.text(text, x, y, color)


def draw_big_number(num, cx, y, color=WHITE):
    """Draw a large score number centered at cx."""
    s = str(num)
    char_w = 8 * 3
    total_w = len(s) * char_w
    start_x = cx - total_w // 2
    for i, ch in enumerate(s):
        bx = start_x + i * char_w
        for dx in range(3):
            for dy in range(3):
                tft.text(ch, bx + dx * 8, y + dy * 8, color)


def draw_huge_number(num, cx, y, color=WHITE):
    """Draw a larger score number using repeated 8x8 glyphs."""
    s = str(num)
    char_w = 8 * 4
    total_w = len(s) * char_w + (len(s) - 1) * 4
    start_x = cx - total_w // 2
    for i, ch in enumerate(s):
        bx = start_x + i * (char_w + 4)
        for dx in range(4):
            for dy in range(4):
                tft.text(ch, bx + dx * 8, y + dy * 8, color)


# ---------------------------------------------------------------------------
# Screen drawing
# ---------------------------------------------------------------------------
def draw_header():
    bg = HOME_BG if active_team == "HOME" else BLACK
    fill_rect(0, 0, DIVIDER_X, HEADER_H, bg)
    tft.text("HOME", 50, 12, HOME_COLOR)
    if active_team == "HOME":
        fill_rect(0, 0, 4, HEADER_H, ACTIVE_MARK)

    bg = AWAY_BG if active_team == "AWAY" else BLACK
    fill_rect(DIVIDER_X, 0, 160, HEADER_H, bg)
    tft.text("AWAY", 220, 12, AWAY_COLOR)
    if active_team == "AWAY":
        fill_rect(316, 0, 4, HEADER_H, ACTIVE_MARK)

    fill_rect(DIVIDER_X - 1, 0, 2, HEADER_H, GREY)


def draw_scores():
    fill_rect(0, HEADER_H, DIVIDER_X, TURN_Y - HEADER_H, BLACK)
    fill_rect(DIVIDER_X, HEADER_H, 160, TURN_Y - HEADER_H, BLACK)
    fill_rect(DIVIDER_X - 1, HEADER_H, 2, TURN_Y - HEADER_H, GREY)

    score_cy = SCORE_Y + 15
    draw_huge_number(home_score, HOME_SCORE_X + 40, score_cy, HOME_COLOR)
    draw_huge_number(away_score, AWAY_SCORE_X + 40, score_cy, AWAY_COLOR)
    tft.text("-", DIVIDER_X - 4, SCORE_Y + 35, GREY)


def draw_turn_track():
    fill_rect(0, TURN_Y, 320, TURN_H + 4, BLACK)

    for t in range(TURN_MIN, TURN_MAX + 1):
        x = TURN_START_X + (t - 1) * TURN_SPACING
        if t == current_turn:
            fill_rect(x, TURN_Y + 2, TURN_BOX_W, TURN_H - 4, ACTIVE_MARK)
            tft.text(str(t), x + 12, TURN_Y + 10, BLACK)
        else:
            fill_rect(x, TURN_Y + 2, TURN_BOX_W, TURN_H - 4, TURN_BG)
            tft.text(str(t), x + 12, TURN_Y + 10, WHITE)

        if t == 4:
            fill_rect(x + TURN_BOX_W + 1, TURN_Y + 8, 2, TURN_H - 16, ORANGE)


def draw_bottom_bar():
    fill_rect(0, BOTTOM_Y, 320, BOTTOM_H, DKGREY)
    tft.text("[ RESET ]", 120, BOTTOM_Y + 8, RED)


def draw_scoreboard():
    draw_header()
    draw_scores()
    draw_turn_track()
    draw_bottom_bar()


# ---------------------------------------------------------------------------
# Touch handling
# ---------------------------------------------------------------------------
def point_in_zone(x, y, zone):
    return zone[0] <= x <= zone[2] and zone[1] <= y <= zone[3]


def handle_touch(tx, ty):
    global home_score, away_score, current_turn, active_team

    if point_in_zone(tx, ty, ZONE_HOME_SCORE):
        home_score = (home_score + 1) % 100
        return True

    if point_in_zone(tx, ty, ZONE_AWAY_SCORE):
        away_score = (away_score + 1) % 100
        return True

    if point_in_zone(tx, ty, ZONE_HOME_HEADER):
        active_team = "HOME"
        return True

    if point_in_zone(tx, ty, ZONE_AWAY_HEADER):
        active_team = "AWAY"
        return True

    if point_in_zone(tx, ty, ZONE_TURN):
        if active_team == "HOME":
            active_team = "AWAY"
        else:
            active_team = "HOME"
            current_turn += 1
            if current_turn > TURN_MAX:
                current_turn = TURN_MIN
        return True

    if point_in_zone(tx, ty, ZONE_RESET):
        home_score = 0
        away_score = 0
        current_turn = 1
        active_team = "HOME"
        return True

    return False


# ---------------------------------------------------------------------------
# Startup animation
# ---------------------------------------------------------------------------
def show_startup():
    tft.fill(BLACK)
    tft.text("BLOOD", 112, 60, RED)
    tft.text("BOWL", 120, 80, RED)
    sleep(0.5)

    tft.text("SCOREBOARD", 88, 110, WHITE)
    tft.text("MAX", 136, 130, YELLOW)
    sleep(0.5)

    tft.text("Touch to begin", 80, 180, GREY)

    for _ in range(100):
        raw = touch.get_touch()
        if raw is not None:
            break
        sleep(0.05)

    tft.fill(BLACK)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
print("bb-scoreboard-max — TFT touchscreen edition")
print("Board: ESP32 DevKit V1 / ESP-WROOM-32 with CP2102")
print("Touch: score areas, headers, turn track, reset bar")

show_startup()
draw_scoreboard()

while True:
    raw = touch.get_touch()

    if raw is not None:
        tx, ty = raw
        now = ticks_ms()
        if ticks_diff(now, last_touch_time) > DEBOUNCE_MS:
            if handle_touch(tx, ty):
                last_touch_time = now
                draw_scoreboard()

    sleep(0.02)
