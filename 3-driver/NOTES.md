# Phase 3: Driver PCB (USB-C ↔ SCSI initiator)

Goal: a board that plugs into a modern computer over USB-C and acts as the SCSI
**initiator** for the D4000. It also serves as the **bus snooper**. The separate snooper PCB
was dropped on 2026-09-23: the G4, the scanner and this board share one multi-initiator
chain (see `1-bus-capture/NOTES.md` for the topology).

## Requirements (draft)

- R1: **SCSI-2 narrow SE initiator.** Async is mandatory; sync (5–10 MB/s) is optional and
  only needed if the scanner negotiates it or async proves too slow. It handles selection,
  arbitration, message phases, disconnect/reselect, and parity generation and checking.
- R2: **SE electricals.** The drivers sink 48 mA, open-collector. The receivers have
  hysteresis (≥0.2 V). Active termination (switchable) is on board. It must be safe when
  unpowered (no backfeed, no bus clamping).
- R2a: **TERMPWR supplied by the board** (we're the initiator; SCSI-2 §5.4.3 requires it):
  4.25–5.25 V at the connector, ≥900 mA source capability, through an **ideal diode**
  (no backflow), with a resettable fuse (≤1.5 A recommended) and a jumper to disable it.
- R3: **Sustained throughput ≥ 1.5 MB/s** end to end, host to scanner, based on the estimate
  in `docs/scanner-facts.md`. Target 3–5 MB/s for margin. Phase 2 will measure the real number.
- R4: **Listen-only mode.** The receivers can monitor the bus without driving it, which makes
  the board a long-capture protocol sniffer for Phase 2.
- R4a: **Buffered LA header.** All 18 signals come out through Schmitt buffers
  (3.3 V CMOS), pinned to match the Digital Discovery's 2×16 input connector, plus marker
  pins driven by firmware (e.g. "CDB start", "error"). This replaces the old snooper board.
- R4b: **Multi-initiator friendly.** The SCSI ID is configurable (default 6). The board never
  asserts RST unless told to, tolerates another initiator's traffic, and its termination is
  switchable, so it works at the chain end or mid-chain.
- R5: **Host interface over USB-C** that needs no custom kernel drivers on macOS, Linux or
  Windows. That means vendor-class bulk with WinUSB/MS OS 2.0 descriptors, or CDC/NCM.
- R6: Firmware updates over USB without special hardware. SWD header for debugging.
- R7: Everything JLC-assemblable from LCSC stock where possible.
- R8: **5 V power from USB-C.** Typical hosts are computers that offer 5 V at 1.5 A, maybe
  3 A, and rarely anything above 5 V. So the board runs on **5 V only** and reads the
  USB-C CC current advertisement (0.5/0.9 A default, 1.5 A, 3 A) to learn its budget. A full
  USB PD controller isn't required, because 5 V at up to 3 A is signalled over CC without PD
  (from memory: verify). Budget: the rough worst case is ~6 W; 1.5 A (7.5 W) should do. On a
  default-current port (≤0.9 A), keep TERMPWR off and report why rather than brown out.
- R8a: **Bench 5 V input as a backup.** Clip-friendly terminals, **reverse-polarity and
  over-voltage protected**, ORed with USB VBUS through ideal diodes so neither source can
  backfeed the other. A USB device must never drive VBUS.

## Why USB speed is the deciding constraint

USB **full-speed** (12 Mbit/s) gives ~1.0–1.2 MB/s of real bulk throughput, which is **below**
our 1.3 MB/s estimate for 16-bit RGB at 4000 dpi. USB **high-speed** (480 Mbit/s) removes the
problem. Many popular MCUs, including the RP2040/RP2350 and most ESP32s, are full-speed only.
(Whether the scanner tolerates a slow host is still an open Phase-2 question. If it simply
pauses, full-speed would work but make big scans slower.)

## Decision: the "brains"

**Recommendation: an MCU, not an FPGA and not a Linux SBC. Specifically, an RP2350 as the
SCSI engine plus a high-speed USB path.**

### Can a Raspberry Pi Zero (2 W) do it?

Probably, yes: the PiSCSI/RaSCSI project drives SCSI from Pi GPIO through 74LS641
transceivers. But I'd not make it the SCSI engine:

- Linux scheduling jitter. Async SCSI is interlocked, so jitter only slows transfers rather
  than corrupting them. But selection timeouts, sync mode and sustained throughput all get
  harder.
- It boots from an SD card, takes tens of seconds to boot, and is a whole OS to maintain.
- It's not on LCSC and not JLC-assemblable. You'd hand-mount a module.

The good part: USB-gadget mode could make it a driverless "network scanner appliance",
and scanning software could run on the device. That's worth remembering as a Phase-4
architecture idea, not as the SCSI engine.

### Do we need an FPGA?

No. Narrow SCSI-2 at ≤10 MB/s is a few-MHz, 18-signal handshake. That is squarely what
PIO (RP2xxx) or FlexIO (i.MX RT) are designed for. An FPGA only earns its place for Wide/Ultra
SCSI or a custom high-rate logic analyzer, and we need neither.

### MCU options

| Option | SCSI side | USB | Pros | Cons |
|---|---|---|---|---|
| **RP2350 + FT232H** (recommended) | PIO state machines. There's prior art: the ZuluSCSI and BlueSCSI v2 open-source projects run SCSI (including an initiator mode) on RP2040/RP2350 | FT232H in FIFO mode: USB 2.0 HS, ~8 MB/s async FIFO | Well-trodden SCSI-on-PIO path you can study. Both chips on LCSC, QFN/LQFP, JLC-assemblable. RP2350 supports PSRAM for line buffering. Great for learning | Two chips. Host uses libftdi/D2XX (driverless on macOS/Linux; Windows auto-installs FTDI's driver) |
| RP2350 alone | PIO | Native full-speed only | Simplest, cheapest, one chip | ~1 MB/s ceiling (see above) |
| NXP i.MX RT1062 (e.g. a Teensy 4.1 module) | FlexIO or bit-bang at 600 MHz | Native HS with integrated PHY | One chip with HS. 1 MB SRAM, optional PSRAM on Teensy | BGA if designed in bare. The Teensy module isn't on LCSC. Less SCSI prior art |
| STM32 with integrated HS PHY (F723/F733, U5A5, H7R/S) | Bit-bang or timer/DMA | Native HS | One chip, LQFP, ST ecosystem, TinyUSB support | No PIO: cycle-exact handshakes are harder. Less SCSI prior art |
| WCH CH32V305/307 | Bit-bang | Native HS with PHY | Very cheap, LCSC-native | Younger ecosystem and docs. A tougher learning path |

**Decided 2026-09-24: RP2350B + FT232H, behind a USB hub.** We reconsidered a one-chip STM32 with built-in USB high speed, because it would free the FT232H's 12–13 GPIO and fix the budget. We rejected it: losing PIO makes the SCSI handshake the riskiest part of the project, with little prior art. The GPIO overrun gets fixed with an expander or FT1248 instead (open question 7).

Original note: this is a real fork. I lean RP2350 + FT232H for the SCSI prior art and
learnability. Teensy 4.1 is the strongest "one chip" alternative if you'd rather avoid the
FTDI. A neat variant is a small USB 2.0 hub chip (e.g. FE1.1s/CH334), so a single USB-C
cable carries both the FT232H (fast data) and the RP2350's own USB (console and firmware
update).

## Block architecture (in progress)

Diagrams: `blocks/0-overview.md`, `1-power.md`, `2-scsi-frontend.md`, `3-mcu-support.md`,
`4-usb.md`. Each is generated from a page source in `blocks/_src/` (named boxes and links)
by `python3 3-driver/blocks/_src/build.py`. The build checks the layout (no overlaps, wires
touch the boxes they name) and writes a connection list under each diagram. To learn what a
diagram says, read its source or that list rather than the art.

Decided with the owner on 2026-09-23:

- **USB: over-spec for high speed.** The RP2350's built-in USB is full-speed only (12 Mbit/s),
  so high speed needs an external bridge. Working choice: FT232H in async FIFO mode (~8 MB/s).
  We build it now rather than waiting for Phase 2 to show whether full speed would do.
- **Power: 5 V from USB-C** (R8, reading the CC current advertisement), plus a **bench 5 V
  input** (R8a) as a backup. The two are ORed with ideal diodes. Budget to be written up.
- **TERMPWR: required by the spec.** SCSI-2 §5.4.3 says "SCSI initiators *shall* supply
  terminator power ... through a diode or similar semiconductor that prevents backflow".
  For single-ended it must be **4.25–5.25 V with at least 900 mA** of source capability. So we
  supply it regardless of what the D4000 does. The pin-26 measurement still tells us whether
  the scanner also supplies it (useful for bring-up), but it no longer blocks the decision.
  **Decided (2026-09-23): we supply it through an ideal diode** (R2a). A Schottky drop
  (~0.3–0.45 V at 0.9 A) on a sagging 5 V could fall below 4.25 V. Power comes from USB-C
  5 V or the bench input (R8, R8a). VBUS tolerance figures are from memory: verify.
  **EN is hardware: CC_OK (port ≥1.5 A) OR bench present**, no MCU involvement, with an LED
  on EN (decided 2026-09-23). See `blocks/1-power.md`.
- **MCU: RP2350B** (QFN-80, 48 GPIO). The RP2350A's 30 GPIO is too few.
- **USB: a USB 2.0 HS hub chip behind the one USB-C connector** (decided 2026-09-24,
  open question 10). The host sees three devices: the hub, the FT232H (high speed, scan
  data) and the RP2350B's native USB (full speed). The native port gives firmware updates
  through the ROM bootloader (UF2/picotool; it lives in ROM so it can't be bricked, and
  the host can trigger it without a button through the ROM `reboot(BOOTSEL)` call), plus a
  CDC serial console. The console **replaces the debug UART header** (2 GPIO saved), and the
  SWD header stays for deep debugging. In-app A/B updates over the FIFO (try-before-you-buy)
  are an optional firmware convenience later. The RP2350's USB_DP/DM need 27 Ω series
  resistors close to the chip (Hardware design with RP2350). The hub is a CH334P with a
  12 MHz crystal (decided 2026-09-24, see "USB hub"). See `blocks/4-usb.md`.
