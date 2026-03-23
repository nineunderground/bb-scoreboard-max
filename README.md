# bb-scoreboard-max

Blood Bowl scoreboard running on ESP32-S3 with a **TFT touchscreen** — no external buttons, LEDs, or OLED needed. Everything is on the screen.

## Hardware

- **ESP32-S3 DevKitC-1 v1.1**
- **4.0" ST7796S TFT display** (480×320, SPI) with **XPT2046 resistive touch**
- Optional: small speaker (30Ω) through a 100Ω resistor for sound effects

This project targets a 4.0" SPI TFT module based on the ST7796S controller, with optional XPT2046 resistive touch. Typical seller labels are "4.0 inch SPI TFT ST7796S" or similar variants mentioning 480x320 resolution.

## TFT + Touch Pinout

Module connector pinout:

    Number  Pin Label    Description
    ------  ---------    -----------------------------------------------------
    1       VCC          5V/3.3V power input
    2       GND          Ground
    3       CS           LCD chip select, active low
    4       RESET        LCD reset, active low
    5       DC/RS        LCD command/data selection
    6       SDI(MOSI)    LCD SPI write data
    7       SCK          LCD SPI clock
    8       LED          Backlight control, active high
    9       SDO(MISO)    LCD SPI read data, optional if reads are unused
    10      T_CLK        Touch SPI clock
    11      T_CS         Touch chip select, active low
    12      T_DIN        Touch SPI input
    13      T_DO         Touch SPI output
    14      T_IRQ        Touch interrupt, low when touched

Notes:

- `T_CLK`, `T_DIN`, and `T_DO` are normally shared with the LCD SPI bus clock/data lines.
- If you do not need touch, you can leave the touch pins disconnected.
- If you do not control backlight brightness in software, tie `LED` to `3V3` for always-on backlight.
- In this project, `T_IRQ` is not used.

## Project layout

    bb-scoreboard-max/
    ├── .gitignore
    ├── main.py            # MicroPython app
    ├── ili9341.py         # TFT display driver (download separately)
    ├── xpt2046.py         # Touch controller driver (download separately)
    ├── requirements.txt   # Host-side tools (esptool, mpremote)
    └── README.md

## Wiring

### TFT + Touch module → ESP32-S3

The TFT and touch controller share the same SPI bus (SPI2/HSPI) with separate CS pins.

    TFT module pin    ESP32-S3 pin   Purpose
    --------------    -------------   -------
    VCC               3V3             Power
    GND               GND             Ground
    CS                GPIO10          TFT chip select
    RESET             GPIO8           TFT reset
    DC (A0)           GPIO9           Data/command
    SDI (MOSI)        GPIO11          SPI data in
    SCK               GPIO12          SPI clock
    LED (BL)          GPIO14          Backlight (some modules)
    SDO (MISO)        GPIO13          SPI data out

    T_CS              GPIO7           Touch chip select
    T_CLK             (shared SCK)    SPI clock (same bus)
    T_DIN             (shared MOSI)   SPI data in (same bus)
    T_DO              (shared MISO)   SPI data out (same bus)
    T_IRQ             not connected   Touch interrupt (optional)

Step-by-step wiring:

1. Connect `VCC` on the display to ESP32-S3 `3V3`.
2. Connect `GND` on the display to ESP32-S3 `GND`.
3. Connect `CS` to `GPIO10`.
4. Connect `RESET` to `GPIO8`.
5. Connect `DC/RS` to `GPIO9`.
6. Connect `SDI(MOSI)` to `GPIO11`.
7. Connect `SCK` to `GPIO12`.
8. Connect `LED` to `GPIO14` if you want software backlight control. If not, connect `LED` directly to `3V3`.
9. Connect `SDO(MISO)` to `GPIO13`.
10. Connect `T_CLK` to the same ESP32-S3 pin as `SCK`, which is `GPIO12`.
11. Connect `T_CS` to `GPIO7`.
12. Connect `T_DIN` to the same ESP32-S3 pin as `SDI(MOSI)`, which is `GPIO11`.
13. Connect `T_DO` to the same ESP32-S3 pin as `SDO(MISO)`, which is `GPIO13`.
14. Leave `T_IRQ` disconnected, because `main.py` does not use it.

Quick wiring summary:

    Display pin   ESP32-S3 pin
    -----------   ------------
    VCC           3V3
    GND           GND
    CS            GPIO10
    RESET         GPIO8
    DC/RS         GPIO9
    SDI(MOSI)     GPIO11
    SCK           GPIO12
    LED           GPIO14 or 3V3
    SDO(MISO)     GPIO13
    T_CLK         GPIO12
    T_CS          GPIO7
    T_DIN         GPIO11
    T_DO          GPIO13
    T_IRQ         not connected

### Speaker (optional)

    Speaker red  → 100Ω resistor → GPIO15
    Speaker black → GND

