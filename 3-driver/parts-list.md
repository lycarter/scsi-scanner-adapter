# Driver board: schematic-ready parts list

Status: 2026-09-24. This file collects every part decided in `NOTES.md`, so drawing the schematic
is mostly placing parts. **`NOTES.md` holds the reasoning**; this file holds the list. When a
decision changes, update both.

Columns:
- **Tier:** JLC library tier. **B** = basic, **P** = preferred (both carry no loading fee),
  **E** = extended (one loading fee per unique part per order).
- **Fit:** **JLC** = JLC assembles it; **Hand** = owner solders it (LCSC or own stock);
  **DNP** = footprint only.
- Stock was checked on 2026-09-24. Check it again before ordering.

## 1. Power (`blocks/1-power.md`)

| Qty | Function | Part | LCSC | Tier | Fit | Notes |
|---|---|---|---|---|---|---|
| 1 | Bench 5 V terminal | 2-pin 5.08 mm screw terminal (Kangnex WJ500V-5.08-2P) | C8465 | E | Hand | Plus a test loop per pole (any 0.1" loop, hand-soldered) |
| 2 | Bench-input eFuse; TERMPWR switch | TI TPS259470ARPWR | C3662799 | E | JLC | Bench: OVLO 5.73 V, ILIM 2.02 A, UVLO 4.17 V. TERMPWR: OVLO = active-low enable, ILIM 1.22 A, UVLO 4.32 V. Resistors: see the table below |
| 1 | USB/bench ORing (U1) | TI LM66200DRLR | C3235556 | E | JLC | Both channels used |
| 2 | 3.3 V rail; terminator 2.80 V | TI TPS73701DCQR | C56848 | E | JLC | Dividers: 3.3 V = 47 k / 27 k, 2.80 V = 20 k / 15 k, 1 % (0.1 % dropped 2026-09-25; measure 3.3 V at bring-up) |
| 1 | CC detection | onsemi LM393DR2G | C7955 | B | JLC | Supply from 5 V; thresholds 0.661 V rising / 0.649 V falling; outputs drive the TERMPWR enable node |
| 1 | CC threshold reference | CJ431 (TL431-type, ±0.5 %) SOT-23 | C3113 | B | JLC | 2.495 V from 3.3 V through 510 Ω. Check its datasheet is in English |
| 2 | CC input filter caps | 1 µF X5R 25 V 0402 | C52923 | B | JLC | With 10 kΩ, τ = 10 ms |
| 2 | USB-C Rd | 5.1 kΩ 1 % 0402 | C25905 | B | JLC | |
| 1 | Bench-present switch | 2N7002 SOT-23 | C8545 | B | JLC | Pulls the TERMPWR enable node low. Gate fed from the bench eFuse *output* (10 k / 100 k) |
| 1 | TERMPWR disable jumper | 1×2 2.54 mm header + shunt | — | — | Hand | |

## 2. SCSI front end (`blocks/2-scsi-frontend.md`)

| Qty | Function | Part | LCSC | Tier | Fit | Notes |
|---|---|---|---|---|---|---|
| 1 | SCSI connector | 2×25 keyed box header, 2.54 mm (BOOMELE) | C30006 | E | Hand | LCSC MOQ 5. Footprint `IDC-Header_2x25_P2.54mm_Vertical` |
| 1 | Alt SCSI connector | Half-pitch 50-pin female, right angle | — | — | DNP | Not stocked anywhere; owner sources later. TERMPWR = pin 38 |
| 3 | Terminator switches | TI SN74LVTH245APWR | C2652121 | E | JLC | **Only 939 at JLC.** Inputs tied high, `/OE` = enable |
| 18 | Terminator resistors | 110 Ω 1 % 0402 (FOJAN) | C2909312 | E | JLC | No no-fee 110 Ω exists; 100 Ω would sit at SCSI-2's current limit |
| 1 | Terminator on/off | 2-position DIP switch, SMD (SHOU HAN) | C6331180 | E | JLC | DIP 1 = default, DIP 2 = firmware may override (see `USAGE.md`) |
| 18 | SCSI ESD | H5VUD5BB SOD-523, 0.3 pF | C20615820 | P | JLC | At the connector |
| 1 | TERMPWR ESD | SMF6.0A SOD-123FL | C19077499 | P | JLC | |
| 14 | SCSI drivers (open-drain) | onsemi FDV301N SOT-23 | C15310 | E | JLC | DB0–7, DBP, ATN, ACK, SEL, BSY, RST. GPIO high = asserted. Fallback: 4 × SN74LVTH125PWR (C7042), see NOTES "SCSI drivers" |
| 14 | Driver gate series R | 100 Ω 1 % 0402 | C25076 | B | JLC | Edge-rate tuning on the bench (0 Ω or larger) |
| 14 | Driver gate pull-down | 4.7 kΩ 1 % 0402 | C25900 | B | JLC | Keeps lines released with the board off or the MCU in reset. ≤ 8.2 kΩ required by RP2350-E9 (was 10 kΩ) |
| 14 | Driver gate cap | 22 pF C0G 0402 | C1555 | B | DNP | Fit if the bus-edge kick on an idle gate exceeds ~0.4 V (bench check) |
| 18 | SCSI receivers | **Nexperia** 74LVC1G17GW,125 SOT-353 | C426705 | E | JLC | Nexperia only (other vendors' limits differ). 3.3 V. Fallback: 3 × Nexperia 74LVC14APW (C6066 / -Q100 C548122) |
| 18 | Receiver decoupling | 100 nF X7R 0402 | C307331 | B | JLC | One per 1G17 |
| 20 | LA tap series R | 100 Ω 1 % 0402 | C25076 | B | JLC | At each 1G17 output (18) and marker GPIO (2); the receivers are the Schmitt buffers, so no second bank |
| 1 | LA header | 2×16 2.54 mm pin header | C124382 | E | Hand | Pinout matches Digital Discovery (to do) |

## 3. RP2350B and support (`blocks/3-mcu-support.md`)

| Qty | Function | Part | LCSC | Tier | Fit | Notes |
|---|---|---|---|---|---|---|
| 1 | MCU | Raspberry Pi RP2350B, QFN-80 | C42415655 | E | JLC | 4,296 at JLC |
| 1 | Core-regulator inductor | Abracon AOTA-B201610S3R3-101-T, 3.3 µH | C42411119 | E | JLC | Polarity mark on the footprint |
| 3 | Regulator caps | 4.7 µF X5R 10 V 0402 | C23733 | B | JLC | Fallback 0603 C19666 if DC bias is a problem |
| 1 | VREG_AVDD filter R | 33 Ω 1 % 0402 | C25105 | B | JLC | |
| 13 | Decoupling | 100 nF X7R 0402 | C307331 | B | JLC | IOVDD ×8, DVDD ×3, ADC_AVDD, USB_OTP/QSPI shared, + flash |
| 1 | 3.3 V bulk | 10 µF X5R 0805 | C15850 | B | JLC | |
| 1 | QSPI flash | Winbond W25Q128JVSIQ, 16 MB | C97521 | B | JLC | |
| 1 | PSRAM | AP Memory APS6404L-3SQR-SN, 8 MB | C5333729 | E | JLC | CS1 = GPIO 47. 100 nF + 1 µF (C52923) decoupling |
| 2 | 10 kΩ pull-ups | 10 kΩ 0402 | C25744 | B | JLC | PSRAM CS1 fitted; QSPI_SS DNP |
| 1 | 12 MHz crystal | Abracon ABM8-272-T3 | C20625731 | E | JLC | Same part ×3 on the board (see USB) |
| 2 | Crystal load caps | 15 pF C0G 0402 | C1548 | B | JLC | |
| 3 | 1 kΩ | 1 kΩ 1 % 0402 | C11702 | B | JLC | Crystal series, BOOTSEL, RUN |
| 2 | BOOTSEL, RUN buttons | Owner's through-hole tact switches | — | — | Hand | Size to check (6 × 6 mm?) |
| 1 | microSD socket | SHOU HAN TF PUSH | C393941 | E | JLC | Card detect → expander |
| 1 | I²C expander | TI TCA9555PWR | C465732 | E | JLC | INT to a test point + DNP 0 Ω |
| — | SWD | Tag-Connect TC2030-IDC footprint (pads + clip holes, no part) | — | — | — | 1 VCC, 2 SWDIO, 3 RUN, 4 SWCLK, 5 GND, 6 NC. Owner buys a TC2030-IDC cable + ARM20-CTX adapter for the J-Link EDU |
| 4 | LEDs | KENTO KT-0603R red (C2286), or KT-0805Y yellow (C2296) where a second color helps | C2286 | B | JLC | TERMPWR enable (3.3 V, 1 k), TERMPWR present (on TERMPWR, 6.8 k, ≤ 0.5 mA), LED1/LED2 on the expander (1 k). The basic green needs Vf up to 3.1 V: not on 3.3 V |

## 4. USB path (`blocks/4-usb.md`)

| Qty | Function | Part | LCSC | Tier | Fit | Notes |
|---|---|---|---|---|---|---|
| 1 | USB-C receptacle | Owner's own; footprint HRO TYPE-C-31-M-12 | (C165948) | — | Hand | 16-pin USB 2.0 |
| 1 | USB hub | WCH CH334P | C5373042 | E | JLC | External 3.3 V mode; reset pulled up (expander optional) |
| 1 | Hub crystal | ABM8-272-T3 | C20625731 | E | JLC | Load caps DNP (internal ~16 pF) |
| 1 | HS USB bridge | **FTDI FT232HL-REEL (LQFP-48)** | C51997 | E | JLC | $9.36. Same pinout as the QFN; the QFN (C82158) is out of stock |
| 1 | FT232H config EEPROM | Microchip 93LC56BT-I/OT, SOT-23-6 | C190271 | E | JLC | Required. Program over USB after assembly |
| 1 | FT232H crystal | ABM8-272-T3 + 2 × 15 pF | C20625731, C1548 | E, B | JLC | Accepted 2026-09-24; see NOTES |
| 2 | RP2350 USB series R | 27 Ω 1 % 0603 | C25190 | P | JLC | Close to the RP2350 |
| 2 | USB D± ESD | H5VUD5BB | C20615820 | P | JLC | |
| 2 | CC ESD | H7VL10B DFN1006 | C20615787 | P | JLC | |
| 1 | VBUS ESD | SMF6.0A | C19077499 | P | JLC | |
| 1 | Bench-terminal TVS | SMF15A | C19077509 | P | DNP | Footprint only |

## Resistors and small passives added 2026-09-25

Values and reasoning: NOTES "Resistor and small-part values". All 1 % 0402, no loading fee.
Rows above that already cover a part (gate 100 Ω, LA 100 Ω, PSRAM 10 k, …) aren't repeated.

| Qty | Value | LCSC | Tier | Where |
|---|---|---|---|---|
| 1 | 47 kΩ | C25792 | B | 3.3 V LDO R1 |
| 1 | 27 kΩ | C25771 | P | 3.3 V LDO R2 |
| 1 | 20 kΩ | C25765 | B | 2.80 V LDO R1 |
| 2 | 15 kΩ | C25756 | P | 2.80 V LDO R2; TERMPWR eFuse UVLO bottom |
| 1 | 39 kΩ | C25783 | P | TERMPWR eFuse UVLO top |
| 1 | 510 kΩ | C11616 | P | Bench eFuse string R1 (only ~8.5k in stock; fine at our volume) |
| 1 | 56 kΩ | C25796 | P | Bench eFuse string R2 |
| 1 | 150 kΩ | C25755 | P | Bench eFuse string R3 |
| 1 | 1.5 kΩ | C25867 | B | Bench eFuse R_ILM (with 150 Ω) |
| 1 | 150 Ω | C25082 | P | Bench eFuse R_ILM |
| 1 | 2.4 kΩ | C25882 | P | TERMPWR eFuse R_ILM (with 330 Ω) |
| 1 | 330 Ω | C25104 | B | TERMPWR eFuse R_ILM |
| 13 | 10 kΩ | C25744 | B | Enable-node pull-up; CC filters ×2; CC reference top (with 3.3 k); bench-FET gate series; SDIO pull-ups ×5; FT232H RESET#, hub reset, expander INT |
| 1 | 3.3 kΩ | C25890 | B | CC reference top (10 k + 3.3 k = 13.3 k) |
| 3 | 4.7 kΩ | C25900 | B | CC reference bottom; I²C SDA/SCL |
| 1 | 1 MΩ | C26083 | B | CC hysteresis |
| 1 | 510 Ω | C25123 | B | CJ431 bias |
| 1 | 22 kΩ | C25768 | B | TERMPWR_OK divider top |
| 1 | 33 kΩ | C25779 | B | TERMPWR_OK divider bottom |
| 1 | 6.8 kΩ | C25917 | P | TERMPWR-present LED |
| 1 | 100 kΩ | C25741 | B | Bench-FET gate pull-down |
| 3 | 1 kΩ | C11702 | B | 3.3 V LEDs |
| 2 | 2.2 nF X7R 50 V 0402 (capacitor) | C1531 | P | eFuse dVdt, bench and TERMPWR (~5.5 ms ramp) |
| 0 (2 DNP) | 0402 pad, ~1 nF if fitted | — | — | eFuse ITIMER, open by default |
| 11 | 0 Ω | C17168 | B | FT1248 rework links: 5 fitted (GPIO 36–40 → I²C/SD), 6 DNP (FT232H pins 17–20, 27, 28) |

## Loading fees (extended parts JLC assembles)

About 17 unique extended parts so far: RP2350B, FT232HL, CH334P, 93LC56B, APS6404L, ABM8-272-T3,
Abracon inductor, TPS73701, TPS259470A, LM66200, TCA9555, SN74LVTH245A, 110 Ω (the 2.74 kΩ is
gone: R_ILM is now 2.4 k + 330 Ω), microSD socket, DIP switch, FDV301N, 74LVC1G17. JLC's fee is a few dollars per unique extended part per order
(from memory: check the current rate). Parts that appear several times on the board cost one fee.

## Still open before the schematic is complete

1. ~~SCSI drivers and receivers~~: decided 2026-09-25 (FDV301N, Nexperia 74LVC1G17GW).
2. LA header pinout matched to the Digital Discovery (buffers settled: 100 Ω series R).
3. ~~SWD connector style~~: decided 2026-09-25, Tag-Connect TC2030-IDC footprint.
4. ~~Resistor values~~: decided 2026-09-25 (table above). Still to set in the schematic:
   ~~eFuse dVdt/ITIMER caps~~ (decided 2026-09-26: 2.2 nF / open).
5. The owner's button size and USB-C part, to confirm the footprints.
