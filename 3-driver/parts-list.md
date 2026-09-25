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
| 2 | Bench-input eFuse; TERMPWR switch | TI TPS259470ARPWR | C3662799 | E | JLC | Bench: OVLO ≈ 5.7 V, ILIM ≈ 2 A, UVLO ≈ 4.3 V. TERMPWR: OVLO = active-low enable, ILIM ≈ 1.2 A (R_ILM ≈ 2.74 kΩ) |
| 1 | USB/bench ORing (U1) | TI LM66200DRLR | C3235556 | E | JLC | Both channels used |
| 2 | 3.3 V rail; terminator 2.80 V | TI TPS73701DCQR | C56848 | E | JLC | 3.3 V feedback divider in 0.1 % resistors (CH334 external mode needs 3.2–3.4 V) |
| 1 | CC detection | onsemi LM393DR2G | C7955 | B | JLC | Supply from 5 V; threshold 0.66 V |
| 2 | USB-C Rd | 5.1 kΩ 1 % 0402 | C25905 | B | JLC | |
| 1 | Bench-present switch | 2N7002 SOT-23 | C8545 | B | JLC | Pulls the TERMPWR enable node low |
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
| 14 | Driver gate pull-down | 10 kΩ 1 % 0402 | C25744 | B | JLC | Keeps lines released with the board off or the MCU in reset |
| 14 | Driver gate cap | 22 pF C0G 0402 | C1555 | B | DNP | Fit if the bus-edge kick on an idle gate exceeds ~0.4 V (bench check) |
| 18 | SCSI receivers | **Nexperia** 74LVC1G17GW,125 SOT-353 | C426705 | E | JLC | Nexperia only (other vendors' limits differ). 3.3 V. Fallback: 3 × Nexperia 74LVC14APW (C6066 / -Q100 C548122) |
| 18 | Receiver decoupling | 100 nF X7R 0402 | C307331 | B | JLC | One per 1G17 |
| — | **LA header buffers** | **Open** | — | — | — | 18 signals + 2 markers, Schmitt, 3.3 V |
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
| — | SWD header | **Open** (3-pin 2.54 mm or JST-SH to match the Pi debug probe) | — | — | Hand | |
| — | LEDs | Basic 0603 (e.g. KT-0603R red C2286); count and colors at schematic time | — | B | JLC | |

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

## Loading fees (extended parts JLC assembles)

About 17 unique extended parts so far: RP2350B, FT232HL, CH334P, 93LC56B, APS6404L, ABM8-272-T3,
Abracon inductor, TPS73701, TPS259470A, LM66200, TCA9555, SN74LVTH245A, 110 Ω, 2.74 kΩ
(R_ILM, if no basic combination works), microSD socket, DIP switch, FDV301N, 74LVC1G17, plus the
LA-buffer parts once chosen. JLC's fee is a few dollars per unique extended part per order
(from memory: check the current rate). Parts that appear several times on the board cost one fee.

## Still open before the schematic is complete

1. ~~SCSI drivers and receivers~~: decided 2026-09-25 (FDV301N, Nexperia 74LVC1G17GW).
2. LA header buffers and the pinout matched to the Digital Discovery.
3. SWD connector style.
4. Resistor values set at schematic time: UVLO/OVLO dividers, R_ILM (prefer a basic series
   combination over the extended 2.74 kΩ, C33360), LDO feedback dividers, LM393 reference and
   hysteresis, LED resistors, I²C pull-ups (4.7 kΩ), SDIO pull-ups.
5. The owner's button size and USB-C part, to confirm the footprints.