ASCII wiring diagram:

    TFT+Touch Module                     ESP32-S3 DevKit
    ----------------                     ----------------
    [ VCC     ] --------------------------> [ 3V3    ]
    [ GND     ] --------------------------> [ GND    ]
    [ CS      ] --------------------------> [ GPIO10 ]
    [ RESET   ] --------------------------> [ GPIO8  ]
    [ DC/A0   ] --------------------------> [ GPIO9  ]
    [ SDI     ] --------------------------> [ GPIO11 ]
    [ SCK     ] --------------------------> [ GPIO12 ]
    [ LED/BL  ] --------------------------> [ GPIO14 ]
    [ SDO     ] --------------------------> [ GPIO13 ]
    [ T_CS    ] --------------------------> [ GPIO7  ]
    [ T_CLK   ] ---- (shared with SCK)
    [ T_DIN   ] ---- (shared with SDI)
    [ T_DO    ] ---- (shared with SDO)

    Speaker                              ESP32-S3 DevKit
    -------                              ----------------
    [ + red  ] --[ 100Ω ]----------------> [ GPIO15 ]
    [ - blk  ] --------------------------> [ GND    ]

## Screen Layout (320×240 landscape)

    ┌──────────────────┬──────────────────┐  0
    │    ▌ HOME        │        AWAY ▌    │  Header (touch to
    │                  │                  │  select active team)
    ├──────────────────┼──────────────────┤  40
    │                  │                  │
    │       0          │        0         │  Score area
    │                  │                  │  (touch to +1)
    │                  │                  │
    ├──────────────────┴──────────────────┤  178
    │  [1][2][3][4] | [5][6][7][8]       │  Turn track
    │               ▲ half-time          │  (touch to advance)
    ├─────────────────────────────────────┤  215
    │            [ RESET ]                │  Reset bar
    └─────────────────────────────────────┘  240

Touch zones:
- **Score area (left/right)** — tap to increase HOME/AWAY score
- **Header (left/right)** — tap to switch active team
- **Turn track** — tap to advance turn (alternates HOME→AWAY→HOME+1)
- **Reset bar** — tap to reset everything

## MicroPython Drivers

You need two driver files not included in this repo (MIT licensed):

### ILI9341 display driver

    wget https://raw.githubusercontent.com/rdagger/micropython-ili9341/master/ili9341.py -O ili9341.py

### XPT2046 touch driver

    wget https://raw.githubusercontent.com/rdagger/micropython-ili9341/master/xpt2046.py -O xpt2046.py

Upload both to the ESP32-S3 alongside `main.py`.

> **Note:** If you use a different ILI9341 driver, the constructor arguments in `main.py` may need adjusting. The code assumes the `rdagger/micropython-ili9341` API.

## Flash and run from Windows

### 1. Create a Python environment

    cd C:\path\to\bb-scoreboard-max
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -U pip
    python -m pip install -r requirements.txt

### 2. Flash MicroPython firmware

Download from: https://micropython.org/download/ESP32_GENERIC_S3/

wget https://micropython.org/resources/firmware/ESP32_GENERIC_S3-20251209-v1.27.0.bin -o ESP32_GENERIC_S3-20251209-v1.27.0.bin

Check serial port with:
Get-WmiObject Win32_PnPEntity | Where-Object { $_.Name -like "*SERIAL*" } | Select-Object Name

    python -m esptool --chip esp32s3 --port COM4 erase-flash
    python -m esptool --chip esp32s3 --port COM4 --baud 460800 write-flash -z 0 ESP32_GENERIC_S3-20251209-v1.27.0.bin

### 3. Upload files to the board

    mpremote connect COM4 sleep 1 fs cp .\ili9341.py :ili9341.py
    mpremote connect COM4 sleep 1 fs cp .\xpt2046.py :xpt2046.py
    mpremote connect COM4 sleep 1 fs cp .\main.py :main.py

### 4. Reset and test

    mpremote connect COM4 reset
    mpremote connect COM4 repl

You should see the startup screen, then the scoreboard.

### 5. Iterate

    mpremote connect COM4 sleep 1 fs cp .\main.py :main.py
    mpremote connect COM4 reset

## Sound effects

If a speaker is wired to GPIO15:
- **Touchdown** — ascending 4-note fanfare when score increases
- **Turn change** — double beep
- **Team switch** — single short beep
- **Reset** — descending 3-note tone

No speaker? Everything works silently.

## Differences from bb-scoreboard

| Feature | bb-scoreboard | bb-scoreboard-max |
|---------|--------------|-------------------|
| Display | 0.96" OLED (128×64) | 2.8" TFT (320×240) |
| Input | 4 physical buttons | Touchscreen |
| Score display | Single digit (0-9) | Two digits (0-99) |
| Team indicator | Traffic light LEDs | On-screen highlight |
| Color | Monochrome | Full color (65K) |
| Sound | None | Optional speaker |
| Modules needed | OLED + button + LED | Just the TFT |

## Notes

- If touch coordinates seem flipped or mirrored, adjust `x_min`, `x_max`, `y_min`, `y_max` and `r` in the XPT2046 constructor.
- If the screen is blank, check the backlight pin — some modules need it driven high.
- If colors look wrong (red↔blue swapped), the module may use BGR instead of RGB — check the driver init options.
- The `r=1` parameter sets landscape rotation. Use `r=0` for portrait.