- **RAM: yes, on board.** A whole scan won't fit (4000 dpi, 16-bit RGB, full area ≈ 12 GB),
  so the RAM is an elastic buffer that rides out host stalls. Working choice: 8 MB QSPI PSRAM on
  the RP2350's second chip select (≈5 s at 1.5 MB/s).
- **microSD slot** (4-bit SDIO over PIO, as BlueSCSI v2 does). Two uses: (a) a spill target
  if the host falls behind; (b) a development path where scan logic on the MCU writes to
  the card, so the scanner side can be brought up before USB and host software exist. The
  PSRAM also absorbs SD write-latency spikes. **Update 2026-09-24 (open question 6): (b) is
  dropped for now. The SD card is spill only, and a CDB-script runner can be added later.**
- **Connector: IDC50** (2×25 shrouded box header, ribbon cable), plus an **unpopulated HD50
  footprint** on the same nets. With both fitted, the board could sit mid-chain.
  - IDC50 and HD50 use **different pin numbers for the same signal**: wire the footprints by
    signal name, never by pin number. On IDC50 the odd pins are ground and the even pins
    carry signals (DB0 = 2 … I/O = 50, TERMPWR = 26), so the ribbon alternates signal and
    ground.
  - SE SCSI-2 allows 6 m of total bus length, counting the cable inside the G4 and inside
    the scanner (§5.2.1). The often-quoted 3 m limit for fast mode is **not** in SCSI-2 rev
    10L; it comes from later standards.
- **SE front end (pencilled in): 74LVT family on a ~2.85 V or 3.3 V rail**, following
  BlueSCSI v2 but with per-bit open-drain drive for real arbitration, plus ATN and RST
  outputs. See `prior-art/bluescsi-v2.md`. **Owner follow-up:** research this choice
  independently before we commit.

### SCSI-2 electrical facts that constrain us (rev 10L, §5)

Checked in `reference/standards/SCSI-2_X3T9.2-375R_rev10L.txt` on 2026-09-23.

| Item | Spec | Section |
|---|---|---|
| Driver output low | 0.0–0.5 V while sinking 48 mA | 5.4.1.1 |
| Driver type | Open-collector or three-state (push-pull) allowed, **except BSY, SEL and RST, which must be OR-tied (open-collector)** | 5.4.1.1, 5.6.2 |
| Receiver thresholds | VIL ≤ 0.8 V, VIH ≥ 2.0 V, recommended switch point ~1.4 V | 5.4.1.2 |
| Receiver hysteresis | **≥ 0.2 V** | 5.4.1.2 |
| Input capacitance | ≤ 25 pF per signal, at the connector | 5.4.1.2 |
| Unpowered behaviour | *Recommended* that powered-off devices still meet IIL/IIH, i.e. don't load the bus | 5.4.1.2 |
| Termination | 220/330 Ω passive, or active at 100–132 Ω; released lines ≥ 2.5 V; terminators contribute ≤ 44.8 mA | 5.4.1 |
| TERMPWR | Initiators **shall** supply it, through a diode; SE: 4.25–5.25 V, ≥ 900 mA; recommended current limit 1.5 A | 5.4.3 |
| Cable | 6.0 m total; **stubs ≤ 0.1 m** off the main cable, including inside a device | 5.2.1 |
| Parity | DB(P) is odd parity; **required** in SCSI-2 (it was optional in SCSI-1); undefined during arbitration, and DB(P) must not be driven false during arbitration | 5.6, Annex |

Consequences for us: receivers must be Schmitt triggers (hysteresis). Keep the traces from
the connectors to the transceivers short, because they count as a stub. If both the IDC50
and HD50 are fitted, the bus passes through the board, so run it straight between the two
connectors and keep the tap short.

### USB hub (decided 2026-09-24): WCH CH334P, with a 12 MHz crystal

- **CH334P, C5373042**: QFN-16 3×3, $0.44, ~38k JLC stock (2026-09-24), extended.
  USB 2.0 HS 4-port, MTT, internal 5 V→3.3 V LDO, built-in upstream pull-up and downstream
  pull-downs. No over-current detection, which we don't need (both downstream devices are on
  board). Reset from an expander pin. Sources: **English datasheet V2.5**
  (`reference/datasheets/CH334DS1_en.pdf`, the one to use for design review) and the newer
  Chinese V2.91 (`CH334.pdf`). The owner required an English datasheet so they can validate
  the design; without one, the FE1.1s or GL850G would have been chosen.
- **Crystal: fitted, not optional.** Datasheet §6.2: crystal-free mode "may deviate from the USB
  specification; only suitable for non-precision applications", and it is "not enabled by
  default on CH335 and some CH334 packages — confirm when ordering". Our HS link carries scan
  data, so we fit a 12 MHz crystal. The English V2.5 confirms this §6.2 wording. The CH334 has
  internal load capacitors ("crystal oscillator with built-in capacitor"). The explicit advice
  to add **no external caps** is in the Chinese V2.91 §6.1 only; confirm it against the
  English reference schematics when choosing the crystal.
- Layout: crystal next to XI/XO, short equal traces, solid ground under it with no signals
  routed beneath, no vias, away from the USB pairs and the SCSI lines.
- **Internal load caps: about 16 pF** (Chinese V2.91 §6.1, p. 26: "XI 和 XO 引脚已内置约16pF
  振荡电容，建议晶体X1不加外部振荡电容", "XI and XO have built-in oscillator caps of about 16 pF;
  we recommend no external caps on crystal X1"). The English V2.5 doesn't give the value. Read as
  16 pF on each pin, the crystal sees 16/2 + ~2–3 pF stray ≈ 10–11 pF, which matches a
  **CL = 10 pF** crystal. That reading is likely but unconfirmed: the text doesn't say "per pin".
- **Crystal choice (accepted 2026-09-24): the ABM8-272-T3 (CL 10 pF, ESR ≤ 50 Ω) fits the CH334
  better than C9002 (CL 20 pF, ESR 80 Ω)**, so one crystal type can serve the RP2350 and the
  hub. Why it's low-risk either way: USB HS allows ±500 ppm; the crystal is ±30 ppm, and a few pF
  of load mismatch pulls it only tens of ppm. Lower ESR only makes start-up easier. Not
  checked: the CH334's drive level into the ABM8 (the datasheet gives no oscillator drive
  figure). Cheap insurance: two unfitted 0402 load-cap pads on XI/XO.
- Rejected: CH334R (same chip in QSOP-16, +$0.12, kept as the pin-compatible-in-function
  fallback), FE1.1s (crystal required, single TT, 0–70 °C, SSOP-28), GL850G (similar), USB2514B
  (configurable, but $2.39 and 3.4k stock).

### Terminator LDO (decided 2026-09-24): TI TPS73701 at 2.80 V

- **What the spec forces (SCSI-2 §5.4.1(b), rev 10L):** (b)(3) allows each terminator ≤ 22.4 mA
  into a line asserted at 0.5 V, so V_term ≤ 0.5 V + 22.4 mA × 110 Ω ≈ **2.96 V**. (b)(4)
  requires released lines ≥ 2.5 V. (b)(2) requires the terminator to be powered from TERMPWR.
  So 3.3 V termination is out (25.5 mA per line).
- Load: (2.8 − 0.5) / 110 ≈ 21 mA per asserted line, ~0.39 A with all 18 asserted.
  Worst-case dissipation (5.25 − 2.8) × 0.39 ≈ 0.95 W, which needs SOT-223-class copper.
- **TPS73701DCQR, C56848** (JLC extended; no basic LDO fits), SOT-223-6, $1.10, 7,148 stock
  (2026-09-24). 2.2–5.5 V in, ~130 mV dropout at 1 A, stable with ≥ 1 µF ceramic, reverse-
  current protection, current limit, thermal shutdown. Accuracy: 1 % initial, 3 % overall
  (legacy silicon) / 1.5 % (new).
- **Set to 2.80 V nominal, not 2.85 V:** with 3 % + 1 % resistors, the worst case is ≈ 2.69–2.91 V,
  inside the 2.5–2.96 V window. At 2.85 V the worst case would touch 2.96 V.
