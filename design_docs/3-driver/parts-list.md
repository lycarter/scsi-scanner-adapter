# Driver board: schematic-ready parts list

Status: 2026-09-26, after the design review (`docs/design-review-2026-09-26.md`; finding IDs
like R006 point there). This file collects every part decided in `NOTES.md`, so drawing the
schematic is mostly placing parts. **`NOTES.md` holds the reasoning** (values and worst cases:
"Resistor and small-part values"); this file holds the list. When a decision changes, update both.

Columns:
- **Tier:** JLC library tier. **B** = basic, **P** = preferred (both carry no loading fee),
  **E** = extended (one loading fee per unique part per order).
- **Fit:** **JLC** = JLC assembles it; **Hand** = owner solders it (LCSC or own stock);
  **DNP** = footprint only.
- Stock was checked on 2026-09-24 (2026-09-26 for new parts). Check it again before ordering.

## 1. Power (`blocks/1-power.md`)

| Qty | Function | Part | LCSC | Tier | Fit | Notes |
|---|---|---|---|---|---|---|
| 1 | Bench 5 V terminal | 2-pin 5.08 mm screw terminal (Kangnex WJ500V-5.08-2P) | C8465 | E | Hand | Plus a test loop per pole (any 0.1" loop, hand-soldered) |
| 2 | Bench-input eFuse; TERMPWR switch | TI TPS259470ARPWR | C3662799 | E | JLC | Bench: OVLO 5.35 V, ILIM 2.22 A, UVLO 4.22 V, EN Zener. TERMPWR: OVLO (via 56 k/47 k) = active-low enable, ILIM 1.22 A, UVLO 4.32 V |
| 1 | Power mux U1 (bench priority) | TI TPS2116DRLR | C3235557 | E | JLC | **Replaces the LM66200 (C3235556), 2026-09-26 (R068).** VIN1 = bench eFuse out, VIN2 = VBUS, MODE = VIN1, PR1 100 k/39 k, ST → expander P02 |
| 2 | 3.3 V rail; terminator 2.83 V | TI TPS73701DCQR | C56848 | E | JLC | 3.3 V = 47 k / 27 k (+ DNP 0603 across R2). 2.83 V = (39 k + 5.6 k) / 33 k. EN = 100 k / 75 k from IN |
| 1 | CC detection | onsemi LM393DR2G | C7955 | B | JLC | Supply from 5 V; thresholds 0.661 V rising / 0.651 V falling; outputs drive the TERMPWR enable node |
| 1 | CC threshold reference | CJ431 (TL431-type) SOT-23 | C3113 | B | JLC | 2.500 V from 3.3 V through **470 Ω**. **No cap on the cathode.** Rank (0.5 % / 1 %) unknown: check the reel |
| 1 | Bench eFuse EN clamp | BZT52C5V6, SOD-123 | C19077402 | P | JLC | EN/UVLO to GND (R057) |
| 2 | USB-C Rd | 5.1 kΩ 1 % 0402 | C25905 | B | JLC | |
| 1 | Bench-present switch | 2N7002 SOT-23 | C8545 | B | JLC | Pulls the TERMPWR enable node low. Gate fed from the bench eFuse *output* (10 k / 100 k) |
| 1 | TERMPWR disable jumper | 1×2 2.54 mm header + shunt | — | — | Hand | |
| 1 | TERMPWR OUT negative-spike clamp | SS14, SMA | C2480 | B | DNP | Cathode on TERMPWR. Fit only if OUT dips below −0.8 V on the scope (leakage counts against the 1 mA TERMPWR budget) |
| 1 | VBUS ESD | SMF6.0A | C19077499 | P | JLC | (also listed under USB) |
| 1 | TERMPWR ESD | SMF6.0A | C19077499 | P | JLC | |
| 1 | Bench-terminal TVS | **SMF15CA** (bidirectional) | C19077510 | P | DNP | Footprint only. Bidirectional, so reversed leads don't forward-bias it (R060) |

### Power-rail capacitors (R097; details in NOTES "Power mux", "eFuse startup", "Power budget")

| Qty | Value | Part | LCSC | Tier | Where |
|---|---|---|---|---|---|
| 1 | 1 µF 50 V X7R 0805 | Samsung CL21B105KBFNNNE | C28323 | B | Bench eFuse IN (rated ≥ 2 × V_IN) |
| 7 | 1 µF 25 V X5R 0402 | | C52923 | B | Bench eFuse OUT / TPS2116 VIN1, TPS2116 VIN2, TERMPWR eFuse OUT, LDO C_IN ×2, CC filters ×2 (PSRAM 1 µF listed in §3) |
| 1 | 4.7 µF 25 V X5R 0805 | Samsung CL21A475KAQNNNE | C1779 | B | VBUS snubber, in series with the 1 Ω below |
| 1 | 1 Ω 1 % 0603 | | C22936 | B | VBUS snubber |
| 1 | 22 µF 25 V X5R 0805 | Samsung CL21A226MAQNNNE | C45783 | B | +5V_SYS bulk (TPS2116 VOUT) |
| 2 | 10 µF 25 V X5R 0805 | | C15850 | B | LDO outputs (3.3 V, 2.83 V) |
| 2 | 2.2 nF X7R 50 V 0402 | | C1531 | P | eFuse dVdt, bench and TERMPWR (~5.5 ms ramp) |
| 0 (2 DNP) | 0402 pad, ~1 nF if fitted | — | — | — | eFuse ITIMER, open by default |
| 1 | 270 Ω 1 % 0603 (100 mW) | | C22966 | B | Terminator-rail bleed (10.5 mA, 30 mW) |
| — | 100 nF 50 V X7R 0402 | | C307331 | B | Bench eFuse IN, TERMPWR eFuse IN, TPS2116 VOUT, LM393, TERMPWR ADC pin (counted in the decoupling total, §5) |

## 2. SCSI front end (`blocks/2-scsi-frontend.md`)

| Qty | Function | Part | LCSC | Tier | Fit | Notes |
|---|---|---|---|---|---|---|
| 1 | SCSI connector | 2×25 keyed box header, 2.54 mm (BOOMELE) | C30006 | E | Hand | LCSC MOQ 5. Footprint `IDC-Header_2x25_P2.54mm_Vertical`. Pin 25 unconnected |
| 1 | Alt SCSI connector | Half-pitch 50-pin female, right angle | — | — | DNP | Not stocked anywhere; owner sources later. TERMPWR = pin 38; pin 13 unconnected |
| 4 | RESERVED lines to GND | 0 Ω 0402 | C17168 | B | JLC | All four RESERVED lines (SCSI-2 §5.4.4): IDC50 23/24/27/28 = HD50 12/37/14/39. Remove if mid-chain. Was 2 (24/28 only) until 2026-09-26 |
| 3 | Terminator switches | TI SN74LVTH245APWR | C2652121 | E | JLC | **Only 939 at JLC.** A1–A8 and DIR tied to the 2.83 V rail, `/OE` = enable. 100 nF each |
| 36 | Terminator resistors | 220 Ω 1 % 0402 (UNI-ROYAL) | C25091 | B | JLC | **Two in parallel per line = 110 Ω** (R006), ≤ 35 mW each. Replaces 18 × 110 Ω C2909312 (extended, would run at 100–110 % of rating) |
| 1 | Terminator on/off | 2-position DIP switch, SMD (SHOU HAN) | C6331180 | E | JLC | DIP 1 = default, DIP 2 = firmware may override (see `USAGE.md`) |
| 18 | SCSI ESD | H5VUD5BB SOD-523, 0.3 pF | C20615820 | P | JLC | At the connector |
| 14 | SCSI drivers (open-drain) | onsemi FDV301N SOT-23 | C15310 | E | JLC | DB0–7, DBP, ATN, ACK, SEL, BSY, RST. GPIO high = asserted. Fallback: 4 × SN74LVTH125PWR (C7042), see NOTES "SCSI drivers" |
| 14 | Driver gate series R | 100 Ω 1 % 0402 | C25076 | B | JLC | Edge-rate tuning on the bench (0 Ω or larger) |
| 14 | Driver gate pull-down | 4.7 kΩ 1 % 0402 | C25900 | B | JLC | Keeps lines released with the board off or the MCU in reset. ≤ 8.2 kΩ required by RP2350-E9 (A2 silicon) |
| 14 | Driver gate cap | 22 pF C0G 0402 | C1555 | B | DNP | Fit only if the bus-edge kick shows on the bus edge (bench check, R037) |
| 18 | SCSI receivers | **Nexperia** 74LVC1G17GW,125 SOT-353 | C426705 | E | JLC | Nexperia only (other vendors' limits differ). 3.3 V. Fallback: 3 × Nexperia 74LVC14APW (C6066 / -Q100 C548122) |
| 18 | Receiver decoupling | 100 nF X7R 0402 | C307331 | B | JLC | One per 1G17 |
| 20 | LA tap series R | 100 Ω 1 % 0402 | C25076 | B | JLC | At each 1G17 output (18) and marker GPIO (2); the receivers are the Schmitt buffers, so no second bank |
| 1 | LA header | Liansheng BH-00169, 2×16 2.54 mm keyed box header | C2685073 | E | Hand | Pin-for-pin copy of the Digital Discovery DIN connector (ref. manual Fig. 8), so a straight 32-way IDC ribbon connects it. Replaces the bare header C124382 |

## 3. RP2350B and support (`blocks/3-mcu-support.md`)

| Qty | Function | Part | LCSC | Tier | Fit | Notes |
|---|---|---|---|---|---|---|
| 1 | MCU | Raspberry Pi RP2350B, QFN-80 | C42415655 | E | JLC | 4,296 at JLC. Plan for A4 silicon. Exposed pad = the only GND |
| 1 | Core-regulator inductor | Abracon AOTA-B201610S3R3-101-T, 3.3 µH | C42411119 | E | JLC | Polarity mark on the footprint |
| 4 | Regulator caps | 4.7 µF X5R 10 V 0402 | C23733 | B | JLC | CIN, COUT, VREG_AVDD, and a 2nd on DVDD pin 32 (R081). Fallback 0603 C19666 for CIN if DC bias is a problem |
| 1 | VREG_AVDD filter R | 33 Ω 1 % 0402 | C25105 | B | JLC | |
| 1 | 3.3 V bulk | 10 µF X5R 0805 | C15850 | B | JLC | Near the MCU |
| 1 | QSPI flash | Winbond W25Q128JVSIQ, 16 MB | C97521 | B | JLC | |
| 1 | PSRAM | AP Memory APS6404L-3SQR-SN, 8 MB | C5333729 | E | JLC | CS1 = GPIO 47. 100 nF + 1 µF (C52923) decoupling. Rated 2.7–3.6 V (LCSC's "3.3 V max" is wrong) |
| 1 | PSRAM CS1 pull-up | **3.3 kΩ** 0402 | C25890 | B | JLC | Was 10 kΩ (R079) |
| 1 | QSPI_SS pull-up | 10 kΩ 0402 | C25744 | B | DNP | Guide R1 is DNF |
| 1 | 12 MHz crystal | Abracon ABM8-272-T3 | C20625731 | E | JLC | Same part ×3 on the board (see USB) |
| 2 | Crystal load caps | 15 pF C0G 0402 | C1548 | B | JLC | |
| 3 | 1 kΩ | 1 kΩ 1 % 0402 | C11702 | B | JLC | Crystal series, BOOTSEL, RUN |
| 2 | BOOTSEL, RUN buttons | Owner's through-hole tact switches | — | — | Hand | Size to check (6 × 6 mm?) |
| 1 | microSD socket | SHOU HAN TF PUSH | C393941 | E | JLC | Card detect → expander. 10 µF (C15850) + 100 nF at the socket |
| 1 | I²C expander | TI TCA9555PWR | C465732 | E | JLC | INT to a test point only (firmware polls) |
| 1 | TERMPWR sense divider | 100 kΩ + 100 kΩ 0402 + 100 nF | C25741 | B | JLC | TERMPWR → GPIO 46 (ADC6), R066. (Resistors counted in §6) |
| — | SWD | Tag-Connect TC2030-IDC footprint (pads + clip holes, no part) | — | — | — | 1 VCC, 2 SWDIO, 3 RUN, 4 SWCLK, 5 GND, 6 NC. Owner buys a TC2030-IDC cable + ARM20-CTX adapter for the J-Link EDU |
| 4 | LEDs | KENTO KT-0603R red (C2286), or KT-0805Y yellow (C2296) where a second color helps | C2286 | B | JLC | TERMPWR enable (3.3 V, 1 k), TERMPWR present (on TERMPWR, **10 k**, ≈ 0.35 mA), LED1/LED2 on the expander (1 k). The basic green needs Vf up to 3.1 V: not on 3.3 V |

## 4. USB path (`blocks/4-usb.md`)

| Qty | Function | Part | LCSC | Tier | Fit | Notes |
|---|---|---|---|---|---|---|
| 1 | USB-C receptacle | Owner's own; footprint HRO TYPE-C-31-M-12 | (C165948) | — | Hand | 16-pin USB 2.0. Shell to GND through a 0 Ω (§6) |
| 1 | USB hub | WCH CH334P | C5373042 | E | JLC | External 3.3 V mode. 10 µF (C15850) + 2 × 100 nF on V5/VDD33. RESET#: **no pull-up**; expander P14 via the Schottky below |
| 1 | Hub reset diode | 1N5819WS Schottky, SOD-323 | C191023 | B | JLC | Anode at CH334 RESET#, cathode at expander P14 (R031) |
| 1 | Hub crystal | ABM8-272-T3 | C20625731 | E | JLC | Load caps DNP (internal ~16 pF) |
| 1 | HS USB bridge | **FTDI FT232HL-REEL (LQFP-48)** | C51997 | E | JLC | $9.36. Same pinout as the QFN; the QFN (C82158) is out of stock. Powered per DS Fig. 6.2: VCCD makes its own 3.3 V (`FT_3V3`) |
| 1 | FT232H config EEPROM | Microchip 93LC56BT-I/OT, SOT-23-6 | C190271 | E | JLC | Required. VCC from FT_3V3. Program over USB after assembly (`USAGE.md`) |
| 1 | FT232H crystal | ABM8-272-T3 + 2 × 15 pF | C20625731, C1548 | E, B | JLC | |
| 1 | FT232H REF | 12 kΩ 1 % 0402 | C25752 | B | JLC | REF to GND (R017) |
| 2 | FT232H VPHY/VPLL ferrites | Sunlord GZ1608D601TF, 600 Ω @ 100 MHz, 0603 | C1002 | B | JLC | From FT_3V3 |
| 2 | FT232H VREGIN, VCCD bulk | 4.7 µF X5R 10 V 0402 | C23733 | B | JLC | + 2 DNP 4.7 µF pads on VPHY/VPLL |
| 10 | FT232H decoupling | 100 nF X7R 0402 | C307331 | B | JLC | VREGIN, VCCD, VCCIO ×3, VPHY, VPLL, VCCA, VCORE, EEPROM |
| 1 | FT232H RESET# cap | 10 nF X7R 50 V 0402 | C15195 | B | JLC | With the 10 kΩ pull-up to FT_3V3 |
| 1 | FT232H EEPROM DO → DI | 2.2 kΩ 1 % 0402 | C25879 | B | JLC | Plus a 10 kΩ DO pull-up (§6) |
| 7 | FT1248 series R | 33 Ω 1 % 0402 | C25105 | B | JLC | At the RP2350 end (R021) |
| 2 | RP2350 USB series R | 27 Ω 1 % 0603 | C25190 | P | JLC | Close to the RP2350 |
| 2 | USB D± ESD | H5VUD5BB | C20615820 | P | JLC | |
| 2 | CC ESD | H7VL10B DFN1006 | C20615787 | P | JLC | |

## 5. Decoupling totals (100 nF X7R 50 V 0402, C307331)

13 (RP2350B + flash, NOTES "MCU support parts") + 18 (1G17) + 10 (FT232H) + 3 ('245) + 2 (CH334)
+ 1 (TCA9555) + 1 (PSRAM) + 1 (microSD) + 1 (LM393) + 3 (bench IN, TERMPWR IN, TPS2116 VOUT)
+ 1 (TERMPWR ADC pin) = **54**.

## 6. Resistors and small parts (values and reasoning: NOTES "Resistor and small-part values")

All 1 % 0402, no loading fee, unless noted. Rows above that already list a part (gate 100 Ω,
LA 100 Ω, 220 Ω terminators, 33 Ω, 12 k, 2.2 k, 3.3 k CS1, …) aren't repeated.

| Qty | Value | LCSC | Tier | Where |
|---|---|---|---|---|
| 1 | 47 kΩ | C25792 | B | 3.3 V LDO R1 |
| 1 | 27 kΩ | C25771 | P | 3.3 V LDO R2 (+ 1 DNP 0603 pad in parallel for trim, R030) |
| 1 | 39 kΩ + 1 × 5.6 kΩ | C25783, C25908 | P, P | 2.83 V LDO R1 (in series) |
| 1 | 33 kΩ | C25779 | B | 2.83 V LDO R2 |
| 2 | 75 kΩ | C25798 | P | LDO EN dividers (bottom) |
| 6 | 100 kΩ | C25741 | B | LDO EN dividers (top) ×2, TPS2116 PR1 top, bench-FET gate pull-down, TERMPWR ADC divider ×2 |
| 1 | 510 kΩ | C11616 | P | Bench eFuse string R1 (only ~8.5k in stock; fine at our volume) |
| 1 + 1 | 39 kΩ + 3.9 kΩ | C25783, C51721 | P, P | Bench eFuse string R2 = 42.9 k |
| 1 + 1 | 150 kΩ + 10 kΩ | C25755, C25744 | P, B | Bench eFuse string R3 = 160 k |
| 1 | 1.5 kΩ | C25867 | B | Bench eFuse R_ILM (2.22 A) |
| 1 | 39 kΩ | C25783 | P | TERMPWR eFuse UVLO top |
| 1 | 15 kΩ | C25756 | P | TERMPWR eFuse UVLO bottom |
| 1 + 1 | 2.4 kΩ + 330 Ω | C25882, C25104 | P, B | TERMPWR eFuse R_ILM (1.22 A) |
| 1 | 56 kΩ | C25796 | P | TERMPWR OVLO divider top (node → OVLO) |
| 1 | 47 kΩ | C25792 | B | TERMPWR OVLO divider bottom |
| 1 | 39 kΩ | C25783 | P | TPS2116 PR1 bottom |
| 18 | 10 kΩ | C25744 | B | Terminator /OE pull-up (to 2.83 V); enable-node pull-up; CC filters ×2; CC ref top (with 3.3 k); bench-FET gate series; SDIO pull-ups ×5; FT232H RESET#; FT232H EEPROM DO; FT232H WR#, SIWU# ×2; expander INT; TPS2116 ST; TERMPWR-present LED |
| 1 | 3.3 kΩ | C25890 | B | CC reference top (10 k + 3.3 k = 13.3 k) |
| 3 | 4.7 kΩ | C25900 | B | CC reference bottom; I²C SDA/SCL |
| 1 | 1 MΩ | C26083 | B | CC hysteresis |
| 1 | 470 Ω | C25117 | B | CJ431 bias (was 510 Ω, R087) |
| 4 | 1 kΩ | C11702 | B | 3.3 V LEDs ×3; terminator DIP 1 pull-down |
| 15 | 0 Ω | C17168 | B | FT1248 rework links: 5 fitted (GPIO 36–40 → I²C/SD), 5 DNP (FT232H pins 17–20, 27); RESERVED ×4 (§2); USB-C shell ×1 |

Dropped on 2026-09-26: 110 Ω C2909312 (→ 2 × 220 Ω), 20 kΩ and 15 kΩ of the old 2.80 V divider,
56 k/150 k/150 Ω of the old bench string (56 k now used for the OVLO divider, 150 k kept),
22 k/33 k TERMPWR_OK divider, 6.8 kΩ LED resistor, 510 Ω CJ431 bias, 10 kΩ CH334 reset
pull-up, LM66200 C3235556.

## Loading fees (extended parts JLC assembles)

16 unique extended parts: RP2350B, FT232HL, CH334P, 93LC56B, APS6404L, ABM8-272-T3, Abracon
inductor, TPS73701, TPS259470A, TPS2116 (replaced the LM66200: no change in count), TCA9555,
SN74LVTH245A, microSD socket, DIP switch, FDV301N, 74LVC1G17. The extended 110 Ω is gone (R006).
JLC's fee is a few dollars per unique extended part per order (from memory: check the current
rate). Parts that appear several times on the board cost one fee.

## Still open before the schematic is complete

1. ~~SCSI drivers and receivers~~: decided 2026-09-25 (FDV301N, Nexperia 74LVC1G17GW).
2. ~~LA header pinout~~: decided 2026-09-26, a copy of the Digital Discovery DIN connector (NOTES log).
3. ~~SWD connector style~~: decided 2026-09-25, Tag-Connect TC2030-IDC footprint.
4. ~~Resistor values~~: decided 2026-09-25, revised 2026-09-26 after the design review.
5. The owner's button size and USB-C part, to confirm the footprints.
6. ~~TPS2116 datasheet~~: in `reference/datasheets/tps2116.pdf` (2026-09-26).
7. Test points: +5V_SYS, 3.3 V, 2.83 V, TERMPWR, FT_3V3, GND, TCA9555 INT, TERMPWR_EN_INVERTED.
