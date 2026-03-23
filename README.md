# bb-scoreboard-max

Blood Bowl scoreboard for an **ESP32 DevKit V1 / ESP-WROOM-32** board with **CP2102 USB-UART** and an SPI TFT touchscreen. All interaction is on the display.

## Hardware

- **ESP32 DevKit V1** based on **ESP-WROOM-32**
- **CP2102** USB-to-UART bridge on the dev board
- **4.0" SPI TFT display** with **XPT2046 resistive touch**
- Optional but recommended: **ESP32S 30P expansion board** or another breakout method that lets you fan out one GPIO to multiple module pins on the shared SPI bus

Important note:

- The display and touch controller share SPI signals. That means one ESP32 GPIO must fan out to two TFT pins for clock, MOSI, and MISO.
- The expansion board solves the physical wiring problem; it does not change the SPI logic.
- `main.py` is now mapped for the classic ESP32-WROOM-32 DevKit V1 pinout.
- The current app still uses the existing `ili9341.py`-style display driver API and a 320x240 layout. If your exact 4.0" ST7796S module needs a different display driver or 480x320 layout, adjust that separately.

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

- `T_CLK`, `T_DIN`, and `T_DO` are shared with the display SPI bus.
- If you do not need touch, you can leave the touch pins disconnected.
- If you do not control backlight brightness in software, tie `LED` to `3V3` or `VCC` for always-on backlight, depending on your module.
- In this project, `T_IRQ` is not used.

## Project layout

    bb-scoreboard-max/
    ├── .gitignore
    ├── main.py            # MicroPython app
    ├── ili9341.py         # Current display-driver module name expected by main.py
    ├── xpt2046.py         # Touch controller driver
    ├── requirements.txt   # Host-side tools (esptool, mpremote)
    └── README.md

## Wiring

### TFT + Touch module -> ESP32 DevKit V1 / ESP-WROOM-32

The TFT and touch controller share the same SPI bus. On ESP32 DevKit V1, this README uses the common VSPI pins from `main.py`.

    TFT module pin    ESP32 pin   Purpose
    --------------    ---------   -------------------------------------------
    VCC               5V or 3V3   Module power, according to your module spec
    GND               GND         Ground
    CS                GPIO5       TFT chip select
    RESET             GPIO26      TFT reset
    DC/RS             GPIO27      TFT command/data select
    SDI(MOSI)         GPIO23      SPI MOSI
    SCK               GPIO18      SPI clock
    LED               GPIO25      Backlight control
    SDO(MISO)         GPIO19      SPI MISO

    T_CS              GPIO33      Touch chip select
    T_CLK             GPIO18      Shared SPI clock
    T_DIN             GPIO23      Shared SPI MOSI
    T_DO              GPIO19      Shared SPI MISO
    T_IRQ             not connected  Touch interrupt unused by main.py

Step-by-step wiring:

1. Connect `GND` on the display to ESP32 `GND`.
2. Connect `VCC` on the display to ESP32 `5V` if your module accepts 5V input, or to `3V3` if your module is strictly 3.3V.
3. Connect `CS` to `GPIO5`.
4. Connect `RESET` to `GPIO26`.
5. Connect `DC/RS` to `GPIO27`.
6. Connect `LED` to `GPIO25` if you want software backlight control. If not, tie `LED` high according to your module design.
7. Connect `T_CS` to `GPIO33`.
8. Connect ESP32 `GPIO18` to both TFT `SCK` and TFT `T_CLK`.
9. Connect ESP32 `GPIO23` to both TFT `SDI(MOSI)` and TFT `T_DIN`.
10. Connect ESP32 `GPIO19` to both TFT `SDO(MISO)` and TFT `T_DO`.
11. Leave `T_IRQ` disconnected.

Quick wiring summary:

    Display pin   ESP32 pin
    -----------   ---------
    VCC           5V or 3V3
    GND           GND
    CS            GPIO5
    RESET         GPIO26
    DC/RS         GPIO27
    SDI(MOSI)     GPIO23
    SCK           GPIO18
    LED           GPIO25 or tied high
    SDO(MISO)     GPIO19
    T_CLK         GPIO18
    T_CS          GPIO33
    T_DIN         GPIO23
    T_DO          GPIO19
    T_IRQ         not connected

Shared-SPI wiring note:

- If your expansion board gives you duplicated terminals, use those to fan out `GPIO18`, `GPIO23`, and `GPIO19`.
- If it gives only one terminal per GPIO, use a small breadboard, lever connector, Y-split jumper, or a short pigtail splice so one ESP32 signal reaches both TFT pins.

ASCII wiring diagram:

    TFT+Touch Module                     ESP32 DevKit V1
    ----------------                     ----------------
    [ VCC     ] --------------------------> [ 5V or 3V3 ]
    [ GND     ] --------------------------> [ GND       ]
    [ CS      ] --------------------------> [ GPIO5     ]
    [ RESET   ] --------------------------> [ GPIO26    ]
    [ DC/RS   ] --------------------------> [ GPIO27    ]
    [ SDI     ] ---+                      
                   +---------------------> [ GPIO23    ]
    [ T_DIN   ] ---+                      
    [ SCK     ] ---+                      
                   +---------------------> [ GPIO18    ]
    [ T_CLK   ] ---+                      
    [ SDO     ] ---+                      
                   +---------------------> [ GPIO19    ]
    [ T_DO    ] ---+                      
    [ LED     ] --------------------------> [ GPIO25    ]
    [ T_CS    ] --------------------------> [ GPIO33    ]

