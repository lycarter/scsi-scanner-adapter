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
- **To check at schematic time:** the crystal CL has to match the internal caps (their value
  wasn't in the parts I read). Candidate: YXC X322512MSB4SI (C9002, JLC's only basic 12 MHz,
  3225, CL 20 pF, ESR 80 Ω). Confirm against the English datasheet or a WCH reference
  design. One crystal type for the whole board is unlikely: the RP2350 guide strongly
  recommends the ABM8-272-T3 (CL 10 pF, ESR ≤ 50 Ω), and C9002's 80 Ω exceeds that.
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
    hub part choice (**decided 2026-09-24: CH334P + 12 MHz crystal**, see "USB hub"). Analysis kept for reference (2026-09-24, from the datasheets):
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