- Rejected: **AMS1117-2.85** (BlueSCSI's part, C14791; dropout ~1.1–1.3 V leaves ~0.2 V of
  margin at 4.25 V TERMPWR, and only 1,077 in stock; BlueSCSI feeds it from 5 V, not
  TERMPWR); **RT9013** (SOT-23-5 can't dissipate ~0.9 W); BCT2057 (cheap, lesser-known brand,
  small DFN); TPS7A4501 (more than needed); **a 3.3 V LDO + divider** (owner's question): a
  divider can't source the 0–0.39 A switching load stiffly. The per-line Thevenin variant
  (~127 Ω to 3.3 V / ~806 Ω to GND) loads the bus when "disabled", draws ~64 mA all the
  time, and adds 36 resistors. An AMS1117-3.3 also falls out of regulation below ~4.5 V
  TERMPWR. The adjustable LDO is the right form of "LDO + divider": the divider sits in the
  feedback path and carries only µA.
- **To check when we draw it:** an LDO can't sink. If another device actively drives a
  released line above our 2.8 V, the current flows back into the rail. Probably fine (SE
  drivers are open-collector or three-state per §5.4.1.1, and asserted lines draw current
  from the rail), but add a small bleed load on the rail and scope it at bring-up.

### CC detection (decided 2026-09-24): LM393 dual comparator

CC_OK drives the hardware TERMPWR enable (`CC_OK OR bench present`, no MCU). A copy goes to
an expander input so firmware can explain a dead bus ("port only offers 500 mA").

- Thresholds (TUSB321 datasheet, the Type-C sink values): **0.66 V** = Default vs. 1.5 A,
  1.23 V = 1.5 A vs. 3 A. Only 1.5 A is detected, which covers the budget. Window: Default
  reads ≤ ~0.61 V, 1.5 A reads ≥ ~0.70 V, so the threshold has about ±40 mV of room.
- Circuit: 5.1 kΩ 1 % Rd from CC1 and CC2 to GND. Each CC goes through a series R + C filter
  (roughly 100 kΩ / 100 nF, τ ≈ 10 ms: debounce, and the big R keeps the cap off the CC
  line) into the inverting input of one LM393 half. A shared 0.66 V reference comes from 3.3 V
  (e.g. 40.2 k / 10 k, 1 %) on the + inputs. The open-collector outputs are wired together
  with a pull-up to 3.3 V, giving **CC_OK_N (active low)**. A ~1 MΩ feedback resistor from
  the output to the reference node adds ~20 mV of hysteresis. Values get finalized at
  schematic time.
- Part: **LM393DR2G, C7955, JLC basic**, $0.07, ~240k stock. Everything else is basic
  passives.
- Error budget: LM393 Vos 5 mV + 1 % dividers + 3.3 V LDO tolerance ≈ ±15–20 mV. That fits the
  ±40 mV window.
- **To check when we draw it (unverified):**
  - Supply the LM393 from the 5 V (ORed) rail, not 3.3 V. Its input common-mode range tops
    out at Vcc − 1.5 V, and a 3 A port puts up to ~2.04 V on CC. The output pull-up still
    goes to 3.3 V.
  - If the host tries PD, its messages swing CC between ~0 and ~1.1 V for about 1 ms. The
    10 ms RC should average that to a dip of ~20 mV, inside the hysteresis. Verify against
    the Type-C/PD spec timing.
  - A legacy USB-A to C cable has a 56 kΩ pull-up, which reads ~0.42 V ("Default"). No
    TERMPWR from USB then: document it in `USAGE.md` (use the bench input).
- Rejected: **TUSB321** (C139392; OUT1 is CC_OK directly, but extended, $1.18, a 1.6 mm
  X2-QFN; the owner preferred the all-basic discrete design); **ADC** (an expander with an ADC or
  the RP2350 ADC: needs firmware, which breaks the "no MCU in the enable path" decision);
  **transistor Vbe threshold** (±50 mV spread and −2 mV/°C drift is wider than the window).
- Zero-cost option for the pin plan, not decided: put the spare GPIO on an ADC-capable pin
  (GPIO 40–47) for TERMPWR or VBUS monitoring.

### Ideal diodes (decided 2026-09-24): one part type, TI LM66200 ×2

**Update 2026-09-24 (proposed): U2 and the polyfuse are replaced by a TPS259470A eFuse; see
"TERMPWR switch". U1 (the ORing) is unchanged.**

**Goal (owner): every ideal diode on the board uses one part type**, because all 134 ideal-diode
/ ORing parts at JLC are extended and each unique part costs a loading fee.

- **LM66200DRLR, C3235556**: dual ideal diode with a shared output, SOT-583, $0.48, 30,949
  JLC stock (2026-09-24). 1.6–5.5 V, 2.5 A per channel, RON 37 typ / 46 max mΩ at 5 V
  (25 °C). Reverse blocking when VOUT > VINx. Truth table: ON low → higher VIN drives VOUT;
  **ON high → VOUT Hi-Z**. ST reports which input is in use.
- **U1, ORing:** VIN1 = USB VBUS, VIN2 = bench input (after its protection), ON = GND,
  VOUT = 5 V rail. ST → expander ("running on bench / USB").
- **U2, TERMPWR switch:** VIN = 5 V rail, VOUT → polyfuse → jumper → TERMPWR. **ON pulled up
  to 5 V, and pulled low (enabled) by a wired-OR of open-drain signals:** the LM393's
  CC_OK_N output and an N-FET switched on by the bench input. That's `CC_OK OR bench` with
  no logic gate. The LED sits on the same node.
- Rejected: **LM66100** (C2869734, $0.23). Its Table 1 says the disabled state is "Diode":
  the body diode still conducts IN→OUT, so it can't turn TERMPWR off. **TPS2121**
  (C485916, $1.05, QFN): a mux with an adjustable current limit that could replace the
  polyfuse. **Fallback if the TERMPWR voltage budget fails.** MAX40200 (1 A, too little);
  CH213K (no enable); external-FET controllers (LM5050/LM74700 class: more parts, aimed at
  higher voltages).
- **To check when we draw it (unverified):**
  - ON logic thresholds aren't in the datasheet (SLVSG04); pulling ON up to 5 V avoids the
    question. The copy of CC_OK_N for the expander needs its own 3.3 V path.
  - U2's unused input: parallel VIN1 and VIN2, or tie VIN2 off? The datasheet doesn't say.
  - Reverse blocking with our board unpowered while another device drives TERMPWR. Likely
    (true Hi-Z off), not confirmed.
  - **TERMPWR voltage budget:** VBUS at the host can be as low as 4.75 V, minus cable drop,
    minus U1 + U2 (~0.1 V at 0.9 A), minus the polyfuse (~0.1–0.25 V), against SCSI-2's
    4.25 V minimum. Pick a low-R polyfuse; if it's still short, use a TPS2121. A good use for
    the spare ADC pin: monitor TERMPWR.

### Power budget (2026-09-24; regulator and supply choices accepted)

Currents per rail, **typical / max**. "Max" adds every part's maximum at once, which won't
happen in practice, so it's a ceiling rather than a forecast. Sources: RP2350 datasheet §14.9.7
(Table 1446) and §14.9.6 (I_IOVDD_MAX, I_QSPI_IOVDD_MAX); FT232H DS v2.0 Table 5.2;
CH334 English DS V2.5 §4.2. Figures marked * are from memory or estimated: check them when
the part is chosen.

**3.3 V rail**

| Load | Typ (mA) | Max (mA) | Basis |
|---|---|---|---|
| RP2350B core (VREG_VIN + VREG_AVDD) | 30 | 80 | Datasheet: 14.7 mA for hello_usb at 150 MHz; we run both cores + 3 PIO + DMA. Max = core regulator's 200 mA at 1.1 V, drawn from 3.3 V |
| RP2350B I/O (IOVDD, QSPI_IOVDD, USB, ADC) | 10 | 40 | Mostly switching current into CMOS inputs; the limits are 100 mA IOVDD and 20 mA QSPI |
| CH334P hub (external 3.3 V mode, see below) | 50 | 85 | DS: 42 mA with 1 HS downstream, 85 mA with 4 HS; we have 1 HS + 1 FS |
| PSRAM, APS6404L 8 MB QSPI* | 10 | 30 | JLC lists I_cc 7 mA; datasheet not yet read |
| QSPI flash* | 5 | 25 | W25Q-class read current |
| microSD* | 30 | 100 | SD default-speed limit (from memory); peaks during writes |
| SE front end (placeholder) | 20 | 40 | Front end still undecided (open question 5) |
| LA header buffers* | 2 | 10 | ~20 lines × C·V·f into the Digital Discovery inputs |
| LEDs (≈4 at 2 mA) | 6 | 10 | |
| TCA9555 | 0 | 1 | µA-class |
| **Total** | **≈165** | **≈420** | |

**5 V rail (`+5V_SYS`, after the ORing diode U1)**

| Load | Typ (mA) | Max (mA) | Basis |
|---|---|---|---|
| 3.3 V regulator input (linear, so I_in = I_out) | 165 | 420 | Table above |
| FT232H (VREGIN = 5 V) | 55 | 80 | DS: I_reg 54 mA at VREGIN 5 V. Max adds margin for the HS PHY |
| LM393 | 0.5 | 1 | |
| **Logic subtotal** | **≈220** | **≈500** | |
| TERMPWR (only when enabled) | ≈300 | 900 | Each asserted line draws ~21 mA from *each* terminator, and the far terminator may be powered from our TERMPWR too. 18 lines × 2 terminators ≈ 0.78 A; 900 mA is the SCSI-2 §5.4.3 capability we must offer |
| **Total** | **≈0.52 A** | **≈1.4 A** | 1.4 A × 5 V ≈ 7 W (R8 guessed ~6 W) |

**Against each source:**

| Source | Allowed | Fits? |
|---|---|---|
| USB-C at 3 A | 3 A | Yes, with lots of room |
| USB-C at 1.5 A (TERMPWR on) | 1.5 A | Yes: 1.4 A worst ceiling, ~1.3 A realistic worst. Thin but inside |
| USB-C Default / USB 2.0 (TERMPWR off by design) | 500 mA once configured | Yes typically (≈220 mA). The 500 mA ceiling touches the limit only if every maximum coincides |
| USB 2.0 before configuration | 100 mA | **No.** The hub, FT232H and RP2350 exceed it at enumeration. Many bus-powered hubs do the same and hosts rarely enforce it. Accepted as a known deviation |
| Bench 5 V | Supply-limited | Yes. Recommend a supply rated ≥ 2 A |

**Heat, worst case:** 3.3 V LDO (5.25 − 3.3) × 0.42 ≈ 0.8 W (typ ≈ 0.3 W); terminator LDO ≈ 0.95 W
(see "Terminator LDO"); ideal diodes ≈ 0.1 W. That's ~2 W worst, ~0.8 W typical. It's fine on a
4-layer board with copper pours under both SOT-223s. The printed case needs vents.

**3.3 V regulator (accepted 2026-09-24): a second TPS73701DCQR (C56848) set to 3.3 V.**
- It's the same part as the terminator LDO, so there's **no extra loading fee**. That's the same
  logic as the one-part LM66200 decision.
- 1 A rating (2.4× the ceiling), ~130 mV dropout at 1 A. It holds 3.3 V down to ~3.5 V in, so a
  sagging USB supply (≈4.4 V at the board with 1.5 A through a worst-case cable) isn't a problem.
- Accuracy: typical ±0.5 %; worst over line, load and temperature is ±3 % (legacy silicon) or
  ±1.5 % (new silicon), plus the feedback resistors.
- Rejected: **AMS1117-3.3** (C6186, the only basic LDO that can deliver the current): its 1.1–1.3 V
  dropout gives ≤ 3.1–3.3 V out from a 4.4 V input, below the CH334's 3.2 V minimum.
  **Buck converter**: the only no-fee part that fits (TPS54331, C9865) is non-synchronous, so it
  needs a Schottky diode and a large inductor, and it adds switching noise near the USB and crystal
  circuits. It would save ~0.5 W worst case, which isn't worth it at these currents.

**Supply choices this budget makes (accepted 2026-09-24):**
- **FT232H VREGIN from 5 V, not 3.3 V.** In 3.3 V mode, VREGIN must be 3.3–3.6 V (DS Table 5.2),
  and a 3.3 V LDO running slightly low would violate that. The 5 V mode accepts 3.6–5.5 V.
  VCCIO stays on the 3.3 V rail (2.97–3.63 V). Check the VPHY/VPLL wiring against the datasheet's
  bus-powered example at schematic time.
- **CH334P in external 3.3 V mode (V5 and VDD33 both on the 3.3 V rail).** With its internal
  LDO, V5 must be ≥ 4.5 V (DS §4.2), and the worst-case USB supply (≈4.4 V) misses that. WCH itself
  suggests this mode for industrial use, because it cuts the hub's dissipation from 85 mA × 5 V
  to 85 mA × 3.3 V (Chinese V2.91 §6.1). The trade-off: external mode needs 3.2–3.4 V, which is
  tighter than the LDO's worst-case ±3 % (typical ±0.5 % is well inside). Use 0.1 % feedback
  resistors to keep the resistor error out of it.
- The **TERMPWR polyfuse** must hold ≥ 0.9 A and trip at ≤ ~1.5 A (SCSI-2 recommends a 1.5 A limit).
  That feeds the open TERMPWR voltage-budget check (see "Ideal diodes").

### GPIO budget (first pass, dedicated pins, no role multiplexing)

| Block | Pins |
|---|---|
| SCSI data out: DB0–7 + P, per-bit open-drain enable | 9 |
| SCSI data in | 9 |
| SCSI control in: all 9 (needed for listen-only mode) | 9 |
| SCSI control out: ATN, ACK, SEL, BSY, RST | 5 |
| FT232H 245 FIFO: D0–7, RXF#, TXE#, RD#, WR# (+ SIWU) | 12–13 |
| microSD SDIO: CLK, CMD, D0–3, card detect | 7 |
| PSRAM chip select (QSPI CS1) | 1 |
| 2 LA marker pins, 2 LEDs (TERM_EN is a DIP switch; expander pin only if spare) | 4 |
| ~~Debug UART TX/RX~~: replaced by the CDC console over native USB (2026-09-24) | 0 |
| TERMPWR_OK digital input (pencilled in) | 1 |
| **Total** | **~57–58 of 48** |

**Over budget by about 10.** TERMPWR is switched in hardware from CC sense, which saves the TERMPWR_EN and CC ADC pins. Options (not yet decided):
- An I²C GPIO expander / ADC for slow signals (optional TERM_EN, LEDs, card detect,
  rail and CC monitoring): costs 2 pins, saves ~8–10. The biggest single lever.
- A USB-C CC detector chip with 2 digital outputs, instead of ADC on CC1/CC2.
- FT232H in FT1248 mode (1/2/4/8-bit bus) instead of the 8-bit FIFO. Pins = width + SCLK,
  SS_n, MISO (4-bit = 7, saving 5–6). AN_167: SCLK ≤ 30 MHz, 30 MB/s at 8-bit, so the raw
  rate is ~15 MB/s at 4-bit and ~7.5 MB/s at 2-bit (minus command/turnaround overhead). That's
  above the async FIFO's 8 MB/s at 4-bit. MIOSIO has internal pull-ups. Sustained USB rate
  is unmeasured, as it is for the FIFO.
- microSD in SPI mode instead of 4-bit SDIO: saves 2, but it's slower.
- Share each data bit's in/out on one pin. BlueSCSI does this, but it risks latching the bus
  (the receiver output would drive the driver enable) unless it's gated carefully. Not preferred.
- A second small MCU or a different USB bridge. That's a bigger change.

**Decided 2026-09-24 (open question 7): FT1248 4-bit + 1-bit SDIO + I²C expander.**

| Block | Pins |
|---|---|
| SCSI (data in/out, control in/out) | 32, GPIO 0–31 |
| FT232H FT1248, 4-bit: MIOSIO0–3, SCLK, SS_n, MISO | 7 |
| microSD 1-bit SDIO: CLK, CMD, D0 (D1–D3 pulled up, not wired to the MCU) | 3 |
| PSRAM CS1: GPIO 47 (erratum RP2350-E15: firmware must re-pad CS1 when it isn't on GPIO 0) | 1 |
| I²C to the expander (LEDs, card detect, TERMPWR_OK; spare pins for TERM_EN, DIP readback) | 2 |
| LA markers | 2 |
| **Total** | **47 of 48** |

- PIO allocation: PIO0 = SCSI at base 0; PIO1 = FT1248 and PIO2 = SDIO, both at base 16, so
  their pins sit in GPIO 32–47. Each block has 32 instruction slots. Estimates: SCSI ~20–30
  (listen and initiator programs can be swapped), FT1248 ~15–25 (no prior art), SDIO ~26
  (BlueSCSI's 4-bit SDIO is 10 + 8 + 8).
- IN/OUT pin groups must be consecutive within a window: plan the pin order before layout.
- BlueSCSI's SDIO is 4-bit only, and its firmware is GPL-3 (reference only), so the 1-bit
  SDIO and FT1248 PIO programs are ours to write.
- FT1248 SCLK: plan for 15–25 MHz (150 MHz / 6 = 25 MHz with a clean 50 % duty). Use
  `INPUT_SYNC_BYPASS` on the read pins. The FT232H's FT1248 AC timing isn't in datasheet v2.0 or
  AN_167, so the ceiling is found by measurement.
- **Expander: TCA9555PWR** (decided 2026-09-24). TI, TSSOP-24, 16 push-pull I/O that power
  up as inputs, 100 kΩ internal pull-ups, 400 kHz I²C, 4.7 kΩ bus pull-ups. C465732 (JLC
  extended; every I²C expander at JLC is extended), $0.69, ~40k LCSC stock (2026-09-24).
  INT goes to a test point + an unfitted 0 Ω link to the spare GPIO; firmware polls by default.
  Tentative pins: in = card detect, TERMPWR_OK, CC detector ×2 (if used), bench present,
  USB present; out = 2 status LEDs, TERM_EN (pencilled in), SD power enable (optional),
  FT232H reset, hub reset. The rest are spare.
  - **Unpowered behavior (datasheet, not measured):** the TCA9535/9555/6416A and the MCP23017
    all spec an I/O clamp for VO > VCC, so an unpowered expander pin clamps toward 0 V. None of
    them fixes the TERM_EN weak spot, so the accepted "documented limitation, no extra parts"
    stands. If that ever changes, a 74LVC1G34-class Ioff buffer (high-Z at VCC = 0) between
    the expander and DIP 2 would fix it.
  - Rejected: MCP23017 (C558584, $1.63, SSOP-28; GPA7/GPB7 output-only per DS20001952D; its
    interrupt capture and 1.7 MHz I²C aren't needed for slow, polled signals), TCA9535 (no
    pull-ups, ~2× the price), XL9555 clone (saves ~$0.16, unknown datasheet quality).
- Only one spare pin. **If pins free up (e.g. the SE front end allows shared data pins, ~8
  saved), switch microSD to 4-bit SDIO first** (+3 pins, ~4× bandwidth, BlueSCSI-proven).
  Going back to the 8-bit FIFO comes second (+5–6 pins).

**FT1248 fallback plan (2026-09-24, owner: "the retooling can be pretty drastic").** We're not
testing FT1248 on dev boards first. If it disappoints, the first board gets reworked, not respun.
The FT232H uses **the same pins** for FT1248 and the 245 FIFO (DS v2.0 Table 3.13 vs. §3.5.3):
MIOSIO0–7 = D0–D7 = pins 13–20; SCLK/SS_n/MISO = RXF#/TXE#/RD# = pins 21/25/26; the FIFO adds
WR# (27) and SIWU# (28). Dropping the **microSD (3 GPIO) and the I²C expander (2)**, plus the
spare (1), frees 6 pins. That's enough for either:
- **8-bit FT1248** (+4 pins; twice the bus width). The first fallback.
- **245 async FIFO** (+5, or +6 with SIWU#), if FT1248 itself misbehaves. Mode is an EEPROM setting.

Layout rules that keep this a bodge job, not a respin:
- **Pin order:** MIOSIO0–3 on GPIO *n*…*n*+3, and the SDIO and I²C pins on *n*+4…*n*+7, so
  after rework they become MIOSIO4–7 / D4–D7 on consecutive GPIOs (PIO `in`/`out` needs that).
  Keep all of them inside PIO1's window (GPIO 16–47).
- Route FT232H pins 17–20, 27 and 28 to pads (test points or DNP 0 Ω links toward those
  GPIOs), with a pull-up/down as the FT232H needs for unused inputs.
- Losing the expander loses the LEDs, card detect and TERMPWR_OK readback. The FT232H and hub
  resets must therefore default to "run" through pull-ups, never rely on the expander.

Verified (RP2350 datasheet, PIO GPIOBASE register, 2026-09-24): each PIO block sees a
32-GPIO window, and GPIOBASE selects base 0 or 16 only. It is set per block, so the SCSI can
use PIO0 at base 0 (GPIO 0–31) while the FT232H uses PIO1 at base 16 (GPIO 16–47). The 32
SCSI pins fill one window exactly, so pin ordering matters.

### FT232H pins in detail (datasheet v2.0 §3.5.3, §4.5)

Why FIFO rather than the FT232H's UART mode: UART mode tops out at 12 Mbaud (datasheet
§4.1). With 10 bits on the wire per byte, that's ≤ 1.2 MB/s, which is below R3 (1.5 MB/s). A UART
costs 2–4 pins; the FIFO costs 12 but reaches 8 MB/s.

Async 245 FIFO, which is the mode we plan to use. "RX" and "TX" are named from the FT232H's side.

| Signal | FT232H pin | Direction | Job |
|---|---|---|---|
| D0–D7 (ADBUS0–7) | 13–20 | both | Data byte. The FT232H drives it only while RD# is low; the MCU drives it to write |
| RXF# (ACBUS0) | 21 | FT → MCU | Low means a byte from the host is waiting to be read |
| TXE# (ACBUS1) | 25 | FT → MCU | Low means there's room to send a byte to the host |
| RD# (ACBUS2) | 26 | MCU → FT | Low puts the byte on D0–7; rising edge fetches the next one |
| WR# (ACBUS3) | 27 | MCU → FT | Falling edge latches D0–7 into the transmit FIFO |
| SIWU# (ACBUS4) | 28 | MCU → FT | Optional: a low strobe sends a short packet now. If tied high, the host's latency timer (settable down to 1 ms) flushes short packets instead |

That's 12 GPIO, or 13 with SIWU#. D0–D7 should be 8 consecutive GPIOs so one PIO `in`/`out`
instruction moves a byte. Timing: RD#/WR# low ≥ 30 ns and a ≥ 49 ns recovery, so ~80 ns per
byte at the pins. The USB side caps async FIFO at 8 MB/s. PIO at 150 MHz (6.7 ns per cycle)
meets this easily.

Pins that cost no MCU GPIO: the 93LC56B EEPROM (EECS/EECLK/EEDATA). **The EEPROM is required**,
because without it the FT232H comes up in UART mode. It's programmed over USB after assembly
(FT_PROG, or `ftdi_eeprom` on macOS/Linux). The 93LC46B is incompatible. Also RESET# and the
12 MHz crystal. ACBUS5/6/8/9 are free in this mode and can be set to "I/O mode" (CBUS bit-bang).

Rejected alternatives: **sync 245 FIFO** (40 MB/s) adds CLKOUT and OE# (14–15 pins) and
needs a 60 MHz synchronous interface, which is too tight for PIO and more than we need.
**FT1248** uses SCLK, SS#, MISO plus 1/2/4/8 MIOSIO lines (4, 5, 7 or 11 pins). Its
throughput at each width is unverified (it's in AN_167, not yet downloaded).

### MCU support parts (decided 2026-09-24, partial)

Part numbers reused from jackw01's **scanlight** (`sl_v4`, an RP2040 board, CERN-OHL-W). We
copy only the part choices; the schematic gets drawn fresh (MIT, see open question 8). Each part
below also matches "Hardware design with RP2350" (the guide), so it is valid for the RP2350B.
JLC stock and tier checked 2026-09-24.

| Function | Part | LCSC | JLC tier, stock | Guide cross-check |
|---|---|---|---|---|
| 12 MHz crystal | Abracon ABM8-272-T3 (3225, CL 10 pF, ESR ≤ 50 Ω, ±30 ppm) | C20625731 | extended, 16,990 | §4.1: the recommended crystal; Pico 2 is tuned for it |
| Crystal load caps ×2 | 15 pF C0G 0402 | C1548 | basic, 1.49 M | §4: 15 pF each (7.5 pF + ~3 pF stray ≈ 10 pF) |
| Crystal series resistor | 1 kΩ 1 % 0402 | C11702 | basic, 8.7 M | §4: 1 kΩ at IOVDD = 3.3 V stops overdrive |
| USB D+/D− series ×2 | 27 Ω 1 % **0603** (scanlight: 0402 C25100, extended) | C25190 | preferred (no fee), 126,830 | 27 Ω close to the chip |
| BOOTSEL + RUN buttons | **Open.** Likely the owner's own through-hole tact switches (~6 mm square, to be checked), hand-soldered and not JLC-assembled | — | — | — |
| BOOTSEL resistor | 1 kΩ (same as above) | C11702 | basic | QSPI_SS → 1 kΩ → button |
| RUN button resistor | 1 kΩ in series with the RUN button (guide R4) | C11702 | basic | Guide Appendix B. No external RUN pull-up (the guide fits none) |
| Core regulator inductor | Abracon AOTA-B201610S3R3-101-T, 3.3 µH, 2016, polarity-marked, Isat 2.4 A, DCR 115 mΩ | C42411119 | extended, 8,685 | Datasheet §6.3.8.2 names it; see conflicts |
| Regulator CIN, COUT, VREG_AVDD caps ×3 | 4.7 µF X5R 10 V 0402 | C23733 | basic, 2.6 M | Guide §2.1: 3 × 4.7 µF 0402 |
| VREG_AVDD filter resistor | 33 Ω 1 % 0402 | C25105 | basic, 2.2 M | Guide §2.1: 33 Ω + 4.7 µF |
| Decoupling ×13 | 100 nF X7R 50 V 0402 | C307331 | basic, 11.7 M | Guide Appendix B: one per supply pin (IOVDD ×8, DVDD ×3, ADC_AVDD), USB_OTP_VDD and QSPI_IOVDD share one (pins 68/69), plus one at the flash |
| 3.3 V bulk near the MCU | 10 µF X5R 25 V 0805 | C15850 | basic, 5.6 M | Guide C19: 10 µF 0805 X5R |
| QSPI flash | Winbond W25Q128JVSIQ, 16 MB, SOIC-8 208 mil | C97521 | **basic**, 44,238 | Guide §3.1: the same part; 16 MB is the most the RP2350 addresses |
| QSPI_SS pull-up | 10 kΩ 0402, **unfitted** (guide R1 is DNF) | C25744 | basic | Guide §3.1: unneeded with this flash; keep the pads |
| PSRAM CS1 pull-up (GPIO 47) | 10 kΩ 0402, **fitted** | C25744 | basic | Guide §3.2 (R13): "definitely needed", because GPIOs are pulled low at power-up |

- **Swapped to no-fee parts (2026-09-24, owner: "swap any components that are extended but
  don't need to be").**
  - 27 Ω: JLC has no basic or preferred 27 Ω in 0402, so we go up to 0603. That's fine next to
    the RP2350's USB pins.
  - Buttons: **deferred (2026-09-24).** The owner has through-hole tact switches in stock
    (thought to be 6 mm square) and will hand-solder them; they'll check the part before we
    pick a footprint. The no-fee fallback, if JLC should place them, is the TS-1187A-B-A-B
    (C318884, basic, 5.1 mm SMD, pressed from the top; used on scanlight `bsl_driver_v1.1`).
  - **The crystal stays extended.** The only no-fee 12 MHz crystal is YXC C9002 (CL 20 pF,
    ESR 80 Ω). That exceeds the guide's 50 Ω maximum, and the guide warns that any other
    crystal circuit "will require extensive testing".
- The ABM8-272-T3 probably suits the CH334 hub as well (see "USB hub"), giving one crystal type for the board. Accepted 2026-09-24.
- **Rest of the RP2350B support circuit (2026-09-24), from the guide** ("Hardware design with
  RP2350", RP2350B Minimal, Appendix B) **and datasheet §6.3.8.2**, swapped for JLC basic parts
  where the spec allows. Those are the rows from "RUN button resistor" down in the table above.
  - The guide's flash, W25Q128JVSIQ, is itself a JLC basic part (C97521). It costs $2.55, against
    ~$0.4 for a 2 MB part. A 16 MB part leaves room for A/B images plus logs. Smaller is an
    option if cost ever matters.
  - Supply pins on the QFN-80 (guide Appendix B pinout): IOVDD 5, 15, 24, 29, 41, 50, 60, 76;
    DVDD 10, 32, 51; ADC_AVDD 59; USB_OTP_VDD 68; QSPI_IOVDD 69; VREG_VIN 64, VREG_AVDD 61.
    The guide ties no filter to ADC_AVDD or USB_OTP_VDD beyond the 100 nF.
  - scanlight's 2.2 µF (C12530, basic) isn't in the RP2350 guide, so it's not used here.
  - Datasheet §6.3.8.2 also asks for CIN ≥ 4.7 µF with ≤ 50 mΩ, and COUT 4.7 µF ±20% with
    ≤ 250 mΩ and ≤ 6 nH. **Unverified:** a 10 V 0402 X5R loses a good share of its capacitance at
    3.3 V DC bias, so C23733 as CIN may land below 4.7 µF in practice. The guide uses the same
    0402 size and accepts this. The 0603 C19666 (4.7 µF 16 V, basic) is the fallback if the
    layout allows.
  - Layout rules to carry into KiCad: inductor orientation per datasheet Figure 23; the
    VREG_PGND return path; the ground cut-out under the VREG_LX net on layer 2 (Figure 24).
- **Core regulator inductor: Abracon, locked in 2026-09-24** (owner: lock it if under $1; it's
  $0.28, or $0.22 at 10+). JLC has **no basic or preferred 3.3 µH inductor at all** (searched 2026-09-24), so
  any choice is extended and pays the loading fee. We keep the guide's Abracon part: it's the
  only one on offer that is polarity-marked with a consistent reel orientation, which the
  datasheet says is required ("The inductor must be marked for polarity"). Cheaper extended
  look-alikes exist (e.g. Coilank APS201610M3R3F, C48783272, $0.03, Isat 3.2 A, DCR 250 mΩ;
  MetalLions MTQH201612S3R3MBT, C17701150, shielded, Isat 2.7 A, DCR 135 mΩ). Their polarity
  marking is unknown.
  - **Why no basic part exists:** JLC's entire no-fee inductor library is 13 parts (checked
    2026-09-24), all small multilayer signal/RF inductors (3.9 nH–100 µH) rated 2–500 mA. No
    power inductor of *any* value is basic or preferred. It isn't an RP2350-specific gap.
  - **Series combination from no-fee parts: no.** 2.2 µH (C1043) + 1 µH (C1042) ≈ 3.2 µH, but
    each is rated 50 mA against switching peaks of a few hundred mA, the pair's DCR is ~1 Ω
    against the ≤ 250 mΩ limit, and multilayer chips aren't the "fully shielded" part the
    datasheet requires (§6.3.8.2).
  - **Skip the inductor with an external 1.1 V supply: allowed, no gain.** The datasheet
    (§6.3.2, Figure 21) allows powering DVDD externally with VREG_FB grounded and no inductor.
    But the only no-fee LDO that goes low is the LM317 (minimum 1.25 V), and the TPS73701's
    minimum is 1.204 V. So this path also needs a new extended part, loses the firmware's
    core-voltage control (used for overclocking), and burns ~0.1 W. Rejected.
  - At schematic time: put a polarity mark on the footprint, and check that JLC's placement
    preview shows the dot the way datasheet Figure 23 wants.
- Still open:
  - nothing; PSRAM decided 2026-09-24 (see "PSRAM" below).
- 3.3 V regulator: decided 2026-09-24, see "Power budget".

### PSRAM (decided 2026-09-24): AP Memory APS6404L-3SQR-SN

- **C5333729**, 64 Mbit (8 MB) QSPI PSRAM, SOP-8, 2.7–3.6 V (the "-3" in the part number; the
  "-SQN" parts are 1.8 V and won't work on our 3.3 V QSPI_IOVDD). JLC extended, 5,052 stock, $3.96;
  LCSC 4,952 stock, $4.01 (2026-09-24).
- It's the part RP2350 boards with PSRAM commonly use. It sits on XIP_CS1n = GPIO 47 with the
  fitted 10 kΩ pull-up (see "MCU support parts"). Decouple it with 100 nF + 1 µF (confirm
  against its datasheet at schematic time).
- **No basic part, and nothing cheaper in the same class.** JLC's whole PSRAM category is
  extended. The only other SOIC 3.3 V option is the APS1604M-3SQR-SN (C18214056, 2 MB, $3.28),
  which would cut the stall buffer from ~5 s to ~1.3 s at 1.5 MB/s to save $0.68. The
  Lyontek/Espressif clones (LY68L6400, ESP-PSRAM64H) aren't stocked at JLC.
- Not yet read: the APS6404L datasheet (fetch it and add to `reference/` at schematic time).
  Its 8 µs maximum CE# low time (tCEM, from memory) limits burst length. The RP2350's QMI
  handles it with its `max_select` setting.

### Bench 5 V input protection (decided 2026-09-24): TI TPS259470ARPWR eFuse

What R8a needs: survive a wrong supply (reverse polarity, a 12 V or 24 V adapter, a bench knob
turned up) and pass only ~4.5–5.5 V on to U1 (LM66200, 6 V absolute maximum).

- **TPS259470ARPWR, C3662799**, TI, QFN-10 2 × 2 mm (HotRod, 0.45 mm pitch). JLC extended, 2,747
  stock, $1.28; LCSC 2,744 stock (2026-09-24). Datasheet SLVSFC9C in `reference/datasheets/`.
- What it gives (datasheet §1): operates 2.7–23 V, **28 V absolute maximum, withstands −15 V
  reverse polarity**, back-to-back FETs (28 mΩ) with true reverse-current blocking, **adjustable
  over-voltage lockout** (1.2 µs response, cuts the output off), adjustable current limit
  0.5–6 A, adjustable UVLO on EN, slew-rate (inrush) control, and a FLT open-drain output.
- Variant choice (datasheet §4): **470** = adjustable OVLO + active current limit;
  **A** = auto-retry after a fault (a bench user just fixes the supply, with no power cycle).
  Rejected: **472** (fixed 3.8/5.7/13.8 V output *clamp*; footnote 1 of the recommended
  operating conditions requires the input to stay at or below the clamp, so it doesn't tolerate a
  sustained 12 V); **474** (circuit breaker instead of current limit; fine, but limiting suits a
  bench supply better); **L** (latch-off: needs a power cycle).
- Settings to finish at schematic time: OVLO ≈ 5.7 V (above a 5.5 V bench setting, below U1's
  6 V absolute maximum; check the threshold tolerance), UVLO ≈ 4.3 V, current limit ≈ 2 A
  (the whole board's worst case is ~1.4 A), EN pull-up ≥ 350 kΩ because the input can go
  negative (recommended-conditions footnote 2). FLT goes to a spare expander input
  ("bench supply fault").
- Optional: an unfitted TVS footprint across the terminal for hot-plug spikes above 28 V.
- Rejected: TVS + polyfuse crowbar (all basic, but an SMBJ5.0A clamps near 9 V, above U1's
  6 V limit); discrete P-FET reverse protection + zener/transistor OV cut-off (all basic, but a
  loose threshold and 6+ parts to get right); 5.5–6.5 V-rated switches like TPS2553/AP2553 (an
  over-voltage *flag*, but they don't survive 12 V).

### TERMPWR switch and current limit (proposed 2026-09-24): a second TPS259470ARPWR, no polyfuse

The owner asked for a polyfuse. Working it through showed a polyfuse can't meet the spec, and
the eFuse already chosen for the bench input can.

- **The spec:** SCSI-2 §5.4.3 wants ≥ 900 mA available, and recommends limiting the current
  to 1.5 A.
- **Why not a polyfuse:** a PTC trips at roughly 2 × its hold current. Hold ≥ 0.9 A means a trip
  around 1.8–2.2 A, above the 1.5 A recommendation. It also drops 0.1–0.25 V, which is the
  weak spot in the TERMPWR voltage budget (see "Ideal diodes").
- **The eFuse instead (TPS259470ARPWR, C3662799, the same part as the bench input, so no new
  loading fee).** It replaces U2 (LM66200) and the polyfuse:
  - Current limit set by R_ILM: the datasheet gives 1.007 A at 3.32 kΩ and 2.03 A at 1.65 kΩ, so
    **≈ 2.74 kΩ gives ≈ 1.2 A (±10 % above 1 A: 1.08–1.32 A)**. That's ≥ 0.9 A and ≤ 1.5 A.
    Check the curve and the transient timer (ITIMER) at schematic time.
  - **R_ON 28 mΩ** (≈ 25 mV at 0.9 A), against LM66200 + polyfuse ≈ 0.15–0.3 V. The TERMPWR
    voltage-budget worry mostly goes away.
  - **True reverse-current blocking, including unpowered:** OUT leakage ≤ 4.86 µA with
    OUT = 12 V and IN = 0 V (datasheet, "Reverse current blocking"). Another device's TERMPWR
    can't backfeed our board (R2).
  - **The OVLO pin doubles as an active-low enable** (pin description: "can also be used as an
    Active Low Enable"). Our existing enable node is already active-low: pulled up to 5 V,
    pulled low by the wired-OR of CC_OK_N and the bench-present N-FET. So it wires straight to
    OVLO, with no inverter. Low (< 1.09 V) = on, high (> 1.2 V) = off.
  - EN/UVLO: a divider from IN sets under-voltage lockout (≈ 4.3 V), with ≥ 350 kΩ total.
  - FLT (open-drain) → a spare expander input: "TERMPWR fault" (overcurrent or short on the bus).
  - The TERMPWR LED stays on the enable node. The disable jumper (R2a) stays in series with the
    output.
- The TPS2121 fallback is no longer needed. The LM66200 part type stays (U1).

### Connectors (2026-09-24)

- **Board: 4 layers** (owner). Outline, dimensions and placement: the owner does the first
  layout pass by hand once the schematic exists.
- **USB-C:** the owner has their own connector kit (hand-soldered). Footprint: **HRO
  TYPE-C-31-M-12** (16-pin USB 2.0 receptacle, SMD pads + through-hole shell pegs; KiCad
  `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12`; LCSC C165948 for reference). It's the
  most common USB 2.0 Type-C footprint, used on scanlight too. CC1 and CC2 are separate pins,
  which our LM393 CC detection needs. The owner matches their part to it.
- **IDC50: a keyed, shrouded 2 × 25 box header, not a bare pin header.** A bare header works
  electrically (same 2.54 mm grid), but a ribbon can go on backwards. SCSI-2 plans for that
  (rev 10L connector table): reversed, TERMPWR (pin 26) lands on pin 25, which is **OPEN**, so
  nothing shorts. But every signal lands on a ground pin and the bus is dead. The shroud's key
  stops that for $0.19.
  - Part: BOOMELE C30006 (2 × 25 box header, through-hole; LCSC 280 stock, MOQ 5, $0.20;
    hand-soldered). Footprint `Connector_IDC:IDC-Header_2x25_P2.54mm_Vertical`.
- **HD50: no real part stocked at JLC or LCSC** (2026-09-24: the only "SCSI 50P" entries are
  zero-stock JLC placeholder records; the 1.27 mm hits are 2-row board-to-board headers, not
  half-pitch SCSI). It's a backup, unfitted footprint, so use a standard **right-angle PCB-mount
  half-pitch 50-pin female** footprint (e.g. the TE AMPLIMITE .050 or 3M 102xx family) and the
  owner sources a part to match later. Wire it by signal name: the SCSI-2 table gives HD50
  pin 38 = TERMPWR (vs. IDC50 pin 26).
- **microSD: SHOU HAN "TF PUSH", C393941.** Push-push, with card-detect pins, 2 mm tall.
  JLC extended, 217k stock, $0.066; LCSC 210k. Every microSD socket at JLC is extended (none
  are basic). Use the EasyEDA/LCSC footprint (pcbparts `cse_get_kicad`) and check it against the
  drawing. Rejected: Hroparts TF-01A (C91145, $0.19, no card-detect listed), Molex 503398
  ($1.14).

### ESD protection (2026-09-24)

Goal: protect what a person touches (USB-C, the SCSI connector, the bench terminal) using
**discrete diodes to ground with no rail pin**. A steering-diode array (SRV05-4 class) has a VCC
pin; tied to our rail, it would clamp the bus to 0 V when our board is off (violates R2).
All parts below are JLC **preferred** (no loading fee).

| Where | Part | LCSC | Why |
|---|---|---|---|
| USB D+, D− (×2) | H5VUD5BB, SOD-523, bidirectional, 0.3 pF, 5 V V_RWM | C20615820 | 0.3 pF is fine for 480 Mbit/s. Replaces the usual USBLC6-2SC6 (extended at JLC) |
| USB CC1, CC2 (×2) | H7VL10B, DFN1006, bidirectional, 7 V V_RWM, 20 pF | C20615787 | CC can sit at up to ~5.5 V from a host's pull-up; 7 V leaves room. CC tolerates hundreds of pF |
| USB VBUS (×1) | SMF6.0A, SOD-123FL, unidirectional, 6 V V_RWM | C19077499 | Above the 5.5 V VBUS maximum |
| SCSI signals (×18) | H5VUD5BB (same as D±) | C20615820 | 0.3 pF keeps us inside SCSI-2's 25 pF-per-signal budget (§5.4.1.2). 5 V V_RWM covers the ~2.8–3 V terminated bus. Bidirectional, so no conduction during normal swings |
| TERMPWR (×1) | SMF6.0A | C19077499 | TERMPWR ≤ 5.25 V |
| Bench terminal (×1, **not fitted**) | SMF15A, SOD-123FL | C19077509 | Clamps at 24.4 V, under the eFuse's 28 V absolute maximum. Unfitted by default because a fitted 15 V TVS would short a 24 V adapter, and the eFuse alone survives up to 28 V |

- Not protected: microSD (inside the case, card only), the LA header (buffered, and goes to a
  lab instrument), SWD (bench use). Add pads later if needed.
- Clamping voltages (10–25 V) are well above what the protected chips tolerate for DC. That's
  normal for ESD parts: they cut a kV-level pulse down to a level the chip's own ~2 kV HBM
  protection absorbs. Put them right at the connector, before any series resistor.
- Unverified: the SCSI capacitance budget depends on the front-end chips (undecided). Roughly:
  transceiver ~5–8 pF + LA buffer ~3–5 pF + terminator output ~5 pF + ESD 0.3 pF + traces ≈ 15–20 pF.

## SCSI electrical front end (candidates)

- The classic, proven choice: 74LS641-1 (open-collector, 48 mA sink) transceivers, as used by
  PiSCSI. It runs on 5 V and needs level care toward the 3.3 V MCU.
- Alternative: MOSFET/open-drain drivers plus Schmitt receivers (74LVC14 class). Study the
  ZuluSCSI and BlueSCSI schematics before choosing; check their licenses before reusing
  anything.
- **Termination (decided 2026-09-24): BlueSCSI v2's logic-chip terminator, redrawn.**
  A 2.85 V LDO feeds 74LVT245s whose A inputs are tied high, and their B outputs drive
  18 × 110 Ω to the bus lines. `/OE` is the enable. Two '245s give 16 channels. BlueSCSI
  handles the last two lines (DBP and I/O) with P-FETs (AO3401A, source on 2.85 V, gate on
  the same enable net). **Decided 2026-09-24: a third '245 instead (6 + 6 + 6 lines).** Why:
  - The saving is small. At 10+ the SN74LVTH245APWR (C2652121, JLC *extended*) costs
    ~$0.92 at JLC and $0.93 at LCSC, against 2 × AO3401A (C15127, *basic*) at ~$0.08 each.
    That's ~$0.75 per board. It matters at BlueSCSI's volume, not at ours. The extended-part
    loading fee is charged once per unique part per order, so a third copy adds none.
    Prices checked 2026-09-24. Stock is low: 939 at LCSC.
  - A P-FET isn't high-Z when unpowered. Its body diode runs from drain (bus side) to
    source (2.85 V). With our rail at 0 V, the far terminator backfeeds through 110 Ω and
    that diode, so two lines get loaded (R2). The LVT's Ioff doesn't have this problem.
    Inferred from the topology, not measured.
  - Six lines per package instead of eight cuts the current through each Vcc pin.
  - The FETs do save board area (2 × SOT-23 vs. a TSSOP-20), and BlueSCSI's 2.85 V rail can
    come from TERMPWR, which may be why the backfeed didn't bother them.
  Why this terminator at all:
  - It's proven on the same MCU family and assembled at JLC from ordinary logic parts.
  - It's easy to switch (R4b): with `/OE` high or the chip unpowered, the outputs go high-Z
    (LVT Ioff), so a powered-off board doesn't load the bus (R2).
  - It fits the SCSI-2 active-terminator window (§5.4.1: 100–132 Ω). 110 Ω plus the
    LVT's output resistance lands inside it, and the 2.85 V idle is above the 2.5 V minimum.
  Rejected: **dedicated terminator ICs** (UC5601/DS2107 class), which are hard to find and
  seldom stocked at JLC (unverified for us); **220/330 Ω passive**, which draws ~13 mA per
  line all the time, and needs a relay or FETs to switch it.
  To check when we draw it (unverified):
  - ~~LDO headroom~~: **decided 2026-09-24: TI TPS73701DCQR set to 2.80 V** (see "Terminator
    LDO").
  - **Current per package.** Up to 8 × 24 mA ≈ 190 mA through one '245 Vcc pin. BlueSCSI gets
    away with it, but check the datasheet. The '245 IOH spec (−32 mA) covers one line.
- **Terminator enable: a DIP switch (decided 2026-09-24).** One switch position grounds
  `/OE` (terminated), and a pull-up to 2.85 V turns it off, as in BlueSCSI. A switch keeps its
  state when the board is unpowered and costs no GPIO. An MCU-controlled `TERM_EN` is
  **pencilled in only**: we add it if a GPIO expander ends up with a spare pin. If we do,
  the switch and the expander pin need a clean way to combine (e.g. a 3-position "off / on /
  MCU" switch). The expander could also read the switch back so the host can report it.
  **Wiring, if the expander pin happens (decided 2026-09-24):** DIP 1 sets the default,
  and DIP 2 lets firmware change it.

  ```
  2.85 V ──10k──┬── /OE of all three '245s   (high = off)
                ├── DIP 1 ──1k── GND         (/OE ≈ 0.26 V = on)
                └── DIP 2 ──── push-pull expander pin
  ```

  | DIP 1, DIP 2 | Result |
  |---|---|
  | 00 | off, fixed |
  | 01 | off by default; firmware can turn it on |
  | 10 | on, fixed |
  | 11 | on by default; firmware can turn it off |

  DIP 1 is the default and DIP 2 is "firmware may change it", so both fixed states exist
  (00 and 10).
  - DIP 1 goes through 1k, not straight to ground, so a push-pull expander output can
    override it. The expander pin must be push-pull, not open-drain.
  - At reset, PCA9555/TCA9535-class expanders power up with their pins as inputs (from
    memory; verified 2026-09-24 for the TCA9555: "At power on, Pxx is configured as an
    input"), so the switch default holds. Firmware reads the
    pin to learn the default, then drives it only to change it.
  - A switch that silently lies is the main risk, and DIP 2 answers it: it plainly says
    "firmware may change this".
  - **Known limitation (acceptable; documented in `USAGE.md`):** with DIP 2 closed and our board unpowered, TERMPWR from another
    device keeps the 2.85 V rail alive. The dead expander's protection diodes then pull
    `/OE` low (on). That only matters in 01. Datasheet check done 2026-09-24: no candidate
    expander stays high-Z when unpowered (see the expander decision). So we rely on the documented
    rule "mid-chain and possibly off: use 00". Expected use is end-of-chain only (owner,
    2026-09-24), which uses 10 or 11 and never hits this. No extra parts for it.
  - Rejected: a two-position open-drain scheme (ON / MCU), where firmware could only turn
    termination on, never off.

## Open questions

1. ~~RP2350 + FT232H vs. Teensy 4.1 vs. STM32 HS~~: decided 2026-09-24: RP2350B + FT232H
   (see "Decision: the brains").
2. ~~Connector~~: decided on IDC50 plus an unpopulated HD50 footprint (2026-09-23).
3. ~~Enclosure / form factor~~: decided 2026-09-24: **3D-printed case, designed around the
   board later**. Placement (desk box vs. on the scanner) is left open. The v1 board shouldn't
   wait on it: external connectors (USB-C, IDC50/HD50, bench terminal, termination DIP, LEDs)
   on one or two edges, M3 mounting holes, and the LA header and SWD reachable with the lid
   off.
4. ~~TERMPWR~~: decided: we supply it via an ideal diode (R2a). Part: LM66200 (U2), decided 2026-09-24.
   The owner's pin-26 measurement is now nice-to-have.
5. SE front end: 74LVT pencilled in, pending the owner's independent research. **When this is
   decided, re-check the GPIO budget: any freed pins go to 4-bit SDIO first.** Terminator part of it decided 2026-09-24 (see front-end section).
6. ~~microSD vs. generic passthrough~~: decided 2026-09-24. Scanner logic lives on the host,
   always. The firmware is a generic passthrough, and microSD is for **spill only** (option A).
   Fallback (B), purely additive firmware: a script runner that executes a list of CDBs
   (host-generated or a recorded G4/SilverFast session) from USB or an SD file. Rejected (C):
   scanner logic in firmware. Choosing the scan area needs a preview and a UI, which belong
   on a host, not a board touchscreen. Early bring-up doesn't need B: CDBs can go over the
   native-USB CDC console before the FT1248 path works.
7. ~~GPIO budget~~: decided 2026-09-24: FT1248 4-bit + 1-bit SDIO + I²C expander, 47 of 48
   (see the GPIO budget section).
8. ~~Licensing~~: decided 2026-09-23: redraw from scratch and stay MIT. Use BlueSCSI (and
   ZuluSCSI) only as reading material; don't copy schematic, layout or firmware.
9. ~~USB PD voltage~~: decided: 5 V only, no step-up, and no PD controller needed. Still open:
   ~~the bench connector~~ (**decided 2026-09-24: 2-pin 5.08 mm screw terminal plus a test loop
   per pole**, hand-soldered from LCSC; clear +/− silkscreen. Rejected: loops only (clips pop
   off mid-scan), binding posts (revisit with the enclosure), barrel jack (9–12 V adapters would
   push the OV protection to 12–24 V)). **Ideal diodes decided 2026-09-24:
   LM66200 ×2** (see "Ideal diodes").
   **CC detection decided 2026-09-24: LM393 comparators** (see "CC detection" under Block
   architecture).
10. ~~USB path~~: decided 2026-09-24: a hub chip (see Block architecture). Still open: the
    hub part choice (**decided 2026-09-24: CH334P + 12 MHz crystal (ABM8-272-T3)**, see "USB hub"). Analysis kept for reference (2026-09-24, from the datasheets):
    - **Through the FT232H, firmware-mediated: viable.** The running app takes the image over
      the FIFO, writes the inactive half of an A/B partition pair, and reboots with
      FLASH_UPDATE. The bootrom's try-before-you-buy (RP2350 datasheet §5.1.17) rolls back if
      the new image doesn't call `explicit_buy()` within 16.7 s. Hardware cost: none. Weak
      spot: a new image that passes its self-test but has a broken update path needs SWD to
      recover. Mitigation: the self-test does a USB round trip before it calls
      `explicit_buy()`.
    - **Through the FT232H, MPSSE → SWD: possible, fiddly.** The FT232H can switch from FIFO to
      MPSSE at runtime (datasheet §4.13). OpenOCD's `ftdi` driver runs SWD on ADBUS0/1/2 with a
      resistor between TDI and TDO (unverified, from memory; the same goes for OpenOCD's
      RP2350 support). But those are D0–D2, which the RP2350 also drives, so the nets need
      isolation. A rescue reset (§3.5.8) parks the RP2350 in the bootrom so it stops driving
      the pins. Worth only as DNP 0 Ω links, as an experiment.
    - **RP2350 UART boot doesn't help.** It runs on the QSPI SD2/SD3 pins at a fixed 1 Mbaud
      and loads RAM only (§5.8), and the FT232H can't be a UART while it's in FIFO mode.
    - **Native USB through a hub chip: the most robust.** It gives ROM-level BOOTSEL (UF2 or
      picotool), which can't be bricked. `picotool reboot` avoids pressing a button, and a CDC
      console could replace the 2 debug-UART GPIOs. Cost: the hub IC, a crystal and passives.
      It uses no GPIO.

## Log

- 2026-09-23: Initial requirements and brains analysis drafted.
- 2026-09-23: Absorbed the snooper role (R4a, R4b). There's no host switch; we rely on
  SCSI multi-initiator instead.
- 2026-09-23: Block-architecture round 1: high-speed USB via external bridge, USB-C power,
  on-board PSRAM, IDC50 plus HD50 footprint.
- 2026-09-23: Round 2: RP2350B, microSD, TERMPWR recommendation (pending measurement), LVT
  pencilled in. Read BlueSCSI v2 (`prior-art/bluescsi-v2.md`); first GPIO budget is over by ~10.
- 2026-09-23: Licensing: redraw from scratch, keep MIT.
- 2026-09-23: Added the SCSI-2 rev 10L draft to `reference/standards/`. It makes TERMPWR mandatory for initiators (≥900 mA), confirms 0.2 V hysteresis, and corrects the 3 m fast-cable claim.
- 2026-09-23: TERMPWR accepted (ideal diode, R2a). Power via USB-C PD (R8).
- 2026-09-23: Power revised: 5 V from USB-C (CC advertisement, no PD) plus a protected bench 5 V input (R8, R8a).
- 2026-09-23: First block diagrams (`blocks/`). GPIO budget revised to ~64–65 of 48.
- 2026-09-23: TERMPWR enable moved to hardware (CC_OK OR bench) with an LED; budget ~60–61 of 48.
- 2026-09-23: TERMPWR_OK input pencilled in; GPIO budget to be resolved later.
- 2026-09-24: Downloaded the RP2350 and FT232H datasheets (`reference/datasheets/`). Wrote up
  the FT232H FIFO pin detail and verified the PIO window and the CS1n pins. Analysed firmware-update
  paths (open question 10).
- 2026-09-24: Decided on a USB 2.0 hub (FT232H + RP2350 native USB over one USB-C), with a
  CDC console replacing the debug UART. GPIO budget is now ~58–59 of 48.
- 2026-09-24: Diagram format: ASCII chosen over Mermaid, D2 and hand-drawn SVG (a trial of all
  four). The script now checks layouts and keeps the input readable (`blocks/_src/build.py`).
  Added page 4 (USB).
- 2026-09-24: Terminator decided: 2.85 V LDO → 74LVT245 (inputs high) → 18 × 110 Ω, as BlueSCSI v2.
- 2026-09-24: Terminator enable is a DIP switch; TERM_EN only via a spare expander pin. Leaning to a third '245 over P-FETs. GPIO budget ~57–58 of 48.
- 2026-09-24: Third '245 locked in (no P-FETs). Proposed two-DIP-position enable (ON / MCU) if the expander pin happens.
- 2026-09-24: Terminator enable wiring: DIP 1 = default (via 1k), DIP 2 = firmware may override via a push-pull expander pin.
- 2026-09-24: Started `USAGE.md` (board docs) with the termination switch settings. Expected use is end-of-chain.
- 2026-09-24: Accepted RP2350B + FT232H (open question 1). A one-chip STM32 HS was reconsidered for GPIO and rejected (no PIO).
- 2026-09-24: GPIO budget decided: FT1248 4-bit, 1-bit SDIO, I²C expander (47/48). AN_167 fetched: FT1248 SCLK ≤ 30 MHz.
- 2026-09-24: Open question 6 decided: passthrough accepted, SD = spill (A), script runner (B) as a later add-on.
- 2026-09-24: Expander: TCA9555PWR. No expander is high-Z unpowered; the TERM_EN limitation stays documented, with no extra parts.
- 2026-09-24: CC detection: LM393 comparators (0.66 V threshold, CC_OK_N wired-OR). TUSB321 was the alternative; ADC rejected (needs firmware).
- 2026-09-24: Ideal diodes: one part type, LM66200 ×2 (U1 ORing, U2 TERMPWR switch with a wired-OR enable). LM66100 rejected (conducts when disabled).
- 2026-09-24: Terminator LDO: TPS73701 at 2.80 V (SCSI-2 §5.4.1(b)(3) caps V_term at ~2.96 V). 3.3 V + divider rejected.
- 2026-09-24: Hub: CH334P with a fitted 12 MHz crystal (WCH: crystal-free may break USB spec and may not be enabled).
- 2026-09-24: Bench connector: 5.08 mm screw terminal + test loops.
- 2026-09-24: Enclosure: 3D-printed case later; v1 is a bench board with edge connectors and M3 holes.
- 2026-09-24: MCU support parts: crystal circuit, USB 27 Ω and buttons reused from scanlight `sl_v4` (part numbers only; it's an RP2040 board, so the core regulator, flash and decoupling are still open).
- 2026-09-24: Swapped the extended MCU support parts for no-fee ones: 27 Ω → 0603 C25190, buttons deferred (owner's through-hole stock). The ABM8-272-T3 crystal stays (no no-fee crystal meets ESR ≤ 50 Ω).
- 2026-09-24: CH334 internal load caps are ~16 pF (Chinese V2.91 §6.1), which matches a CL 10 pF crystal. Accepted: ABM8-272-T3 for both the RP2350 and the hub, with unfitted load-cap pads on the hub.
- 2026-09-24: Rest of the RP2350B support parts per the RP2350 guide, basic where possible: W25Q128JVSIQ (basic), 13 × 100 nF, 3 × 4.7 µF, 33 Ω, 10 µF bulk, 10 kΩ pull-ups. Conflict: no basic 3.3 µH inductor exists, so the Abracon part stays (extended).
- 2026-09-24: Power budget drafted: 3.3 V ≈165/420 mA, 5 V ≈0.52/1.4 A with TERMPWR. Proposed: a second TPS73701 for 3.3 V, FT232H VREGIN from 5 V, CH334 in external 3.3 V mode.
- 2026-09-24: FT1248: no dev-board test (owner). Assume it works as advertised; fall back to bodge wires or cut traces on the first board if needed.
- 2026-09-24: Accepted: 3.3 V = second TPS73701, FT232H VREGIN from 5 V, CH334 in external 3.3 V mode. Inductor: Abracon kept for now; JLC has no no-fee power inductor of any value, and series or external-1.1 V workarounds don't help.
- 2026-09-24: FT1248 fallback plan: drop microSD + expander to free 6 GPIO for 8-bit FT1248 or the 245 FIFO; pin-order and pad rules recorded under the GPIO budget.
- 2026-09-24: PSRAM: APS6404L-3SQR-SN (8 MB, 3.3 V). Bench input protection: TPS259470ARPWR eFuse (−15 V/28 V tolerant, adjustable OVLO). Abracon inductor locked in ($0.28).
- 2026-09-24: 4-layer board; layout is the owner's hand pass after the schematic. Connectors: USB-C footprint HRO TYPE-C-31-M-12 (owner's part), IDC50 keyed box header C30006, HD50 generic footprint (not stocked), microSD C393941. ESD: discrete preferred diodes (no rail pin). TERMPWR: proposed second TPS259470A instead of LM66200 U2 + polyfuse.