## Screen Layout

The current `main.py` still uses a **320x240 landscape layout**:

    ┌──────────────────┬──────────────────┐  0
    │    ▌ HOME        │        AWAY ▌    │
    ├──────────────────┼──────────────────┤  40
    │                  │                  │
    │       0          │        0         │
    │                  │                  │
    ├──────────────────┴──────────────────┤  178
    │  [1][2][3][4] | [5][6][7][8]       │
    ├─────────────────────────────────────┤  215
    │            [ RESET ]                │
    └─────────────────────────────────────┘  240

Touch zones:
- **Score area (left/right)** -> increase HOME or AWAY score
- **Header (left/right)** -> select active team
- **Turn track** -> advance turn
- **Reset bar** -> reset everything

## MicroPython Drivers

You need the touch driver plus a display driver module that matches the API used by `main.py`.

### Current display driver module name used by the code

    ili9341.py

The current code imports `ili9341` and calls `ili9341.ILI9341(...)`. If your 4.0" ST7796S module does not work with that driver, replace it with an ST7796S-compatible driver and update `main.py` accordingly.

### XPT2046 touch driver

    wget https://raw.githubusercontent.com/rdagger/micropython-ili9341/master/xpt2046.py -O xpt2046.py

Upload the required driver files alongside `main.py`.

## Flash and run from Windows

### 1. Create a Python environment

    cd C:\path\to\bb-scoreboard-max
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -U pip
    python -m pip install -r requirements.txt

### 2. Install the CP2102 Windows driver

Silicon Labs says the official Virtual COM Port drivers for CP210x devices are on the VCP driver page:

    https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

Open the official page from PowerShell:

    Start-Process "https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers"

After downloading and extracting the Windows driver package, install the INF from an elevated PowerShell session:

    cd $env:USERPROFILE\Downloads
    Get-ChildItem -Recurse -Filter silabser.inf
    pnputil /add-driver .\CP210x_Universal_Windows_Driver\silabser.inf /install

If the extracted folder name differs, use the path returned by `Get-ChildItem`.

Unplug and reconnect the board, then confirm the COM port:

    Get-CimInstance Win32_PnPEntity |
      Where-Object { $_.Name -match "CP210|COM[0-9]+" } |
      Select-Object Name

### 3. Flash MicroPython firmware for classic ESP32

Official download page:

    https://micropython.org/download/ESP32_GENERIC/

As of 2026-03-23, the latest stable `ESP32_GENERIC` release on that page is `v1.27.0`, dated `2025-12-09`.

Example flashing commands:

    python -m esptool --chip esp32 --port COMx erase-flash
    python -m esptool --chip esp32 --port COMx --baud 460800 write-flash -z 0 ESP32_GENERIC-v1.27.0.bin

If flashing fails, hold `BOOT`, tap `EN` or `RESET`, release `BOOT`, and retry.

### 4. Upload files to the board

    mpremote connect COMx sleep 1 fs cp .\ili9341.py :ili9341.py
    mpremote connect COMx sleep 1 fs cp .\xpt2046.py :xpt2046.py
    mpremote connect COMx sleep 1 fs cp .\main.py :main.py

### 5. Reset and test

    mpremote connect COMx reset
    mpremote connect COMx repl

### 6. Iterate

    mpremote connect COMx sleep 1 fs cp .\main.py :main.py
    mpremote connect COMx reset

## Differences from bb-scoreboard

| Feature | bb-scoreboard | bb-scoreboard-max |
|---------|--------------|-------------------|
| Board | ESP32-S3 DevKitC-1 | ESP32 DevKit V1 / ESP-WROOM-32 |
| Display | 0.96" OLED (128x64) | 4.0" SPI TFT touchscreen |
| Input | 4 physical buttons | Touchscreen |
| Score display | Single digit (0-9) | Two digits (0-99) |
| Team indicator | Traffic light LEDs | On-screen highlight |
| Color | Monochrome | Full color |
| Modules needed | OLED + button + LED | TFT + touch |

## Notes

- `main.py` now uses ESP32 classic VSPI-style pins: `GPIO18`, `GPIO19`, `GPIO23`, plus `GPIO5`, `GPIO25`, `GPIO26`, `GPIO27`, and `GPIO33`.
- Avoid `GPIO6` through `GPIO11` on ESP32-WROOM-32 boards because they are used by onboard flash.
- If touch coordinates are mirrored, adjust `x_min`, `x_max`, `y_min`, `y_max`, and `r` in the XPT2046 constructor.
- If the screen stays blank, check power, backlight wiring, and whether your display needs a different driver than the current `ili9341`-compatible API.
