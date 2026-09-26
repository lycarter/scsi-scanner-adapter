# Phase 3: Driver PCB (USB-C ↔ SCSI initiator)

Goal: a board that plugs into a modern computer over USB-C and acts as the SCSI
**initiator** for the D4000. It also serves as the **bus snooper**. The separate snooper PCB
was dropped on 2026-09-23: the G4, the scanner and this board share one multi-initiator
chain (see `design_docs/1-bus-capture/NOTES.md` for the topology).

## Requirements (draft)

- R1: **SCSI-2 narrow SE initiator.** Async is mandatory; sync (5–10 MB/s) is optional and
  only needed if the scanner negotiates it or async proves too slow. It handles selection,
  arbitration, message phases, disconnect/reselect, and parity generation and checking.
- R2: **SE electricals.** The drivers sink 48 mA, open-collector. The receivers have
  hysteresis (≥0.2 V). Active termination (switchable) is on board. It must be safe when
  unpowered (no backfeed, no bus clamping).
- R2a: **TERMPWR supplied by the board** (we're the initiator; SCSI-2 §5.4.3 requires it):
  4.25–5.25 V at the connector, ≥900 mA source capability, through an **ideal diode**
  (no backflow), with a current limit (≤1.5 A recommended; an eFuse since 2026-09-24, see
  "TERMPWR switch") and a jumper to disable it.
- R3: **Sustained throughput ≥ 1.5 MB/s** end to end, host to scanner, based on the estimate
  in `docs/scanner-facts.md`. Target 3–5 MB/s for margin. Phase 2 will measure the real number.
- R4: **Listen-only mode.** The receivers can monitor the bus without driving it, which makes
  the board a long-capture protocol sniffer for Phase 2. **Protocol mode traces every phase,
  DATA included, async and sync** (owner, 2026-09-26 review R013): one record per REQ/ACK
  handshake. A short edge-level mode captures triggered windows into RAM.
- R4a: **Buffered LA header.** All 18 signals come out through Schmitt buffers
  (3.3 V CMOS), pinned to match the Digital Discovery's 2×16 input connector, plus marker
  pins driven by firmware (e.g. "CDB start", "error"). This replaces the old snooper board.
- R4b: **Multi-initiator friendly.** The SCSI ID is configurable (default 6). The board never
  asserts RST unless told to, tolerates another initiator's traffic, and its termination is
  switchable, so it works at the chain end or mid-chain.
- R5: **Host interface over USB-C** that needs no custom kernel drivers on macOS, Linux or
  Windows. That means vendor-class bulk with WinUSB/MS OS 2.0 descriptors, or CDC/NCM.
  (Still the requirement, owner 2026-09-26. The FT232H path uses FTDI's own Windows Update
  driver on Windows and, preferably, Apple's built-in serial driver on macOS; a bench test
  decides the macOS path, see `design_docs/4-software/NOTES.md` and design review R052/R053.)
- R6: Firmware updates over USB without special hardware. SWD for debugging (Tag-Connect TC2030 pads, decided 2026-09-25).
- R7: Everything JLC-assemblable from LCSC stock where possible.
- R8: **5 V power from USB-C.** Typical hosts are computers that offer 5 V at 1.5 A, maybe
  3 A, and rarely anything above 5 V. So the board runs on **5 V only** and reads the
  USB-C CC current advertisement (0.5/0.9 A default, 1.5 A, 3 A) to learn its budget. A full
  USB PD controller isn't required, because 5 V at up to 3 A is signalled over CC without PD
  (from memory: verify). Budget: the rough worst case is ~6 W; 1.5 A (7.5 W) should do. On a
  default-current port (≤0.9 A), keep TERMPWR off and report why rather than brown out.
- R8a: **Bench 5 V input for extra current.** Clip-friendly terminals, **reverse-polarity and
  over-voltage protected**. USB stays connected (it's the data link); when the bench supply is
  present it **takes over** the whole board through a priority power mux (TPS2116, 2026-09-26),
  and neither source can backfeed the other. A USB device must never drive VBUS.

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

Parts list for the schematic: `parts-list.md` (the reasoning stays here).

Diagrams: `blocks/0-overview.md`, `1-power.md`, `2-scsi-frontend.md`, `3-mcu-support.md`,
`4-usb.md`, `5-rp2350-pinout.md` (the pin map, drawn with `chip45()`). Each is generated from a page source in `blocks/_src/` (named boxes and links)
by `python3 design_docs/3-driver/blocks/_src/build.py`. The build checks the layout (no overlaps, wires
touch the boxes they name) and writes a connection list under each diagram. To learn what a
diagram says, read its source or that list rather than the art.

Decided with the owner on 2026-09-23:

- **USB: over-spec for high speed.** The RP2350's built-in USB is full-speed only (12 Mbit/s),
  so high speed needs an external bridge. Working choice: FT232H in async FIFO mode (~8 MB/s).
  We build it now rather than waiting for Phase 2 to show whether full speed would do.
- **Power: 5 V from USB-C** (R8, reading the CC current advertisement), plus a **bench 5 V
  input** (R8a) for extra current. A priority mux (bench first) joins them (2026-09-26; was
  ideal-diode ORing). Budget: "Power budget".
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
- **SE drivers (decided 2026-09-25): 14 × onsemi FDV301N discrete N-MOSFETs, open-drain on
  every line we drive**, with the SN74LVTH125PWR as the recorded fallback. **Receivers
  (decided 2026-09-25): 18 × Nexperia 74LVC1G17GW**, fallback 3 × Nexperia 74LVC14APW. Each
  bus line gets its own small cluster of parts. See "SCSI drivers" and "SCSI receivers" under
  the front-end section.

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

### Terminator LDO (decided 2026-09-24): TI TPS73701, now at 2.83 V (2026-09-26)

**Update 2026-09-26 (design review R023/R083/R042/R086):** the rail moves to **2.83 V
(R1 = 39 k + 5.6 k, R2 = 33 k; R1‖R2 = 19 kΩ as TI recommends)** with a **270 Ω 0603 bleed**
(≈ 10.5 mA, 30 mW) to GND.
- Why 2.83 V: the SN74LVTH245A needs VCC ≥ 2.7 V, and at 2.80 V the worst case reached 2.69 V
  (V_OH then ≥ 2.49 V, under SCSI-2's 2.5 V released-line minimum). 2.831 V × (±3 % legacy
  silicon ± 1 % divider) = **2.72–2.94 V**, which clears 2.7 V and stays under the 2.96 V
  ceiling. New silicon (±1.5 %) gives 2.76–2.90 V.
- The ceiling comes from §5.4.1(b)(3), which is a **44.8 mA total for both terminators** into a
  line asserted at 0.5 V, not 22.4 mA each. Even at 2.94 V and R_out = 0, ours is
  (2.94 − 0.5)/108.9 Ω = 22.4 mA; the LVTH output resistance brings it lower.
- Why the bleed: the TPS737's accuracy is specified only for I_OUT ≥ 10 mA (the idle bus draws
  ~0.7 mA), it has no active pull-down (overshoot after a load drop decays with τ ≈ 0.24 s
  without a bleed), and it can't sink current pushed in from the bus by an active-negation
  driver. 10.5 mA of bleed fixes all three. It comes out of TERMPWR (terminator power is
  exempt from SCSI-2's 1 mA limit).
- The text below is the original 2.80 V analysis, kept for the reasoning.

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
- ~~To check when we draw it: an LDO can't sink~~: settled 2026-09-26, the 270 Ω bleed above.
  Scope the rail at bring-up, including during the G4 captures (the Adaptec may use
  active negation).

### CC detection (decided 2026-09-24): LM393 dual comparator

CC_OK drives the hardware TERMPWR enable (`CC_OK OR bench present`, no MCU). A copy goes to
an expander input so firmware can explain a dead bus ("port only offers 500 mA").

- Thresholds (TUSB321 datasheet, the Type-C sink values): **0.66 V** = Default vs. 1.5 A,
  1.23 V = 1.5 A vs. 3 A. Only 1.5 A is detected, which covers the budget. Window: Default
  reads ≤ ~0.61 V, 1.5 A reads ≥ ~0.70 V, so the threshold has about ±40 mV of room.
- Circuit (values final, 2026-09-25):
  - 5.1 kΩ 1 % Rd from CC1 and CC2 to GND.
  - **Each CC goes through 10 kΩ / 1 µF (τ = 10 ms)** into the inverting input of one LM393
    half.
  - The shared reference sits on the + inputs. A **CJ431 (C3113, basic)** shunt reference,
    biased from 3.3 V through **470 Ω** (≥ 1.21 mA even at 3.16 V with V_ref at its 2.525 V
    maximum; its I_KA(min) is 1.0 mA), gives **2.500 V** nominal (CJ431 datasheet: 2.475–2.525 V;
    the 0.5 % rank is 2.487–2.513 V, and the LCSC listing doesn't say which rank C3113 is).
    That's divided by **13.3 kΩ (10 k + 3.3 k) / 4.7 kΩ** to 0.653 V. **No capacitor on the
    CJ431 cathode** (TL431-class shunts go unstable with some load capacitance); if the tap
    ever needs filtering, put the cap on the 0.65 V tap, behind 13.3 kΩ.
  - **1 MΩ** from the wired-OR node to the reference node gives ~10 mV of hysteresis. (The node
    now sits at ≈ 3.0 V when high, not 3.3 V, because of the OVLO divider; see "TERMPWR switch".)
  - The open-collector outputs are wired together **directly onto the TERMPWR enable node**
    (10 kΩ pull-up to 3.3 V; see "TERMPWR switch"). So the node is CC_OK_N wired-OR with the
    bench-present FET.
- **Worst case (recomputed 2026-09-26, design review R087):** nominal **0.661 V rising / 0.651 V
  falling**. With 1 % resistors, the rail at 3.16–3.44 V, node low 0–0.4 V, onsemi LM393 V_IO
  ±9 mV and I_IB ≤ 400 nA over 0–70 °C, and the CJ431's full 17 mV tempco taken one-sided:
  - 0.5 % rank: rising ≤ 0.689 V, falling ≥ 0.620 V → **+10/+11 mV** inside the 0.61–0.70 V window.
  - 1 % rank: rising ≤ 0.692 V, falling ≥ 0.617 V → **+6/+8 mV**.
  Thinner than the +15 mV first claimed (which used TL431's 2.495 V and ±0.8 % tempco), but
  inside. Check the reel label for the rank at bring-up.
- **Why these changes (2026-09-25):**
  - With the reference taken from the 3.3 V rail, *no* 1 % divider passed worst case. The
    rail's ±3 % alone moves 0.655 V by ±20 mV.
  - The classic LM393's input bias current is up to 250 nA (TI LM393 family table: 25 typ /
    250 max). Through the planned 100 kΩ that's a 25 mV error, half the window. 10 kΩ with
    1 µF keeps τ = 10 ms at 1/10 of the error.
- Part: **LM393DR2G, C7955, JLC basic**, $0.07, ~240k stock. Everything else is basic
  passives.
- ~~Error budget: ±15–20 mV~~: that was optimistic. See the worst case above.
- **To check when we draw it (unverified):**
  - Supply the LM393 from the 5 V rail (+5V_SYS), not 3.3 V. Its input common-mode range tops
    out at Vcc − 1.5 V, and a 3 A port puts up to ~2.04 V on CC. The output pull-up still
    goes to 3.3 V.
  - If the host tries PD, its messages swing CC between ~0 and ~1.1 V for about 1 ms. The
    10 ms RC should average that to a dip of ~20 mV, inside the hysteresis. Verify against
    the Type-C/PD spec timing.
  - A legacy USB-A to C cable has a 56 kΩ pull-up, which reads ~0.42 V ("Default"). No
    TERMPWR from USB then: documented in `USAGE.md` (use the bench input).
  - A **non-compliant** A-to-C cable with a 10 kΩ pull-up reads 1.69 V ("3 A") and would enable
    TERMPWR on a 500 mA USB-A port. Hardware can't tell; `USAGE.md` says to use a C-to-C cable
    or the bench input.
- Rejected: **TUSB321** (C139392; OUT1 is CC_OK directly, but extended, $1.18, a 1.6 mm
  X2-QFN; the owner preferred the all-basic discrete design); **ADC** (an expander with an ADC or
  the RP2350 ADC: needs firmware, which breaks the "no MCU in the enable path" decision);
  **transistor Vbe threshold** (±50 mV spread and −2 mV/°C drift is wider than the window).
- Zero-cost option for the pin plan, not decided: put the spare GPIO on an ADC-capable pin
  (GPIO 40–47) for TERMPWR or VBUS monitoring.

### Ideal diodes (decided 2026-09-24): one part type, TI LM66200 ×2

**Update 2026-09-24 (accepted): U2 and the polyfuse are replaced by a TPS259470A eFuse; see
"TERMPWR switch".**

**Update 2026-09-26 (design review R068): U1 is replaced by a TPS2116 priority mux; see "Power
mux". The LM66200 leaves the board.** ORing picks whichever input is higher, so with the bench at
5.0 V and USB at 5.0–5.25 V, USB usually won. Then "bench present" enabled TERMPWR while USB
carried it, even on a 500 mA port. The owner wants the bench to take over when it's connected.
The section below is kept for the reasoning.

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
  - ON logic thresholds: we first thought they weren't in the datasheet; they are (V_ON 0.8/1.0/1.2 V, SLVSG04 §6.5). Pulling ON up to 5 V avoided the
    question. The copy of CC_OK_N for the expander needs its own 3.3 V path.
  - U2's unused input: parallel VIN1 and VIN2, or tie VIN2 off? The datasheet doesn't say.
  - Reverse blocking with our board unpowered while another device drives TERMPWR. Likely
    (true Hi-Z off), not confirmed.
  - **TERMPWR voltage budget:** VBUS at the host can be as low as 4.75 V, minus cable drop,
    minus U1 + U2 (~0.1 V at 0.9 A), minus the polyfuse (~0.1–0.25 V), against SCSI-2's
    4.25 V minimum. Pick a low-R polyfuse; if it's still short, use a TPS2121. A good use for
    the spare ADC pin: monitor TERMPWR.

### Power mux (decided 2026-09-26): TI TPS2116, bench input has priority

- **TPS2116DRLR, C3235557**, TI, SOT-583 (the LM66200's package), JLC extended, $0.40, ~85k stock
  (2026-09-26). 1.6–5.5 V, 2.5 A continuous, 40 mΩ typ, reverse-current blocking when VOUT > VINx,
  controlled output slew (~1.7 ms to 5 V), thermal shutdown. Datasheet SLVSFG1A
  (`reference/datasheets/tps2116.pdf`). Still one ideal-diode/mux part type on the board.
- **Wiring (priority mode, §7.6):** VIN1 = bench eFuse output, VIN2 = USB VBUS, **MODE tied to VIN1**,
  **PR1 from VIN1 through 100 k / 39 k** (0.281 × VIN1). V_REF is 0.92–1.08 V, so VIN1 counts as
  present above 3.56 V nominal (3.24–3.90 V worst). The bench eFuse output is either 0 V or
  ≥ 4.05 V (its UVLO minimum), so whenever the bench is live, PR1 > V_REF and **VIN1 powers the
  board whatever VIN2 is**. With the bench absent, MODE = PR1 = 0 and the mux runs from VIN2.
- **ST** (open-drain, pulled up 10 kΩ to 3.3 V) is high while VIN1 is in use → expander P02
  PWR_SRC (1 = bench).
- **TERMPWR enable is unchanged:** the bench-present 2N7002 (gate from the bench eFuse output)
  now means "bench is powering the board", because priority mode makes the two the same.
- **Caps:** VIN1 1 µF (shared with the bench eFuse OUT); VIN2 1 µF + the VBUS snubber below;
  VOUT 100 nF + 22 µF bulk on +5V_SYS (soft start ≈ 1.7 ms → ≈ 65 mA inrush).
- **VBUS snubber (design review R074):** the TPS2116, like the LM66200, is rated 6 V absolute, and
  no TVS can clamp a 5.5 V rail below 6 V (the SMF6.0A starts at 6.67 V). Plug-in ringing
  (cable L into a low-ESR MLCC) is damped instead: **1 Ω (0603) in series with 4.7 µF (0805,
  25 V)** from VBUS to GND, next to VIN2's 1 µF. That's R ≈ √(L/C) for ~1 µH of cable into 1 µF,
  and 5.7 µF total, under USB's 10 µF attach limit. Scope VBUS at plug-in at bring-up.
- **To check at schematic/bring-up:** the output dip when the bench is unplugged (switchover,
  §7.5): 22 µF at ~0.5 A gives ~66 µs before +5V_SYS falls 1.5 V, which the 3.3 V LDO rides
  through. §7.4: if VIN1 collapses faster than 1 V/10 µs, VIN2 must be ≥ 2.5 V (it is, USB).
- Rejected: **TPS2121** (priority mux with 24 V rating and adjustable current limit, $1.04,
  VQFN-HR): more than needed, since the bench side already has an eFuse; the owner picked the
  TPS2116. **Keep LM66200 + ST enable:** the bench would have to be set above USB (≈ 5.4 V) to be
  used, which fights the lowered bench OVLO.

### Power budget (2026-09-24; regulator and supply choices accepted; updated 2026-09-26)

Currents per rail, **typical / max**. "Max" adds every part's maximum at once, which won't
happen in practice, so it's a ceiling rather than a forecast. Sources: RP2350 datasheet §14.9.7
(Table 1446) and §14.9.6 (I_IOVDD_MAX, I_QSPI_IOVDD_MAX); FT232H DS v2.0 Table 5.2;
CH334 English DS V2.5 §4.2. Figures marked * are from memory or estimated: check them when
the part is chosen.

**3.3 V rail**

| Load | Typ (mA) | Max (mA) | Basis |
|---|---|---|---|
| RP2350B core (VREG_VIN + VREG_AVDD) | 30 | 115 | Datasheet: 14.7 mA for hello_usb at 150 MHz; we run both cores + 3 PIO + DMA. Max = core regulator's 200 mA at 1.1 V at 59 % efficiency (Table 1442) ≈ 113 mA from 3.3 V (2026-09-26; was 80) |
| RP2350B I/O (IOVDD, QSPI_IOVDD, USB, ADC) | 10 | 40 | Mostly switching current into CMOS inputs; the limits are 100 mA IOVDD and 20 mA QSPI |
| CH334P hub (external 3.3 V mode, see below) | 50 | 85 | DS: 42 mA with 1 HS downstream, 85 mA with 4 HS; we have 1 HS + 1 FS |
| PSRAM, APS6404L 8 MB QSPI | 10 | 30 | Datasheet Table 9: I_CC ≤ 7 mA read/write; 30 is generous |
| QSPI flash | 5 | 25 | W25Q128JV §9.4: ≤ 20 mA read at 104 MHz, ≤ 25 mA program/erase |
| microSD* | 30 | 200 | 100 mA is the default-speed limit; High Speed (which the firmware plans for) may draw up to ~200 mA (from memory, unverified) |
| SE front end | 20 | 40 | Kept as margin: FET drivers and 18 × 74LVC1G17 draw < 1 mA static (I_CC ≤ 40 µA each at 125 °C, unverified exact); switching adds a little |
| LA header drive (via 100 Ω)* | 2 | 10 | ~20 lines × C·V·f into the Digital Discovery inputs |
| LEDs (≈4 at 2 mA) | 6 | 10 | |
| TCA9555 | 0 | 1 | µA-class |
| **Total** | **≈165** | **≈555** | Was ≈420 before the 2026-09-26 corrections |

**5 V rail (`+5V_SYS`, after the power mux U1)**

| Load | Typ (mA) | Max (mA) | Basis |
|---|---|---|---|
| 3.3 V regulator input (linear, so I_in = I_out) | 165 | 555 | Table above |
| FT232H (VREGIN = 5 V) | 55 | 80 | DS: I_reg 54 mA at VREGIN 5 V, including its own 3.3 V (VCCD) for I/O, PHY and EEPROM. Max adds margin for the HS PHY |
| LM393 | 0.5 | 1 | |
| **Logic subtotal** | **≈220** | **≈640** | |
| TERMPWR (only when enabled) | ≈310 | 910 | Each asserted line draws ~21 mA from *each* terminator, and the far terminator may be powered from our TERMPWR too. 18 lines × 2 terminators ≈ 0.78 A; 900 mA is the SCSI-2 §5.4.3 capability we must offer. Plus the 10.5 mA terminator bleed |
| **Total** | **≈0.53 A** | **≈1.55 A** | Ceiling; 1.55 A × 5 V ≈ 7.8 W (R8 guessed ~6 W) |

**Against each source:**

| Source | Allowed | Fits? |
|---|---|---|
| USB-C at 3 A | 3 A | Yes, with lots of room |
| USB-C at 1.5 A (TERMPWR on) | 1.5 A | Yes in practice: ~1.3 A realistic worst. The 1.55 A ceiling needs every maximum at once (e.g. a 200 mA SD write while all 18 lines are asserted into two terminators), which doesn't happen. Thin |
| USB-C Default / USB 2.0 (TERMPWR off by design) | 500 mA once configured | Yes typically (≈220 mA). The 640 mA ceiling exceeds it only if every maximum coincides |
| USB 2.0 before configuration | 100 mA | **No.** The hub, FT232H and RP2350 exceed it at enumeration. Many bus-powered hubs do the same and hosts rarely enforce it. Accepted as a known deviation |
| Bench 5 V (powers everything when present) | Bench eFuse limit 2.0–2.45 A | Yes. Use a supply rated ≥ 2.5 A, set to 5.0 V. The ceiling (1.55 A) is well inside. Only a TERMPWR overload at its own limit (≤ 1.41 A) plus maximum logic (0.64 A) reaches ~2.05 A, where the bench eFuse may current-limit too: accepted (it's a fault case) |

**Heat, worst case (updated 2026-09-26, design review R085):** the input can be 5.5 V (USB) or
up to 5.59 V (bench OVLO worst case), and the TPS737 DCQ is 53.1 °C/W on legacy silicon but
**76 °C/W on new silicon** (JEDEC board; JLC doesn't let us choose).
- 3.3 V LDO: (5.59 − 3.3) × 0.555 ≈ 1.27 W ceiling → +67–97 °C; typical 0.17 A ≈ 0.3 W.
- Terminator LDO: (5.59 − 2.83) × 0.40 A ≈ 1.1 W ceiling → +58–84 °C; typical ~0.35 W.
- Mux + eFuses ≈ 0.2 W.
At a 40 °C in-case ambient the every-maximum ceiling can reach T_J ≈ 125–135 °C on new silicon
(thermal shutdown at 160 °C protects it). Typical is < 30 °C of rise. **Layout:** keep the two
SOT-223s apart, give each ≥ 2–3 in² of copper tied to an inner ground with vias under the tab,
and vent the printed case.

**3.3 V regulator (accepted 2026-09-24): a second TPS73701DCQR (C56848) set to 3.3 V.**
- It's the same part as the terminator LDO, so there's **no extra loading fee**. That's the same
  logic as the one-part ideal-diode decision (then LM66200, now TPS2116).
- 1 A rating (1.8× the ceiling), ~130 mV typ / 500 mV max dropout at 1 A. It holds 3.3 V down to
  ~3.5–3.8 V in, so a sagging USB supply (≈4.4 V at the board with 1.5 A through a worst-case
  cable) isn't a problem.
- **EN pins (both LDOs, 2026-09-26, R084):** 100 k / 75 k from each LDO's own input (EN = 0.43 ×
  V_IN), so each turns on only above ≈ 4.0 V (EN ≥ 1.7 V) and EN stays ≤ 2.4 V at 5.59 V in. TI
  warns that EN tied straight to IN can overshoot on slow input ramps (ours are 1.7–15 ms).
- **Caps:** C_IN 1 µF and C_OUT 10 µF (0805) at each LDO; TI's minimum is 1 µF on the output.
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
  **With VREGIN at 5 V, VCCD is an output** (the FT232H's internal 3.3 V), and FTDI's examples
  (DS Fig. 6.1/6.2) feed VCCIO, VPHY, VPLL and the EEPROM from it. **Updated 2026-09-26 (R016):
  copy Fig. 6.2 exactly** (net `FT_3V3`; VPHY and VPLL through 600 Ω ferrites). VCCIO is *not* on
  the board 3.3 V rail, and **VCCD must never connect to the board 3.3 V** (two regulators would
  fight). The FT232H's 3.3 V I/O talks to the RP2350's 3.3 V directly; both come from the same
  5 V, so there's no sequencing problem. See "FT232H pins in detail".
- **CH334P in external 3.3 V mode (V5 and VDD33 both on the 3.3 V rail).** With its internal
  LDO, V5 must be ≥ 4.5 V (DS §4.2), and the worst-case USB supply (≈4.4 V) misses that. WCH itself
  suggests this mode for industrial use, because it cuts the hub's dissipation from 85 mA × 5 V
  to 85 mA × 3.3 V (Chinese V2.91 §6.1). The trade-off: external mode needs 3.2–3.4 V, which is
  tighter than the LDO's worst-case ±3 % (typical ±0.5 % is well inside). **Decided 2026-09-25:
  1 % feedback resistors (47 k / 27 k, no-fee), not 0.1 %.** The LDO dominates either way
  (worst case 3.16–3.44 V with 1 %, 3.20–3.40 V with 0.1 %, legacy silicon), and JLC doesn't
  let us pick the silicon. We assume the CH334 stays in spec, and the owner measures the rail
  at bring-up (swap one resistor if needed).
  - **2026-09-26 (R030/R078):** the CH334's low-voltage reset trips anywhere from 2.5 to 3.2 V
    (§4.2), and the RP2350's VREG_AVDD/USB_OTP_VDD need ≥ 3.135 V. Raising the setpoint to
    ~3.37 V was considered and rejected: it would push worst-case legacy silicon past the
    CH334's 3.4 V maximum. So the rail **stays at 3.30 V**, with a **DNP 0603 footprint in
    parallel with R2 (27 k)** for rework trim (e.g. fitting 1 MΩ raises the rail ≈ 60 mV) and
    10 µF + 100 nF at the CH334. Measure under load (SD write + TERMPWR on) at bring-up.
- ~~The **TERMPWR polyfuse** must hold ≥ 0.9 A and trip at ≤ ~1.5 A~~: superseded 2026-09-24 by the
  TERMPWR eFuse (1.22 A limit, 28 mΩ), see "TERMPWR switch".

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
| TERMPWR_OK digital input (pencilled in; became the GPIO 46 ADC input on 2026-09-26) | 1 |
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
| PSRAM CS1: GPIO 47 (erratum RP2350-E14: firmware must re-pad CS1 when it isn't on GPIO 0) | 1 |
| I²C to the expander (LEDs, card detect, fault flags, resets; spare pins for TERM_EN, DIP readback) | 2 |
| LA markers | 2 |
| TERMPWR sense (ADC6, GPIO 46; added 2026-09-26, R066) | 1 |
| **Total** | **48 of 48** |

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
  INT goes to a test point only; firmware polls (the optional link to GPIO 46 went away when
  46 became the TERMPWR ADC, 2026-09-26).
  Tentative pins: in = card detect, TERMPWR_OK (moved to the ADC 2026-09-26), CC detector ×2 (if used), bench present,
  USB present; out = 2 status LEDs, TERM_EN (pencilled in), SD power enable (optional),
  FT232H reset, hub reset. The rest are spare. **Pin-by-pin assignment accepted 2026-09-25:
  `blocks/5-rp2350-pinout.md`, "I²C expander pinout"** (port 0 = inputs, port 1 = outputs,
  address 0x20; P01 = TERMPWR_EN_N instead of a CC_OK copy).
  - **Unpowered behavior (datasheet, not measured):** the TCA9535/9555/6416A and the MCP23017
    all spec an I/O clamp for VO > VCC, so an unpowered expander pin clamps toward 0 V. None of
    them fixes the TERM_EN weak spot, so the accepted "documented limitation, no extra parts"
    stands. If that ever changes, a 74LVC1G34-class Ioff buffer (high-Z at VCC = 0) between
    the expander and DIP 2 would fix it.
  - Rejected: MCP23017 (C558584, $1.63, SSOP-28; GPA7/GPB7 output-only per DS20001952D; its
    interrupt capture and 1.7 MHz I²C aren't needed for slow, polled signals), TCA9535 (no
    pull-ups, ~2× the price), XL9555 clone (saves ~$0.16, unknown datasheet quality).
- No spare pin left (GPIO 46 senses TERMPWR since 2026-09-26). **If pins free up (e.g. the SE front end allows shared data pins, ~8
  saved), switch microSD to 4-bit SDIO first** (+3 pins, ~4× bandwidth, BlueSCSI-proven).
  Going back to the 8-bit FIFO comes second (+5–6 pins).

**FT1248 fallback plan (2026-09-24, owner: "the retooling can be pretty drastic").** We're not
testing FT1248 on dev boards first. If it disappoints, the first board gets reworked, not respun.
The FT232H uses **the same pins** for FT1248 and the 245 FIFO (DS v2.0 Table 3.13 vs. §3.5.3):
MIOSIO0–7 = D0–D7 = pins 13–20; SCLK/SS_n/MISO = RXF#/TXE#/RD# = pins 21/25/26; the FIFO adds
WR# (27) and SIWU# (28). Dropping the **microSD (3 GPIO) and the I²C expander (2)** frees 5
pins. That's enough for either:
- **8-bit FT1248** (+4 pins; twice the bus width). The first fallback.
- **245 async FIFO** (+5), if FT1248 itself misbehaves. Mode is an EEPROM setting. SIWU# is tied
  high (10 kΩ to the FT232H VCCIO); short packets go out on the latency timer instead. (Until
  2026-09-26 the spare GPIO 46 could take SIWU#; it's now the TERMPWR ADC.)

Layout rules that keep this a bodge job, not a respin:
- **Pin order:** MIOSIO0–3 on GPIO *n*…*n*+3, and the SDIO and I²C pins on *n*+4…*n*+7, so
  after rework they become MIOSIO4–7 / D4–D7 on consecutive GPIOs (PIO `in`/`out` needs that).
  Keep all of them inside PIO1's window (GPIO 16–47).
- Route FT232H pins 17–20 and 27 to DNP 0 Ω links toward those GPIOs. Pins 27 (WR#) and 28
  (SIWU#) each get a 10 kΩ pull-up to the FT232H VCCIO, so they're never floating.
- Losing the expander loses the LEDs, card detect, fault flags and PWR_SRC readback (TERMPWR
  stays readable on the ADC). The FT232H and hub resets must therefore default to "run", never
  rely on the expander: the FT232H through its 10 kΩ pull-up, the CH334 through its internal one.

Verified (RP2350 datasheet, PIO GPIOBASE register, 2026-09-24): each PIO block sees a
32-GPIO window, and GPIOBASE selects base 0 or 16 only. It is set per block, so the SCSI can
use PIO0 at base 0 (GPIO 0–31) while the FT232H uses PIO1 at base 16 (GPIO 16–47). The 32
SCSI pins fill one window exactly, so pin ordering matters.

### RP2350B pin map and PIO plan (accepted 2026-09-25)

The diagram with every package pin is `blocks/5-rp2350-pinout.md`. The reasoning:

- **SCSI on GPIO 0–31, PIO0 at base 0, both blocks in SCSI-2 connector order** (Table 2).
  Each block then runs connector → per-line clusters → MCU without crossings.
  - Inputs 0–17: DB0–7, DBP, ATN, BSY, ACK, RST, MSG, SEL, C/D, REQ, I/O. These are the
    74LVC1G17 outputs, with **INOVER = invert** in the pad so software reads 1 = asserted.
  - Outputs 18–31: DB0–7 and DBP gates (18–26), then ATN, BSY, ACK, RST and SEL gates
    (27–31). The FET gates are 1 = asserted. **Since 2026-09-26 the PIO0 `out` group is 10
    pins, 18–27: data, parity and ATN** (see "Who drives what").
  - PIO only needs *consecutive* groups; the order within a group is free. `wait pin` can
    reach REQ at bit 16, and side-set can be any pin (ACK = 29). MSG, C/D and I/O are no
    longer adjacent (bits 13/15/17), so firmware gathers the bus phase from three bits.
  - Crystal: GPIO 27 is package pin 28, two pins from XIN (30). Connector order puts ATN
    there, which rarely toggles. (My first draft wrongly said GPIO 28–31 were the ones by the
    crystal; they're beyond SWD and RUN.)
- **Who drives what:**
  - PIO0: data gates, **ATN** and ACK (per-byte handshakes).
    - **ATN moved to PIO0 on 2026-09-26 (design review R010).** SCSI-2 §6.2.1: the initiator
      negates ATN "while the REQ signal is true and the ACK signal is false during the last
      REQ/ACK handshake" of MESSAGE OUT. That window is ~100 ns wide, which only PIO can hit.
      ATN (GPIO 27) sits right after DBP, so `out pins, 10` carries it as bit 9 of every word.
      The CPU sets it between phases (e.g. selection with ATN) by injecting instructions.
  - CPU (SIO): BSY and SEL, which change per phase on µs timescales (arbitration delay
    2.4 µs). That keeps arbitration, selection and reselection in C. During arbitration the
    CPU puts our ID bit on the bus: simplest is to switch that one data pin to SIO for the
    arbitration window (the SET group can't reach DB5–DB7 from OUT_BASE).
  - **RST is CPU-only:** its function select is SIO, so PIO physically can't assert it (R4b).
  - Rejected: an all-PIO "control" SM. It's atomic, but two SMs writing overlapping pins
    need ownership handoffs ("last writer wins"), and it costs slots we may want for sync
    transfers.
- **Everything else on GPIO 32–47:**
  - FT1248 on 32–35 and 41–43 (PIO1, base 16).
  - I²C0 on 36/37.
  - SD CLK, CMD and D0 on 38–40 (PIO2, base 16).
  - LA markers on 44/45.
  - **TERMPWR sense on 46 (ADC6)**, through 100 k / 100 k with 100 nF (2026-09-26, R066; it
    was the spare). 0–5.6 V reads as 0–2.8 V. Accuracy is the ADC reference's (ADC_AVDD = the
    3.3 V rail, ±3 %), so calibrate against a measured rail at bring-up for the 4.25 V warning.
  - PSRAM CS1 on 47 (3.3 kΩ pull-up).
  - 33 Ω series resistors on the 7 FT1248 nets at the RP2350 end (R021).
- **FT1248 fallback links (accepted):**
  - Fitted 0 Ω from GPIO 36–40 to their I²C/SD nets.
  - Unfitted 0 Ω from FT232H pins 17–20 and 27 to GPIO 36–40 (pin 28, SIWU#, is pulled up
    instead; 46 is the TERMPWR ADC).
  - That's 10 × C17168. The swap table is on page 5.
- **RP2350-E9 (datasheet erratum):** a Bank 0 pad set as an input (input buffer on, output
  off) at a mid-level voltage sources about 120 µA and floats to about 2.2 V. Only a pull of
  **≤ 8.2 kΩ** overcomes it. That's above the FDV301N's 0.70–1.06 V threshold, so a gate pin
  left as an input would assert its SCSI line.
  - Fixes: **4.7 kΩ gate pull-downs** (C25900, was 10 kΩ), and a firmware rule to **clear
    the input enable on all 14 gate pins** and set the pin direction before handing a pin to
    PIO.
  - Reset is unaffected: pads come out of reset with the input buffer off.

**PIO0 sketch** (4 SMs, 32 slots; about 26 used). Revised 2026-09-26 after the design review
(R007–R013, R100–R104). Not assembled yet: the Phase 4 firmware writes the real programs.

```
; data_in (DATA IN). IN_BASE=0, JMP_PIN=15 (C/D), side-set = ACK (GPIO 29), REQ = in bit 16.
; Autopush at 9 bits. STATUS / MESSAGE IN run the same loop for a known byte count.
.side_set 1 opt
.wrap_target
    wait 1 pin 16     side 0     ; REQ asserted (inputs inverted: 1 = asserted); ACK released
    jmp  pin, phase              ; C/D asserted: the target left DATA IN; hand back (R101)
    in   pins, 9      side 1 [7] ; sample DB0-7+P, assert ACK, hold >= 53 ns (REQ ringing, R011)
    wait 0 pin 16                ; REQ released; ACK drops at the top of the loop
.wrap
phase:
    irq  wait 0       side 0     ; tell the CPU, which reads the phase and switches programs
                                 ; 5 instr

; data_out (DATA OUT / COMMAND / MESSAGE OUT). OUT_BASE=18, OUT_COUNT=10: DB0-7, DBP, ATN.
; Each FIFO word holds two 10-bit pin states: bits 0-9 = the byte (+ parity from a lookup
; table, + ATN), bits 10-19 = the state after REQ drops (data released; ATN kept, or 0 on the
; last MESSAGE OUT byte). JMP_PIN = C/D in DATA OUT. COMMAND and MESSAGE OUT (short, known
; counts; C/D is asserted there) use a copy without the jmp, and the CPU checks the phase after.
.side_set 1 opt
.wrap_target
    pull block        side 0     ; ACK negated
    wait 1 pin 16                ; REQ asserted
    jmp  pin, phase              ; DATA OUT only: phase changed (R101)
    out  pins, 10     [7]        ; drive the byte (+ATN; ATN drops here on the last MSG OUT byte, R010)
    nop               [7]        ; 16 cycles = 107 ns data -> ACK at 150 MHz (>= 100 ns, R008/R100)
    nop               side 1 [7] ; assert ACK; hold >= 53 ns before looking at REQ (R011)
    wait 0 pin 16                ; REQ released
    out  pins, 10                ; release the data bus between bytes (R009), ATN per the word
.wrap
phase:
    irq  wait 0       side 0     ; 9 instr

; sniff, protocol mode (long captures, R4/R104): one record per handshake, DATA included.
; An SM per direction waits for the strobe (REQ assert for target->initiator phases, ACK
; assert for initiator->target), then `in pins, 18` + push: state of all 18 lines at the
; strobe. DMA into an SRAM ring; the CPU adds a coarse time per block and summarises long
; DATA phases (counts, first N bytes, checksum) if the link can't take them.   ~3 instr each

; sniff, edge mode (short triggered windows into SRAM/PSRAM): one SM pushes
; {18 state bits, 14-bit loop-count delta} in ONE word per change, so state and time can't
; desynchronise (the old two-SM sniff + stamp scheme could).                    ~6 instr
```

- data_in and data_out both side-set ACK and wait on REQ: enable only one at a time
  (`pio_sm_set_enabled`), because the last writer wins on a shared pin.
- The old firmware deadline "release all 9 data gates within 400 ns when the phase turns
  target-driven" is gone: data_out releases the bus between bytes (SCSI-2 §6.1.5.1 allows it
  once REQ is false).
- **Sync transfers (open, R105 undecided):** at 10 MB/s fast sync the hold time is 10 ns and
  the PIO input synchroniser samples 7–13 ns after the edge. Protocol-mode tracing of sync DATA
  (owner, R013) will need `INPUT_SYNC_BYPASS` on the sampled pins and maybe a higher clock.
  Whether the D4000 negotiates sync at all is a Phase 2 question.
- Resources: PIO0 ≈ 5 + 9 + 2 × 3 + 6 = 26 of 32 slots (initiator and listen programs can also
  be swapped). PIO1 (FT1248 4-bit master) ≈ 26–30 slots, PIO2 (1-bit SDIO) ≈ 20–26. DMA and
  IRQs fit (design review R106, R107).

### Firmware rules from the design review (2026-09-26)

Hardware stays as drawn. These are requirements on the Phase 4 firmware, collected here so
they're not lost. Each cites its design-review finding.

- **Bus safety (R004, R014, R103):** enable the watchdog in the SCSI engine. The hard-fault
  handler releases all 14 gates first. GPIO interrupts on RST asserted, BSY and SEL both false,
  and I/O asserted run at the highest NVIC priority, from SRAM, and force every gate off within
  SCSI-2's 800 ns bus-clear delay (disable the PIO0 SMs; SIO clear plus OEOVER on the PIO pins).
  Arbitration and selection run in a tight loop on a dedicated core (core 1), interrupts masked
  only for that window, never touching flash or PSRAM (bus set delay ≤ 1.8 µs). Filter RST
  glitches (≥ 2 samples). The host protocol exposes a "bus reset" (RST ≥ 25 µs).
- **Memory (R092):** build with `PICO_COPY_TO_RAM` so code runs from SRAM. SCSI and sniffer DMA
  go into SRAM rings only; a second stage moves blocks to and from PSRAM through the uncached
  alias. **No flash writes during a SCSI session** (an erase stalls XIP and PSRAM for up to
  0.4 s). QMI starting point for the APS6404L: clkdiv 2 (75 MHz), PAGEBREAK 1024, MAX_SELECT
  within tCEM 8 µs, RXDELAY ≈ 2; send the QPI-exit command before the 66h/99h reset after a
  soft reset. Register a `flash_set_qmi_cs1_setup_function()` so PSRAM timing survives flash
  writes. **Never program FLASH_DEVINFO CS1 in OTP** (on A2 silicon, E14 makes the bootrom
  drive GPIO 0, the DB0 receiver output).
- **RP2350-E9:** clear the input enable on the 14 gate pins after `gpio_set_function` or
  `pio_gpio_init` (both set IE = 1). The ADC pin (GPIO 46) also runs with IE off.
- **FT1248 (R021):** keep the 7 FT1248 pins as inputs until FT1248 mode is confirmed (blank
  EEPROM = UART mode, which drives pins 13 and 15). The host tool never calls
  `FT_SetBitMode` except reset (0x00). Send the FT1248 flush command (0x4) after short replies.
- **TERMPWR (R049, R064, R069):** no arbitration or selection unless the TERMPWR ADC reads
  ≥ ~4.0 V; report "no TERMPWR" to the host; mark sniffer captures invalid while it's absent;
  warn below 4.25 V. Ignore TERMPWR_FLT_N for a few ms after TERMPWR_EN_N changes, and when
  FLT is low while the ADC shows TERMPWR present, report "another device supplies TERMPWR"
  (reverse blocking), not a short.
- **microSD (R108):** High Speed mode (50 MHz, CMD6). Treat spill as "extends the stall buffer",
  not "sustains throughput"; the half-duplex bus can't write and drain at once.
- **CH334 reset:** pulse P14 low ≥ 4 µs to reset; never hold it high as an output at power-up.
- **Suspend (R005):** accepted deviation, like the 100 mA pre-configuration one: the board
  draws ~0.2 A in USB suspend. Optionally turn LEDs and the SD card off.

### Debug: Tag-Connect TC2030-IDC + the owner's J-Link EDU (decided 2026-09-25)

- **Footprint:** KiCad `Connector:Tag-Connect_TC2030-IDC-FP_2x03_P1.27mm_Vertical` (the legged
  version, with holes for the retaining clips). There's no part on the BOM.
- **Pads (Tag-Connect ARM20-CTX sheet, checked 2026-09-25):** 1 VCC (3.3 V, used as the probe's
  target reference), 2 SWDIO, 3 nRESET → RP2350 RUN, 4 SWCLK, 5 GND, 6 SWO → not connected
  (the RP2350 has no SWO pin).
- **Probe: the owner's SEGGER J-Link EDU.** SEGGER officially supports the RP2350 (both
  Cortex-M33 cores, flash programming; news 2024-11-11, SEGGER KB "Raspberry Pi Pico 2"). The
  EDU licence covers non-commercial use, which this hobby project is.
  - To buy: the **TC2030-IDC** cable plus Tag-Connect's **ARM20-CTX** adapter (J-Link 20-pin
    → TC2030-IDC).
- Rejected:
  - **ST-Link V2:** ST's own protocol, not the RP2350's supported path. Raspberry Pi's
    OpenOCD targets CMSIS-DAP probes, and the clones are unreliable.
  - **Raspberry Pi Debug Probe** (~$12, CMSIS-DAP, the officially supported probe): a good
    second choice, but it has a 3-pin JST-SH plug and there's no off-the-shelf TC2030
    adapter for it.
- Routine flashing needs no probe: BOOTSEL + USB (UF2/picotool). The probe is for
  step-debugging.

### Resistor and small-part values (decided 2026-09-25; revised 2026-09-26 after the design review)

All are 1 % 0402 JLC basic or preferred parts unless noted. Worst cases use 1 % resistors
and the datasheet threshold spreads. Rows marked **(R0xx)** changed in the design review.

| Circuit | Values | Result | Worst case / check |
|---|---|---|---|
| 3.3 V LDO feedback (TPS73701, Vout = 1.204 (R1+R2)/R2) | R1 47 k, R2 27 k, **+ DNP 0603 across R2** (R030) | 3.300 V | 3.16–3.44 V on legacy silicon (±3 %), 3.21–3.39 V on new (±1.5 %). Measure at bring-up; fitting 1 MΩ across R2 raises it ≈ 55 mV |
| Terminator LDO feedback **(R023, R083)** | R1 **39 k + 5.6 k**, R2 **33 k** (R1‖R2 = 19 kΩ, TI's recommendation) | 2.831 V | 2.72–2.94 V: above the LVTH245's 2.7 V minimum, under SCSI-2's 2.96 V |
| Terminator rail bleed **(R042, R086)** | **270 Ω 0603** (C22966) to GND | 10.5 mA, 30 mW | Keeps the TPS737 in its ≥ 10 mA accuracy spec; absorbs current pushed in from the bus |
| LDO EN dividers ×2 **(R084)** | **100 k / 75 k** from each LDO's input | EN = 0.43 × V_IN | On above ≈ 4.0 V; EN ≤ 2.4 V at 5.59 V |
| Bench eFuse EN/UVLO + OVLO string **(R057, R059, R061)** | R1 510 k, R2 **39 k + 3.9 k**, R3 **150 k + 10 k** | UV 4.22 V, OV **5.35 V** | UV 4.05–4.41 V; OV 5.14–5.59 V (incl. ±0.1 µA pin leakage); recovers below 4.86 V. Set the bench to 5.0 V. See "Bench 5 V input protection" for why the string wasn't scaled up |
| Bench eFuse EN clamp **(R057)** | **BZT52C5V6** (C19077402), EN to GND | EN ≤ 5.9 V | EN would reach 6.83 V (abs max 6.5 V) at 24 V in. At 5 V, EN = 1.42 V, far below the knee |
| Bench eFuse current limit (R_ILM = 3334/I) **(R095)** | **1.5 k** | 2.22 A | 2.0–2.45 A (±10 %). Above the 1.55 A ceiling and under the TPS2116's 2.5 A. Only a TERMPWR overload at its own limit plus maximum logic (≈ 2.05 A) can reach it: accepted |
| TPS2116 PR1 divider (from VIN1 = bench) | 100 k / 39 k | 0.281 × VIN1 | Bench counts as present above 3.56 V (3.24–3.90 V); the eFuse output is 0 or ≥ 4.05 V |
| TPS2116 ST pull-up | 10 k to 3.3 V | → expander P02 | 1 = bench in use |
| VBUS snubber **(R074)** | **1 Ω 0603** (C22936) + **4.7 µF 25 V 0805** (C1779) | ≈ critically damped with 1 µF on VIN2 | 5.7 µF on VBUS in total (≤ 10 µF USB limit) |
| TERMPWR eFuse EN/UVLO | 39 k / 15 k | 4.32 V | 4.20–4.47 V (kept, R069) |
| TERMPWR eFuse current limit | 2.4 k + 330 Ω series | 1.22 A | 1.02–1.41 A (datasheet rows; was quoted 1.06–1.39) |
| TERMPWR enable node pull-up | 10 k to 3.3 V | | Node ≈ 2.9–3.1 V when high, because of the OVLO divider below |
| TERMPWR eFuse OVLO divider **(R062)** | **56 k (node → OVLO) / 47 k (OVLO → GND)** | 0.456 × node | Off: OVLO 1.31–1.43 V (> 1.223 V trip, inside the 0.5–1.5 V recommended range). On: ≤ 0.32 V (< 1.076 V) |
| CC input filter ×2 | 10 k + 1 µF (C52923) | τ 10 ms | Bias error ≤ 4 mV |
| CC reference **(R087)** | CJ431 (C3113) + **470 Ω** bias; 10 k + 3.3 k over 4.7 k; 1 M hysteresis; **no cap on the cathode** | 0.661 / 0.651 V | +6 to +11 mV margin each side (depends on the CJ431 rank) |
| TERMPWR sense → GPIO 46 (ADC6) **(R066)** | **100 k / 100 k + 100 nF** at the pin | 0.5 × TERMPWR | 0–5.6 V → 0–2.8 V. Draws 26 µA from TERMPWR. Replaces the 22 k/33 k TERMPWR_OK divider into the expander |
| TERMPWR "present" LED (on TERMPWR itself) **(R065)** | **10 k** (C25744) + red LED | ≈ 0.35 mA | Non-terminator TERMPWR draw ≤ 0.35 + 0.03 (ADC divider) + 0.44 (eFuse leakage when disabled) ≈ 0.82 mA, under SCSI-2's 1.0 mA |
| Bench-present 2N7002 gate, fed from the **bench eFuse output** | 10 k series, 100 k to GND | 4.5 V at 5 V | Keeps the ±20 V gate away from a 24 V mistake on the raw terminal |
| FDV301N gate ×14 | 100 Ω series, **4.7 k** pull-down, 22 pF DNP | | E9 |
| Terminator resistors ×18 **(R006)** | **2 × 220 Ω 0402 in parallel** (C25091, basic) | 110 Ω | ≤ 35 mW per resistor (55 % of 62.5 mW) at 2.94 V into an asserted line. Replaces the extended 110 Ω C2909312 |
| PSRAM CS1 pull-up **(R079)** | **3.3 k** (C25890) | | 3.02 V against the RP2350's 36 kΩ minimum reset pull-down (APS6404L VIH = VDD − 0.4 V) |
| FT1248 series ×7 **(R021)** | **33 Ω** (C25105) at the RP2350 end | | Damps ringing at 25 MHz; limits contention |
| FT232H REF **(R017)** | **12 k 1 %** (C25752) to GND | | DS Table 3.2 |
| FT232H RESET# | 10 k to FT_3V3 + **10 nF** (C15195) | | DS Fig. 6.2; expander P13 can also pull it low |
| FT232H EEPROM **(R017)** | DO **10 k** pull-up to FT_3V3; DO → DI **2.2 k** (C25879) | | DS Table 3.3 / Fig. 6.2 |
| FT232H WR#, SIWU# (pins 27/28) **(R022)** | **10 k** pull-ups to FT_3V3 | | Never floating in FIFO mode; harmless in FT1248 mode |
| CH334 RESET# **(R031)** | **No pull-up** (internal ~25 k); expander P14 → Schottky **1N5819WS** (C191023, cathode at P14) | | WCH: a pin driven high at power-up enables CDP and turns off hub sleep |
| LEDs on 3.3 V (TERMPWR-enable LED, expander LED1/LED2) | 1 k with red KT-0603R (C2286) or yellow KT-0805Y (C2296) | ~1–1.5 mA | JLC's only basic green (KT-0805G, Vf 2.6–3.1 V) is too close to 3.3 V |
| I²C SDA/SCL | 4.7 k to 3.3 V | | |
| SDIO CMD, D0–D3 pull-ups | 10 k ×5 | | SD spec 10–100 kΩ; D1–D3 aren't wired to the MCU |
| TCA9555 INT | 10 k pull-up to 3.3 V | | Test point only; firmware polls |
| SCSI RESERVED lines **(R002)** | 2 × 0 Ω (C17168) to GND, fitted | | IDC50 24/28 = HD50 37/39; remove if the board ever sits mid-chain. IDC50 25 / HD50 13 stay unconnected |

### eFuse startup (dVdt) and fault-timer (ITIMER) capacitors (decided 2026-09-26)

From TI TPS25947 datasheet SLVSFC9C:
- dVdt pin: SR [V/ms] = 2000 / C_dVdt [pF] (Eq. 4), with inrush I = SR × C_OUT (Eq. 3).
  Open = fastest ramp (t_ON ≈ 0.3 ms at 2.7 V, RL = 100 Ω, 1 µF). The charging current is
  0.81 / 2.21 / 3.82 µA (min / typ / max), so the real slope spans about ×0.37 to ×1.73 of
  nominal.
- ITIMER: blanking t = ΔV_ITIMER × C / I_ITIMER (Eq. 8). ΔV is 1.29 / 1.51 / 1.74 V and I is
  1.2 / 1.8 / 2.5 µA, so about 0.84 ms per nF (0.51–1.45 ms). Open = minimum delay, which
  TI allows ("Leave the ITIMER pin open … minimum possible delay"). During start-up the current
  limit acts without waiting for ITIMER.
- 470 variants (ours): after a fault, active current limiting at I_LIM until thermal shutdown
  (154 °C). The "A" suffix means auto-retry after t_RST = 110 ms.

| | Bench eFuse | TERMPWR eFuse |
|---|---|---|
| **C_dVdt** | **2.2 nF** (C1531, preferred): 0.91 V/ms nominal, so a 5 V ramp takes ~5.5 ms (3–15 ms over the spread) | **2.2 nF**, the same part |
| Load it charges | The bench eFuse OUT / TPS2116 VIN1 caps (≈ 2 µF); the 22 µF on +5V_SYS charges through the TPS2116's own soft start | TERMPWR: our TVS, 1 µF and the 2.83 V LDO input, plus other devices' terminator caps. Assumed ≤ 50 µF |
| Inrush | ≤ ~75 mA even at the fast end. That's gentle on a bench supply set to a low current limit | Only applies at power-up; see the OVLO note below |
| **C_ITIMER** | **Open**, plus an unfitted 0402 pad (1 nF ≈ 0.84 ms blanking if a load step ever trips it) | **Open**, plus an unfitted pad. It limits strictly at 1.22 A, which matches SCSI-2's ≤ 1.5 A recommendation |

- **Important: our TERMPWR enable bypasses dVdt.** The datasheet says the 470x "bypass the
  inrush control (dVdt) and start up in a current limited manner" when recovering from an OVLO
  event. We use OVLO as the TERMPWR enable, so every enable ramps TERMPWR at the 1.22 A limit,
  not the dVdt slope.
  - Into 50 µF that's 5 V × 50 µF / 1.22 A ≈ 0.2 ms, about 0.6 mJ in the FET. Harmless.
  - The USB port sees a ~0.2 ms step of up to 1.22 A on top of the board's ~0.5 A.
  - The dVdt cap still matters for power-up with the enable already low.
  - Accepted. The alternative, enabling through EN/UVLO (active-high), would need an inverter.
- **Shorts:** a TERMPWR short sits at 1.22 A with ~5 V across the FET (~6 W), hits thermal
  shutdown, and retries every 110 ms. The average power stays low, and TERMPWR_FLT_N reports it.
  The bench path behaves the same at 2 A.
- **Firmware (unverified):** FLT may pulse while the eFuse current-limits during the
  enable ramp. Ignore TERMPWR_FLT_N for a few ms after TERMPWR_EN_N changes. FLT also goes low
  in reverse-current blocking (another device's TERMPWR is higher than ours, Table 7-3): with
  the TERMPWR ADC showing a healthy voltage, that's not a fault (R064).
- **VBUS capacitance (settled 2026-09-26):** VBUS sees the TPS2116's 1 µF on VIN2 plus the
  1 Ω + 4.7 µF snubber: 5.7 µF, under USB's 10 µF at attach. +5V_SYS bulk is behind the mux's
  soft start.
- **Other eFuse caps (R097):** bench IN: 1 µF 50 V X7R 0805 (C28323) + 100 nF 50 V; bench OUT:
  1 µF. TERMPWR IN: 100 nF; TERMPWR OUT: 1 µF, plus a **DNP SS14 Schottky footprint** (C2480)
  from OUT (cathode) to GND, which TI suggests against the negative spike when the eFuse
  interrupts a long cable (OUT pulse minimum −0.8 V). Fit it only if the scope shows OUT going
  below −0.8 V: its leakage counts against SCSI-2's 1 mA TERMPWR draw.
- **The TERMPWR enable now reaches OVLO through a 56 k / 47 k divider** (R062), which keeps
  OVLO inside its 0.5–1.5 V recommended range. The dVdt bypass described above is unchanged.

### FT232H pins in detail (datasheet v2.0 §3.5.3, §4.5)

Why FIFO rather than the FT232H's UART mode: UART mode tops out at 12 Mbaud (datasheet
§4.1). With 10 bits on the wire per byte, that's ≤ 1.2 MB/s, which is below R3 (1.5 MB/s). A UART
costs 2–4 pins; the FIFO costs 12 but reaches 8 MB/s.

**Status (2026-09-26):** FT1248 4-bit was chosen on 2026-09-24 (see "GPIO budget"). This
section is now the **reference for the 245 FIFO fallback**, plus the FT232H support circuit
below, which applies to every mode.

Async 245 FIFO (the fallback mode). "RX" and "TX" are named from the FT232H's side.

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

**Support circuit (design review R016/R017, per DS v2.0 Fig. 6.2; applies to every mode):**
- VREGIN (5 V mode) from +5V_SYS, with 4.7 µF + 100 nF. **VCCD is an output** here: it's the
  local `FT_3V3` net (4.7 µF + 100 nF) and feeds VCCIO ×3 (100 nF each), VPHY and VPLL (each
  through a 600 Ω ferrite, GZ1608D601TF C1002, + 100 nF, 4.7 µF pads DNP) and the EEPROM VCC.
  **Never connect VCCD to the board 3.3 V.**
- VCCA and VCORE: 100 nF each (outputs; don't load them).
- REF: 12 kΩ 1 % to GND. TEST (pin 42): GND.
- RESET#: 10 kΩ to FT_3V3 + 10 nF; expander P13 can also pull it low.
- EEPROM 93LC56B: DO pulled up with 10 kΩ, DO → DI through 2.2 kΩ (DS Table 3.3; the figure
  shows 2 kΩ). CS/CLK pull-ups aren't fitted in FTDI's figure.
- ACBUS7/PWRSAV# (pin 31): open, with "Suspend on ACBus7 Low" **off** in the EEPROM (enabled
  with the pin open, it would hold the chip in suspend).
- WR# (27) and SIWU# (28): 10 kΩ pull-ups to FT_3V3, so the FIFO fallback never floats them.
- Crystal: ABM8-272-T3 + 2 × 15 pF (see "FT232H package and crystal"). Drive level checked:
  ≈ 65 µW against the crystal's 200 µW maximum (review R019).

Pins that cost no MCU GPIO: the 93LC56B EEPROM (EECS/EECLK/EEDATA). **The EEPROM is required**,
because without it the FT232H comes up in UART mode. It's programmed over USB after assembly
(FT_PROG on Windows; from macOS, libftdi's `ftdi_eeprom` with `flash_raw` of a saved image, `eeprom_type = 0x56`, as root, because it can't set the FT1248 option bits itself; see `USAGE.md`). The 93LC46B is incompatible. Also RESET# and the
12 MHz crystal. ACBUS5/6/8/9 are free in this mode and can be set to "I/O mode" (CBUS bit-bang).

Rejected alternatives: **sync 245 FIFO** (40 MB/s) adds CLKOUT and OE# (14–15 pins) and
needs a 60 MHz synchronous interface, which is too tight for PIO and more than we need.
**FT1248** uses SCLK, SS#, MISO plus 1/2/4/8 MIOSIO lines (4, 5, 7 or 11 pins). Its
throughput at each width is unverified (AN_167 was fetched 2026-09-24; see the GPIO budget). **FT1248 was chosen on 2026-09-24.**

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
| Regulator CIN, COUT, VREG_AVDD, second DVDD caps ×4 | 4.7 µF X5R 10 V 0402 | C23733 | basic, 2.6 M | Guide §2.1: 3 × 4.7 µF 0402; datasheet §6.3.8.1 / Fig. 19 adds a 4th on DVDD (QFN-80 pin 32, bottom edge, away from LX; 2026-09-26, R081) |
| VREG_AVDD filter resistor | 33 Ω 1 % 0402 | C25105 | basic, 2.2 M | Guide §2.1: 33 Ω + 4.7 µF |
| Decoupling ×13 | 100 nF X7R 50 V 0402 | C307331 | basic, 11.7 M | Guide Appendix B: one per supply pin (IOVDD ×8, DVDD ×3, ADC_AVDD), USB_OTP_VDD and QSPI_IOVDD share one (pins 68/69), plus one at the flash |
| 3.3 V bulk near the MCU | 10 µF X5R 25 V 0805 | C15850 | basic, 5.6 M | Guide C19: 10 µF 0805 X5R |
| QSPI flash | Winbond W25Q128JVSIQ, 16 MB, SOIC-8 208 mil | C97521 | **basic**, 44,238 | Guide §3.1: the same part; 16 MB is the most the RP2350 addresses |
| QSPI_SS pull-up | 10 kΩ 0402, **unfitted** (guide R1 is DNF) | C25744 | basic | Guide §3.1: unneeded with this flash; keep the pads |
| PSRAM CS1 pull-up (GPIO 47) | **3.3 kΩ** 0402, **fitted** (10 kΩ until 2026-09-26, R079) | C25890 | basic | Guide §3.2 (R13): "definitely needed", because GPIOs are pulled low at power-up. 10 kΩ against the RP2350's 36 kΩ-minimum pull-down gives only 2.58 V, under the APS6404L's VIH of VDD − 0.4 V; 3.3 kΩ gives 3.02 V |

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
  fitted **3.3 kΩ** pull-up (see "MCU support parts"). Decouple it with 100 nF + 1 µF (confirm
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
turned up) and pass only ~4.5–5.5 V on to U1 (LM66200 then, TPS2116 since 2026-09-26; both 6 V absolute maximum).

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
- **Settings (revised 2026-09-26, design review R057–R061, R095):** OVLO **5.35 V** (5.14–5.59 V
  worst case), UVLO 4.22 V (4.05–4.41 V), current limit **2.22 A** (2.0–2.45 A). Values in
  "Resistor and small-part values". FLT goes to expander P03 ("bench supply fault"). **Set the
  bench supply to 5.0 V** (5.1 V at most).
  - The old 5.73 V OVLO (5.56–5.93 V) let more than 5.5 V through to the parts downstream
    (mux, both LDOs, FT232H VREGIN; recommended maximum 5.5 V) and onto TERMPWR. The threshold
    spread (±1.7 %), the resistors and the pins' ±0.1 µA leakage make a ~0.45 V window, so no
    string can sit between a 5.1 V bench setting and a strict 5.5 V. 5.14–5.59 V is the best
    fit; the top corner is 0.41 V under the 6 V absolute maximums.
  - **EN clamp:** any UVLO near 4.2 V puts EN at 0.285 × V_IN, so a 24 V adapter drives EN to
    6.8 V, over its 6.5 V absolute maximum. A **BZT52C5V6 Zener from EN to GND** clamps it; OVLO
    then still sits at ≈ 4.6 V (locked out). At a normal 5 V input EN is 1.42 V, about a quarter
    of the Zener voltage, where its leakage is typically nA (the datasheet only bounds it,
    ≤ 1 µA at 2 V). Check UVLO on the bench: 1 µA of leakage would shift UV by up to 0.5 V. Owner: acceptable; if
    it's a problem, bodge in a different clamp.
  - **Reverse polarity: not scaled up (owner asked for it, R059; conflict with R061).** TI's
    footnote (≥ 350 kΩ, met by 510 kΩ) and its §8.3 text (< 10 µA into the pins) disagree. At
    −15 V the 510 k string passes ~28 µA, and the Zener now takes most of it in its forward
    direction. Scaling the string to ≥ 1.5 MΩ would meet < 10 µA, but the pins' ±0.1 µA leakage
    through 1.6 MΩ moves OVLO by ±0.16 V and spreads the trip to ~5.0–5.7 V, breaking R061.
    Over-voltage accuracy protects the 6 V parts, so it wins. Accepted by the owner (2026-09-26).
  - **Input caps:** 1 µF 50 V X7R (C28323) + 100 nF at IN (TI: rated ≥ 2 × V_IN).
- Optional: an unfitted TVS footprint across the terminal for hot-plug spikes above 28 V:
  **SMF15CA** (bidirectional, C19077510). A unidirectional SMF15A would forward-conduct on
  reversed leads and take the supply's full current.
- Rejected: TVS + polyfuse crowbar (all basic, but an SMBJ5.0A clamps near 9 V, above U1's
  6 V limit); discrete P-FET reverse protection + zener/transistor OV cut-off (all basic, but a
  loose threshold and 6+ parts to get right); 5.5–6.5 V-rated switches like TPS2553/AP2553 (an
  over-voltage *flag*, but they don't survive 12 V).

### TERMPWR switch and current limit (accepted 2026-09-24): a second TPS259470ARPWR, no polyfuse

The owner asked for a polyfuse. Working it through showed a polyfuse can't meet the spec, and
the eFuse already chosen for the bench input can.

- **The spec:** SCSI-2 §5.4.3 wants ≥ 900 mA available, and recommends limiting the current
  to 1.5 A.
- **Why not a polyfuse:** a PTC trips at roughly 2 × its hold current. Hold ≥ 0.9 A means a trip
  around 1.8–2.2 A, above the 1.5 A recommendation. It also drops 0.1–0.25 V, which is the
  weak spot in the TERMPWR voltage budget (see "Ideal diodes").
- **The eFuse instead (TPS259470ARPWR, C3662799, the same part as the bench input, so no new
  loading fee).** It replaces U2 (LM66200) and the polyfuse:
  - Current limit: R_ILM = 3334 / I_LIM (datasheet Eq. 7). **2.4 kΩ + 330 Ω in series
    (2.73 kΩ, both no-fee) gives 1.22 A**. The spread, interpolated from the datasheet's
    3.32 kΩ and 1.65 kΩ rows, is about ±13 %, so 1.06–1.39 A: ≥ 0.9 A and ≤ 1.5 A. This
    replaces the extended 2.74 kΩ. A single 2.4 kΩ could reach 1.59 A. Check ITIMER at
    schematic time.
  - **R_ON 28 mΩ typ, 45 mΩ max over temperature** (≈ 25–41 mV at 0.9 A), against LM66200 +
    polyfuse ≈ 0.15–0.3 V. The TERMPWR voltage-budget worry mostly goes away. Worst case on a
    1.5 A USB port with a long cable is still ≈ 4.23–4.26 V at the connector (R069, Type-C
    figures unverified); kept as is, with the TERMPWR ADC to measure and warn.
  - **True reverse-current blocking, including unpowered:** OUT leakage ≤ 4.86 µA with
    OUT = 12 V and IN = 0 V (datasheet, "Reverse current blocking"). Another device's TERMPWR
    can't backfeed our board (R2).
  - **The OVLO pin doubles as an active-low enable** (pin description: "can also be used as an
    Active Low Enable"). Our enable node is active-low: **pulled up to 3.3 V through 10 kΩ**
    (changed from 5 V on 2026-09-25), pulled low by the wired-OR of the LM393 outputs
    (CC_OK_N) and the bench-present N-FET. So it reaches OVLO with no inverter, **through a 56 k / 47 k divider since 2026-09-26** (R062).
    Low (< 1.09 V) = on, high (> 1.2 V) = off.
    - The 5 V pull-up only existed because the old LM66200 switch had (we thought) undocumented ON
      thresholds. At 3.3 V the expander can read the node directly (P01 = TERMPWR_EN_N).
    - Side effect: for the ~ms after 5 V is up but before 3.3 V is, the node reads low and
      TERMPWR may switch on briefly. Harmless: with the bus idle the terminators draw almost
      nothing.
  - EN/UVLO: **39 kΩ / 15 kΩ** from IN (the 5 V rail) → 4.32 V rising (≈ 4.19–4.46 V worst).
  - FLT (open-drain) → a spare expander input: "TERMPWR fault" (overcurrent or short on the bus).
  - The TERMPWR LED stays on the enable node: 3.3 V → 1 kΩ → LED → node, lit when the node
    is low (off when high: the node sits at ≈ 3.0 V, too little across the LED). The disable jumper (R2a) stays in series with the
    output.
- The TPS2121 fallback is no longer needed. (U1 stayed an LM66200 until 2026-09-26, when it became a TPS2116; see "Power mux".)

### Connectors (2026-09-24)

- **Board: 4 layers** (owner). Outline, dimensions and placement: the owner does the first
  layout pass by hand once the schematic exists.
- **USB-C shell:** to GND through a fitted 0 Ω link, so an RC (e.g. 1 MΩ ∥ 4.7 nF) can replace
  it later if EMC testing wants the shield separated.
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
  - **Pin handling (2026-09-26, R002; SCSI-2 Table 2 and §5.4.4):** pin 25 (HD50 13) is
    **OPEN**: leave it unconnected, or the reversed-cable case above shorts TERMPWR. The
    RESERVED pins 24 and 28 (HD50 37 and 39) go to GND through a fitted 0 Ω each (end devices
    "shall" ground them; remove the links if the board ever sits mid-chain). Even pins 20, 22,
    30 and 34 (HD50 35, 36, 40, 42) are GROUND, not signals. Wire both connectors from the
    table by signal name.
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
| Bench terminal (×1, **not fitted**) | **SMF15CA** (bidirectional), SOD-123FL | C19077510 | Clamps at 24.4 V, under the eFuse's 28 V absolute maximum. Unfitted by default because a fitted 15 V TVS would short a 24 V adapter, and the eFuse alone survives up to 28 V. Bidirectional since 2026-09-26 (R060): a unidirectional TVS forward-conducts on reversed leads |

- Not protected: microSD (inside the case, card only), the LA header (buffered, and goes to a
  lab instrument), SWD (bench use). Add pads later if needed.
- Clamping voltages (10–25 V) are well above what the protected chips tolerate for DC. That's
  normal for ESD parts: they cut a kV-level pulse down to a level the chip's own ~2 kV HBM
  protection absorbs. Put them right at the connector, before any series resistor.
- SCSI capacitance budget (≤ 25 pF per signal, §5.4.1.2). §5.4 says termination is "assumed to
  be external" for these measurements, so our terminator doesn't count. Estimate with the
  FDV301N drivers: FET C_oss ~10 pF at 2.8 V (typical curve, DS Fig. 8) + 74LVC1G17 C_I 5 pF
  (typ, Nexperia) + ESD 0.3 pF + traces ~3 pF ≈ 18 pF. The LA path hangs off the receiver
  output, not the bus.
  - Mid-chain (terminator disabled, so it counts): the '245's C_io adds ~9 pF → **~27 pF**,
    about 2 pF over, on typical values (R027). Accepted: that's the secondary topology.

### FT232H package and crystal (decided 2026-09-24)

- **Package: FT232HL-REEL (LQFP-48), C51997**, 3,224 at JLC, $9.36. The QFN FT232HQ we'd assumed is
  out of stock at LCSC (0) and JLC (10 left, at $27). FTDI uses the same pin numbering for both
  packages (DS v2.0 §3), so the pin tables above still hold. The LQFP is also easier to bodge
  (see the FT1248 fallback plan).
- The owner asked about cheaper parts. Rejected for v1: **CH347F** ($3.35; UART tops out at
  9 Mbaud ≈ 0.9 MB/s, below R3; SPI mode needs WCH's vendor driver and a redesign),
  **CH32V305 as a bridge MCU** ($1.90–2.98; a second firmware to write; a candidate for a v2
  cost-down), **FX2LP** ($11). Saving ~$6–7 a board isn't worth that risk at v1 quantities.
- **Crystal: the same ABM8-272-T3** as the RP2350 and the hub, with 2 × 15 pF. FT232H DS §6.3
  wants a fundamental-mode, parallel-cut crystal (it is) and load caps chosen per the crystal
  maker (27 pF is only an example). FTDI writes "12 MHz ± 0.003 %" (±30 ppm). The ABM8 is
  ±30 ppm at 25 °C plus ±30 ppm over −40…85 °C, so on paper it can exceed that. USB HS itself
  allows ±500 ppm, and near room temperature the drift is a few ppm. We don't use the features
  (UART baud accuracy) that FTDI's tighter number protects. Accepted.

## SCSI electrical front end (candidates)

- The classic, proven choice: 74LS641-1 (open-collector, 48 mA sink) transceivers, as used by
  PiSCSI. It runs on 5 V and needs level care toward the 3.3 V MCU.
- Alternative: MOSFET/open-drain drivers plus Schmitt receivers (74LVC14 class). Study the
  ZuluSCSI and BlueSCSI schematics before choosing; check their licenses before reusing
  anything. **Chosen for the drivers on 2026-09-25 (below).**

### SCSI drivers (decided 2026-09-25): 14 × FDV301N, fallback SN74LVTH125PWR

**What SCSI-2 asks of a driver** (rev 10L, read 2026-09-25):
- Asserting a line (§5.4.1.1): V_OL 0–0.5 V while sinking 48 mA, at our connector.
- Negating a line: V_OH 2.5–5.25 V. With open-drain drivers **we never drive it.** The
  terminators hold released lines at ≥ 2.5 V (§5.4.1(b)(4)). There's no high-side current spec.
- Released line (§5.4.1.2): I_IH 0–0.1 mA at 2.7 V, I_IL 0 to −0.4 mA at 0.5 V, ≤ 25 pF. SCSI-2
  *recommends* meeting I_IL/I_IH when powered off too.
- **Open-drain everywhere.** §5.6.2 requires BSY, SEL and RST to be OR-tied and allows either
  kind on the other lines. But in arbitration (Table 6, "S ID"; §5.7 note 20) a device may
  assert only its own ID bit, must release the other seven, and must never drive DB(P) false.
  BlueSCSI's whole-bus push-pull '245 with one `DIR` pin can't do that. Open-drain on all 14
  lines uses one GPIO per line and makes bus fights impossible. The only cost is a slower
  rising edge (terminator into cable capacitance), which doesn't matter at our speeds.

**Circuit, per line (×14: DB0–7, DBP, ATN, ACK, SEL, BSY, RST):**

```
RP2350 GPIO ──100 Ω──┬── G  FDV301N  D ──── bus line (connector, ESD, terminator, receiver)
                     │               S ──── GND
                   4.7 kΩ ─ GND   (10 kΩ until 2026-09-25; RP2350-E9)
                   22 pF ─ GND  (DNP)
```

GPIO high = line asserted. We never drive REQ, MSG, C/D or I/O (Table 6: target-only), so
those 4 have receivers only.

**FDV301N (C15310)**: onsemi SOT-23, extended, $0.037, ~495k at JLC (2026-09-25). Checked
against its datasheet:
- V_GS(th) 0.70–1.06 V. R_DS(on) ≤ 5 Ω at V_GS = 2.7 V at 25 °C, and ≤ 9 Ω at T_J = 125 °C
  (I_D = 0.2 A). So **V_OL ≤ 0.24 V at 48 mA (25 °C) and ≤ 0.43 V at 125 °C**, inside
  SCSI-2's 0.5 V. The LVTH125 only guarantees 0.55 V at 48 mA.
- I_DSS ≤ 1 µA (10 µA at 55 °C). Released and unpowered, it leaks far less than the LVTH's
  ±100 µA I_off, which sits exactly at the 0.1 mA I_IH limit.
- No supply pin, so there's no power sequencing. The body diode (source = GND) only conducts
  if the bus goes below about −0.6 V.
- C_oss is 6 pF at 10 V but about 10 pF at 2.8 V (typical curve, Fig. 8). That's about 3.5 pF
  more than the LVTH125 (6.5 pF typ). Budget ≈ 18 of 25 pF (see ESD section).

**Safe at power-up, and a known weak spot:**
- RP2350 GPIOs reset with the pull-down on and the pad isolated (datasheet Table 853:
  PDE = 1, ISO = 1, IE = 0). That holds the gates low, so the lines stay released during
  reset and boot. The **4.7 kΩ** pull-down keeps them low when the board is off. (It was
  10 kΩ, changed on 2026-09-25 because of RP2350-E9; see "RP2350B pin map".) With the LVTH
  it's the other way round: the same reset pull-down pulls `/OE` low, which *enables* the
  drivers, so external pull-ups would have to overpower it.
- Weak spot, inferred from typical curves: a rising bus edge couples through C_rss
  (~2.5 pF at 2.8 V) into a gate held only by the resistor (board off, or MCU in reset). The
  kick is ~2.8 V × 2.5/11 ≈ 0.6 V, close to the 0.70 V minimum V_th, and V_th drops about
  2.1 mV/°C when hot. The DNP 22 pF cap cuts it to about 0.2 V. **Bench check:** watch a
  gate on the scope with the board off while the G4 drives the bus. **Revised 2026-09-26
  (R037):** the kick is self-limiting (V_th is defined at 250 µA, so a brief 0.7 V sinks at most
  a few hundred µA from a 20+ mA terminator, and it opposes the rising edge). Fit the caps only if
  it makes a visible dip or step on the bus edge.
- The 100 Ω gate resistor limits ringing and edge rate. It can be swapped for 0 Ω or a larger
  value to tune slew on the bench.

**Cost and area per board, 2026-09-25:**

| Option | Parts | Cost (10+) | Rough area |
|---|---|---|---|
| **14 × FDV301N (chosen)** | 14 SOT-23 + 14 × 10 kΩ + 14 × 100 Ω + 14 DNP 22 pF | ≈ $0.55 | ≈ 170–230 mm² |
| 4 × SN74LVTH125PWR (fallback) | 4 TSSOP-14 + 4 × 100 nF + 14 pull-ups | ≈ $2.05 | ≈ 180 mm² |
| 7 × DMN2004DWK-7 (dual, C156343) | 7 SOT-363 + the same passives | ≈ $1.10 | ≈ 100 mm² |

- One extended part either way, so the loading fee is the same.
- Discretes can sit right on each bus trace by the connector, which keeps stubs short.
- The dual DMN2004DWK wasn't checked: its C_oss at low V_DS is unverified, and it has only
  5.2k in stock.

**Fallback: SN74LVTH125PWR (C7042)**, TSSOP-14, extended, $0.50 at 10+, ~3.0k at JLC. With
A = GND and `/OE` = GPIO, it's the same open-drain logic with inverted polarity (GPIO
low = asserted). Switch to it if the routing gets hairy, if per-placement cost becomes a
problem, or if the owner changes their mind. From TI SCBS703I:
- V_OL ≤ 0.55 V at 48 mA, a 50 mV miss of the letter of SCSI-2. The real load is two
  2.83 V/110 Ω terminators, about 42 mA at 0.5 V.
- I_off ±100 µA. Power-up 3-state is **specified**: I_OZPU/I_OZPD ±50 µA below V_CC 1.5 V.
- C_o 6.5 pF. Rated 64 mA on every output at once, so about 180 mA through one package is
  fine (inferred; there's no per-GND-pin figure).
- Needs a pull-up on each `/OE` strong enough to beat the RP2350's reset pull-down (e.g.
  10 kΩ), and a 100 nF cap per package. Run it from 3.3 V.
- Prefer it over the SN74LVT125PWR (C2675577): the plain LVT's datasheet (SCBS133F) doesn't
  specify power-up 3-state and has 8 pF C_o, for about $0.18 more.

**Rejected:**
- **2N7002:** V_th up to 2.5 V, so it isn't guaranteed to turn on from 3.3 V.
- **2SK3018:** 13 Ω at 2.5 V.
- **AO3400-class logic FETs:** C_oss around 100 pF.
- **FDV301N clone C20069151:** "preferred" tier, but only 9.5k in stock and the datasheet
  language is unknown.
- **74LS641-1:** 5 V TTL, needs level shifting.
- **74LVC07-class open-drain buffers:** only 24 mA I_OL.

**GPIO sharing and serial inputs (considered and rejected on 2026-09-25):**
- The RP2350 *can* change pin direction every cycle (PIO `set`/`out`/`mov pindirs`, side-set
  pindirs). The obstacle is outside the chip. A receiver output is always driving, so on a
  shared net it either fights the GPIO or, with the GPIO as input, drives the FET gate. That
  makes a loop from bus to receiver to gate: an inverting receiver latches the line asserted,
  and a non-inverting one oscillates.
- Breaking the loop needs output-enabled receivers plus a mode pin, as BlueSCSI does with its
  role signal. That saves about 8 pins, but it breaks arbitration (drive our ID bit while
  reading the other seven) and listen-only mode (all 18 receivers on).
- A shift-register input expander is too slow in *latency*. An 18-bit shift at ~50 MHz is
  ~360 ns, which is longer than a ~330 ns byte cycle at 3 MB/s, eats into the 400/800 ns
  bus-settle/bus-free budget, and the sniffer would miss edges.
- A hybrid, with the slow phase lines on a shift register, saves only about 4 pins.
- Pins would only buy 4-bit SDIO, so it stays **32 dedicated pins: 14 drive + 18 sense.**

### SCSI receivers (decided 2026-09-25): 18 × Nexperia 74LVC1G17GW, fallback 74LVC14APW

**What SCSI-2 asks of a receiver** (§5.4.1.2): V_IL 0–0.8 V, V_IH 2.0–5.25 V, hysteresis
≥ 0.2 V. For a Schmitt input that means **VT+ ≤ 2.0 V** (a line at 2.0 V always reads
released), **VT− ≥ 0.8 V** (a line at 0.8 V always reads asserted), and VT+ − VT− ≥ 0.2 V. Our
own R2 adds: no bus loading or clamping when unpowered.

**Per line (×18), next to that line's FET cluster:** bus → 74LVC1G17 input; output → GPIO
(and the LA tap, open); 100 nF on VCC; supply 3.3 V. It's non-inverting, so GPIO low means
asserted (PIO or GPIO INOVER can flip it). The 4 receive-only lines (REQ, MSG, C/D, I/O)
have just the receiver.

**Datasheets compared (2026-09-25).** Every vendor gives guaranteed limits only at 3.0 V and
at 3.6 or 4.5 V, never at 3.3 V.

| Part (vendor, datasheet) | Limits near our 3.3 V supply | Unpowered (I_OFF) | Verdict |
|---|---|---|---|
| **74LVC1G17 (Nexperia Rev. 16.1)** | At 3.0 V: VT+ 1.29–1.71, VT− 0.88–1.24 (−40…85 °C; the limits that matter, VT+ max 1.71 and VT− min 0.88, are the same to 125 °C). Interpolated toward the 4.5 V row: at 3.3 V ≈ VT+ ≤ 1.84, VT− ≥ 0.97 | **±2 µA, specified** | **Chosen**: meets R2; ~0.16 V threshold margin (interpolated, not guaranteed at 3.3 V) |
| 74LVC14A (Nexperia Rev. 11; -Q100 Rev. 5 identical) | At 3.0 V **and** 3.6 V: VT+ 1.2–2.0, VT− 0.8–1.5, hysteresis 0.3–1.2 | Not specified (inputs tolerate 5.5 V; I_I only at V_CC = 3.6 V) | **Fallback**: thresholds guaranteed, R2 unverified |
| 74LVC14A (TI SCAS285AC) | VT− min **0.6 V** at 3.0 V | Not specified (TI removed I_off from its feature list) | Rejected: fails VT− |
| 74LVC3G17 / 2G17 (Nexperia) | VT+ max **2.2 V** at 3.0 V | ±2 µA | Rejected: fails VT+ |
| 74LVC3G17 (TI SCES470F) | At 3.0 V: VT+ ≤ 1.87, VT− ≥ 0.84 (0.04 V margin) | ±2 µA | Rejected: marginal, low stock |

**Lesson: a generic "74LVC14" or "74LVC1G17" isn't enough.** Vendors publish different
guaranteed limits for the same part number, so the BOM must name the Nexperia MPN, and any
substitute needs the same check.

**Parts:** 74LVC1G17GW,125 (Nexperia, SOT-353), C426705, extended, $0.11, ~19k at JLC. C_I
5 pF typ. Cost ≈ $2.00 per board, plus 18 × 100 nF.

**Fallback: 3 × Nexperia 74LVC14APW** (C6066, $0.23, 2.9k; or the -Q100 version C548122,
15.4k). It saves 15 packages and 15 caps. Polarity is inverted (GPIO high = asserted). Use it
if placement count matters more than a specified unpowered state.

**Owner's reason for B:** besides meeting R2, one cluster of parts per bus line (FET, three
passives, 1G17, 100 nF) is a clean repeated layout that sits on its own trace by the
connector, which keeps stubs short.

**Bench check:** on the first board, sweep one input slowly and confirm VT+/VT− at our real
3.3 V supply.

**LA tap (decided 2026-09-25): one 100 Ω series resistor per receiver output**, placed at
the 1G17 output and running to the LA header. The MCU trace comes straight off the same
output. Two more 100 Ω resistors go on the firmware marker pins. That's 20 in total, C25076
(basic).
- The receivers are already Schmitt buffers at 3.3 V CMOS, so R4a needs no second buffer
  bank. That rejects 3 extra chips.
- A short or a mis-plugged probe at the header draws at most 3.3 V / 100 Ω = 33 mA, inside
  the 1G17's ±50 mA absolute maximum (Nexperia Rev. 16.1). The MCU input stays valid.
- 100 Ω plus the 1G17's roughly 20–25 Ω output resistance roughly matches a ribbon or jumper
  lead (about 100–150 Ω, typical, not measured). That source-terminates the lead and damps
  ringing.
- The Digital Discovery probably has its own input protection (owner; not checked against
  Digilent's reference manual). The resistors cost nothing either way.
- Still to do: the header pinout matched to the Digital Discovery's 2×16 input connector.
- **Termination (decided 2026-09-24): BlueSCSI v2's logic-chip terminator, redrawn.**
  A 2.85 V LDO feeds 74LVT245s whose A inputs are tied high, and their B outputs drive
  18 × 110 Ω to the bus lines. (Ours, as of 2026-09-26: 2.83 V, SN74LVTH245A, and each 110 Ω made of
  2 × 220 Ω 0402 in parallel, R006.) **Tie A1–A8 and DIR straight to the rail** (DIR high =
  A→B; DIR low would make A outputs fight the ties, and bus-hold inputs mustn't get pull
  resistors, R039). Unused B7/B8 stay unconnected. `/OE` is the enable. Two '245s give 16 channels. BlueSCSI
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
    **Correction 2026-09-26 (R026):** Ioff only applies at VCC = 0, i.e. when nobody supplies
    TERMPWR. Whenever TERMPWR is up (ours or another device's), a disabled '245 is powered,
    and its B-port **bus-hold** keepers load each line through 110 Ω: ≥ 75 µA typical, up to
    +500 / −750 µA while a line switches, with the wrong sign compared with §5.4.1.2's
    I_IH/I_IL. Harmless in size (≤ 83 mV of pull), and only mid-chain (enabled termination is
    excluded from those limits). A non-bus-hold SN74LVT245B would avoid it; not worth a change.
  - It fits the SCSI-2 active-terminator window (§5.4.1: 100–132 Ω). 110 Ω plus the
    LVT's output resistance lands inside it (typical; the datasheet doesn't bound R_out, so
    measure it at bring-up and drop to 100 Ω if R_out > 22 Ω, R025), and the 2.83 V idle is
    above the 2.5 V minimum.
  Rejected: **dedicated terminator ICs** (UC5601/DS2107 class), which are hard to find and
  seldom stocked at JLC (unverified for us); **220/330 Ω passive**, which draws ~13 mA per
  line all the time, and needs a relay or FETs to switch it.
  To check when we draw it (unverified):
  - ~~LDO headroom~~: **decided 2026-09-24: TI TPS73701DCQR, 2.83 V since 2026-09-26** (see
    "Terminator LDO").
  - ~~Current per package~~: checked 2026-09-26. Six lines × ≤ 22.4 mA ≈ 134 mA per package;
    TI gives no per-VCC-pin limit, and each output (−32 mA I_OH) is within spec.
  - **Decoupling:** 100 nF at each '245 VCC; 10 µF on the rail at the LDO.
- **Terminator enable: a DIP switch (decided 2026-09-24).** One switch position grounds
  `/OE` (terminated), and a pull-up to the terminator rail (2.83 V; BlueSCSI uses 2.85 V) turns it off, as in BlueSCSI. A switch keeps its
  state when the board is unpowered and costs no GPIO. An MCU-controlled `TERM_EN` is
  **pencilled in only**: we add it if a GPIO expander ends up with a spare pin. If we do,
  the switch and the expander pin need a clean way to combine (e.g. a 3-position "off / on /
  MCU" switch). The expander could also read the switch back so the host can report it.
  **Wiring, if the expander pin happens (decided 2026-09-24):** DIP 1 sets the default,
  and DIP 2 lets firmware change it.

  ```
  2.83 V ──10k──┬── /OE of all three '245s   (high = off)
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
    device keeps the 2.83 V terminator rail alive. The dead expander's protection diodes then pull
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
4. ~~TERMPWR~~: decided: we supply it via an ideal diode (R2a). Part: LM66200 (U2), decided 2026-09-24;
   replaced the same day by a TPS259470A eFuse (see "TERMPWR switch").
   The owner's pin-26 measurement is now nice-to-have.
5. SE front end: terminator decided 2026-09-24; **drivers decided 2026-09-25 (14 × FDV301N,
   fallback SN74LVTH125PWR)**; **receivers decided 2026-09-25 (18 × Nexperia 74LVC1G17GW,
   fallback 3 × Nexperia 74LVC14APW)**. **LA isolation decided 2026-09-25: 100 Ω series resistors** (see "SCSI receivers"). Question closed.
   GPIO re-check done: sharing pins was rejected (see "SCSI drivers"), so it stays 32 dedicated
   pins and no pins are freed.
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
   LM66200 ×2** (see "Ideal diodes"); U2 became an eFuse (2026-09-24) and U1 a TPS2116 mux (2026-09-26).
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

11. **Bench test before the JLC order (decided 2026-09-26, R111):** an FT232H breakout + a Pico 2 W
    run FT1248 (and, if needed, the 245 FIFO) and the macOS `/dev/cu.usbserial-*` path. It runs in
    parallel with the KiCad schematic and **must finish before the board is ordered**, so a
    disappointing FT1248 changes the GPIO plan while it's still a schematic.
12. **RP2350 stepping (decided 2026-09-26, R034/R111):** plan for A4 silicon; keep everything that
    makes A2 safe (E9 pull-downs, E14 note). `picotool info -a` shows the revision at bring-up.
13. ~~Open for the owner's second pass~~ **(accepted by the owner, 2026-09-26):** R059 asked to scale up the bench eFuse string
    for < 10 µA reverse-polarity current, but that conflicts with R061's over-voltage accuracy
    (see "Bench 5 V input protection"). Kept at 510 k (~28 µA, meets TI's ≥ 350 kΩ footnote).

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
- 2026-09-24: Accepted: TERMPWR eFuse (second TPS259470A) replaces LM66200 U2 + polyfuse. Power diagram updated.
- 2026-09-24: FT232H → FT232HL (LQFP; QFN out of stock). FT232H crystal = ABM8-272-T3 (one crystal part ×3). Cheaper bridges (CH347F, CH32V305, FX2LP) rejected for v1. Wrote `parts-list.md`.
- 2026-09-25: SCSI drivers: 14 × FDV301N (open-drain on every driven line), SN74LVTH125PWR as the fallback. Pin sharing and a serial input expander were considered and rejected; it stays 32 dedicated GPIO. Corrected the capacitance budget (the terminator is excluded per §5.4).
- 2026-09-25: SCSI receivers: 18 × Nexperia 74LVC1G17GW (I_OFF specified; thresholds guaranteed at 3.0 V, interpolated at 3.3 V). Fallback 3 × Nexperia 74LVC14APW. TI's LVC14A fails VT− and Nexperia's 2G17/3G17 fail VT+, so the BOM must pin the vendor.
- 2026-09-25: LA tap: 100 Ω series resistor per receiver output (and on the 2 markers); no second buffer bank. Closes open question 5.
- 2026-09-25: RP2350B pin map accepted (SCSI blocks in connector order; ATN/BSY/SEL on the CPU, RST CPU-only; FT1248 0 Ω rework links; E9 → 4.7 kΩ gate pull-downs). Expander pinout accepted (P01 = TERMPWR_EN_N). Debug: TC2030-IDC pads + J-Link EDU. All resistor values set; CC reference now a CJ431 with a 10 k/1 µF filter; TERMPWR enable node pulled up to 3.3 V; 3.3 V LDO divider 1 %.
- 2026-09-26: eFuse caps: C_dVdt 2.2 nF on both (~5.5 ms ramp), ITIMER open with unfitted pads. The TERMPWR enable (via OVLO) bypasses dVdt and ramps at the 1.22 A limit (~0.2 ms): accepted.
- 2026-09-26: Full design review: `docs/design-review-2026-09-26.md` (1 High, ~22 Med, questions for a second pass). Trivial doc slips fixed in place; design changes not yet applied.
- 2026-09-26: Applied the approved design-review fixes (`docs/design-review-2026-09-26.md`): U1 → TPS2116 priority mux (bench first) + VBUS snubber; bench eFuse OVLO 5.35 V, EN Zener, ILIM 2.22 A, 50 V input cap, SMF15CA; TERMPWR OVLO divider, TERMPWR sense on GPIO 46 (ADC) replacing TERMPWR_OK, LED 10 k; terminator 2.83 V + 270 Ω bleed, 2 × 220 Ω per line, DIR/A ties; LDO EN dividers and caps; CJ431 470 Ω and recomputed margins; PSRAM CS1 3.3 k; 4th DVDD 4.7 µF; ATN on PIO0; FT232H powered per DS Fig. 6.2 with its support parts, 33 Ω on FT1248, WR#/SIWU# pull-ups; CH334 reset via Schottky, no pull-up, 10 µF; RESERVED pins grounded; PIO sketch rewritten; firmware rules section; power budget and heat updated.
- 2026-09-26: KiCad project started at `pcb/scsi-adapter.kicad_pro` (KiCad 9 format, so both 9 and 10 open it). Stackup is JLC04161H-7628, JLC's default 1.6 mm 4-layer: 1 oz outer, 0.5 oz inner, 0.2104 mm 7628 prepreg (Dk 4.4), 1.065 mm core (Dk 4.6), from jlcpcb.com/impedance (read 2026-09-26). The finish in the stackup is ENIG (flatter pads for the 0.4 mm QFN-80); this only records intent, and the finish is really chosen when ordering. Board Setup minimums follow JLC's 4-layer capabilities with a little margin: 0.1 mm track and space, vias 0.3 mm drill on 0.5 mm pads (the no-surcharge range; JLC's minimum is 0.15/0.25), 0.3 mm copper to edge, silkscreen text 1.0 mm tall with 0.15 mm stroke. The Default net class is 0.2 mm track, 0.15 mm clearance, and 0.6/0.3 mm vias. `scsi-adapter.kicad_dru` adds a 0.15 mm PTH annular ring, 0.45 mm pad hole-to-hole, 0.5 mm minimum NPTH, 0.15 mm SMD pad-to-pad, and 0.28 mm PTH-to-track, each tested against a deliberately bad pad. USB_HS net class: 90 Ω differential on L1 over L2 (non-coplanar), 0.29 mm width, 0.20 mm gap, from JLC's impedance calculator for the standard JLC04161H-7628 (11.44 mil / 8 mil; the 3313A stackup gives the same, while 7628A/B/C need 0.38–0.58 mm because their L1→L2 dielectric is thicker). Order with impedance control on and JLC04161H-7628 selected; with no stackup requirement JLC could build something else. Keep top-layer pour ≥ ~0.6 mm from the pair so the non-coplanar model holds. Still open: board outline; assigning USB nets to USB_HS in the schematic.
