# Decision log

One line per decision; details and rationale live in the phase `NOTES.md`.
Status: **proposed** (awaiting owner), **accepted**, **superseded**.

| Date | Phase | Decision | Status |
|---|---|---|---|
| 2026-09-23 | all | Four phases live in separate folders, each with its own `NOTES.md`. Shared facts go in `docs/` | accepted |
| 2026-09-23 | all | `reference/` stays out of git (43 MB, vendor copyright, Mac resource forks). `docs/sources.md` records where each item came from. Howtek files have no public link, so any fact we rely on is copied into our own notes | accepted |
| 2026-09-23 | 1 | Snooper v1 = buffered, Schmitt-input LA tap plus host switch. No MCU/FPGA on board | superseded (merged into driver board) |
| 2026-09-23 | 1 | Buy an external LA with ≥24 channels, ≥200 MS/s, scriptable (DSLogic U3Pro32) | superseded |
| 2026-09-23 | 1 | LA: Digilent Digital Discovery (32 ch at 200 MS/s, official WaveForms SDK), budget ≤ $1k | accepted |
| 2026-09-23 | 1 | Rigol DS1074Z is used for analog signal integrity, not as the LA | accepted |
| 2026-09-23 | 1 | "Loop-through-scanner" topology with switchable local terminators | superseded |
| 2026-09-23 | 1 | Start with a Pico 2 protocol-level sniffer (becomes the driver's listen mode). Defer the LA purchase until driver bring-up or an unexplained capture | accepted |
| 2026-09-23 | 3 | MCU-based driver, not FPGA or Linux SBC: RP2350B (PIO) + FT232H for USB HS. Accepted 2026-09-24; the GPIO overrun is to be fixed with other levers, not by switching to a one-chip HS MCU | accepted |
| 2026-09-23 | 1+3 | No snooper PCB. The driver board gets listen-only mode plus a buffered LA header, and the G4, scanner and driver share one multi-initiator daisy chain | accepted |
| 2026-09-23 | 3/4 | Board firmware is a generic SCSI passthrough; the scanner logic lives on the host. Accepted 2026-09-24 | accepted |
| 2026-09-23 | 3 | Over-spec USB: high speed via an external bridge (RP2350 USB is full-speed only); don't wait for Phase 2 | accepted |
| 2026-09-23 | 3 | Power: 5 V only, from USB-C (read the CC current advertisement; no PD controller), plus a protected bench 5 V input ORed via ideal diodes | accepted |
| 2026-09-23 | 3 | On-board PSRAM as a stall buffer (working choice: 8 MB QSPI) | accepted |
| 2026-09-23 | 3 | SCSI connector: IDC50 box header, plus an unpopulated HD50 footprint on the same nets | accepted |
| 2026-09-23 | 3 | MCU is the RP2350B (48 GPIO) | accepted |
| 2026-09-23 | 3 | microSD slot (SDIO), for spill-over and for standalone scan development | accepted |
| 2026-09-23 | 3 | Supply TERMPWR (required of initiators by SCSI-2 §5.4.3: 4.25–5.25 V, ≥900 mA) through an ideal diode, polyfuse and jumper | accepted |
| 2026-09-23 | 3 | SE front end: 74LVT family with per-bit open-drain data, following BlueSCSI v2 | superseded (drivers: FDV301N, 2026-09-25) |
| 2026-09-23 | 3 | Hardware redrawn from scratch and kept MIT; BlueSCSI (CERN-OHL-S) and ZuluSCSI/BlueSCSI firmware (GPL-3) are reference only | accepted |
| 2026-09-23 | 3 | TERMPWR enable is hardware logic (CC ≥1.5 A OR bench present) with a status LED; no MCU pin | accepted |
| 2026-09-24 | 3 | USB 2.0 hub chip behind the USB-C: FT232H (HS data) + RP2350 native USB (FS: ROM-bootloader updates, CDC console replacing the debug UART) | accepted |
| 2026-09-24 | all | Parts lookup: pcbparts MCP (project `.mcp.json`) for JLC search/stock/tier, `tools/lcsc.py` for LCSC store stock/MOQ. Rejected jlcsearch-based tools (stale stock) and @jlcpcb/mcp (no preferred tier, keyword only) | accepted |
| 2026-09-24 | 3 | Switchable active terminator: 2.85 V LDO → 3 × 74LVT245 (inputs tied high, `/OE` = enable, 6 lines each, no P-FETs) → 18 × 110 Ω, following BlueSCSI v2 | accepted |
| 2026-09-24 | 3 | Terminator enable is a DIP switch. MCU `TERM_EN` is pencilled in only, if a GPIO expander has a spare pin. If it is fitted: DIP 1 = default on/off, DIP 2 = firmware may override | accepted |
| 2026-09-24 | 3 | GPIO budget: FT232H in 4-bit FT1248 (7 pins), microSD in 1-bit SDIO (3), I²C expander for LEDs/card detect/TERMPWR_OK (2): 47 of 48. PIO0 = SCSI (GPIO 0–31), PIO1 = FT1248, PIO2 = SDIO (both base 16). If the SE front-end decision frees pins, switch to 4-bit SDIO first | accepted |
| 2026-09-24 | 3/4 | microSD is for spill only (A). A firmware CDB-script runner (from USB or an SD file) is an optional add-on later (B). No scanner logic in firmware: scan-area selection needs a preview UI on the host | accepted |
| 2026-09-24 | 3 | GPIO expander: TCA9555PWR (C465732, TSSOP-24, extended). INT goes to a test point + an unfitted 0 Ω link to the spare GPIO; firmware polls. No expander is high-Z when unpowered, so the TERM_EN limitation stays documented (no extra parts). Rejected: MCP23017 (costs more, GPA7/GPB7 output-only), TCA9535, XL9555 clone | accepted |
| 2026-09-24 | 3 | CC detection: LM393 dual comparator (C7955, basic) against a 0.66 V reference, giving a wired-OR CC_OK_N for the hardware TERMPWR enable, with a copy to the expander. Rejected: TUSB321 (extended, tiny QFN), ADC (needs firmware), transistor threshold (imprecise) | accepted |
| 2026-09-24 | 3 | Goal: one part type for every ideal diode (all are JLC extended). Choice: TI LM66200 (C3235556) ×2. U1 = USB/bench ORing (ON low, ST → source status). U2 = TERMPWR switch (ON pulled to 5 V, pulled low by wired-OR of CC_OK_N and bench-present). Rejected: LM66100 (body diode conducts when disabled), TPS2121 (fallback if the TERMPWR voltage budget fails) | accepted |
| 2026-09-24 | 3 | Terminator LDO: TI TPS73701DCQR (C56848) set to 2.80 V, fed from TERMPWR. SCSI-2 §5.4.1(b)(3) caps V_term at ≈2.96 V; 2.80 V keeps the worst-case tolerance inside 2.5–2.96 V. Rejected: AMS1117-2.85 (dropout, stock), 3.3 V LDO + divider (not stiff, loads the bus when disabled) | accepted |
| 2026-09-24 | 3 | USB hub: WCH CH334P (C5373042) with a fitted 12 MHz crystal and no external load caps. An English datasheet (V2.5) is in reference/; the owner required one. WCH says crystal-free mode may break the USB spec and may not be enabled on stocked parts. Rejected: FE1.1s, GL850G, USB2514B | accepted |
| 2026-09-24 | 3 | Bench 5 V connector: 2-pin 5.08 mm screw terminal plus a test loop per pole (hand-soldered). Rejected: barrel jack (12 V adapter risk), loops only, binding posts (revisit with the enclosure) | accepted |
| 2026-09-24 | 3 | Enclosure: 3D-printed case designed around the board later; placement open. v1 layout: external connectors on 1–2 edges, M3 mounting holes | accepted |
| 2026-09-24 | 4 | Host software targets macOS and Windows (Linux/SANE optional). UI is a web page served by the local host tool | accepted |
| 2026-09-24 | 3 | RP2350B support parts reused from scanlight `sl_v4` (part numbers only, schematic redrawn): ABM8-272-T3 + 2 × 15 pF + 1 kΩ, USB 27 Ω (0603 C25190, preferred), only the crystal is extended. Buttons deferred: owner's through-hole stock, hand-soldered. Core regulator, flash size and 3.3 V regulator still open | accepted |
| 2026-09-24 | 3 | One 12 MHz crystal type: ABM8-272-T3 (C20625731) for the RP2350B and the CH334 hub. The CH334's ~16 pF internal caps suit CL 10 pF; unfitted load-cap pads on the hub as insurance. Rejected: YXC C9002 (CL 20 pF, ESR 80 Ω) | accepted |
| 2026-09-24 | 3 | RP2350B support parts per the RP2350 guide, basic where possible: W25Q128JVSIQ 16 MB flash, 100 nF / 4.7 µF / 10 µF decoupling, 33 Ω AVDD filter, 10 kΩ CS1 pull-up. Inductor: Abracon AOTA-B201610S3R3-101-T (extended; JLC has no no-fee power inductors). Owner may search more | accepted |
| 2026-09-24 | 3 | FT1248: no dev-board test; assume it works as advertised. Fallback: rework the first board, dropping microSD + the I²C expander to free 6 GPIO for 8-bit FT1248 or the 245 FIFO (same FT232H pins). Pin order and pads planned for it | accepted |
| 2026-09-24 | 3 | Power budget: 3.3 V ≈165/420 mA, 5 V ≈0.52/1.4 A with TERMPWR (fits a 1.5 A USB-C port). 3.3 V regulator = second TPS73701 (no new fee). FT232H VREGIN from 5 V; CH334 in external 3.3 V mode. Rejected: AMS1117 (dropout), buck (noise, parts) | accepted |
| 2026-09-24 | 3 | Core-regulator inductor locked: Abracon AOTA-B201610S3R3-101-T (C42411119, $0.28) | accepted |
| 2026-09-24 | 3 | PSRAM: APS6404L-3SQR-SN (C5333729), 8 MB, 3.3 V, SOP-8, on CS1 = GPIO 47. Rejected APS1604M (2 MB) | accepted |
| 2026-09-24 | 3 | Bench input protection: TI TPS259470ARPWR eFuse (C3662799): −15 V to 28 V tolerant, OVLO ≈ 5.7 V, current limit ≈ 2 A, auto-retry. Rejected: TVS crowbar (clamps above U1's 6 V), discrete OV cut-off, 6 V-class switches | accepted |
| 2026-09-24 | 3 | 4-layer board. Outline and placement: owner's hand layout after the schematic | accepted |
| 2026-09-24 | 3 | Connectors: USB-C footprint HRO TYPE-C-31-M-12 (owner's part, hand-soldered); IDC50 keyed box header (C30006); HD50 generic half-pitch footprint, part sourced later (none stocked); microSD SHOU HAN TF PUSH (C393941) | accepted |
| 2026-09-24 | 3 | ESD: discrete JLC-preferred diodes, none with a rail pin (so an unpowered board doesn't clamp the bus): H5VUD5BB on USB D± and 18 SCSI lines, H7VL10B on CC, SMF6.0A on VBUS and TERMPWR, SMF15A unfitted on the bench terminal | accepted |
| 2026-09-24 | 3 | TERMPWR: second TPS259470A eFuse (≈1.2 A limit, OVLO as active-low enable) replaces LM66200 U2 + polyfuse. A PTC can't hold 0.9 A and trip ≤1.5 A | accepted |
| 2026-09-24 | 3 | FT232H package: FT232HL (LQFP-48, C51997, $9.36); the QFN is out of stock. Cheaper bridges rejected for v1: CH347F (UART too slow, driver), CH32V305 (second firmware; v2 cost-down candidate), FX2LP | accepted |
| 2026-09-24 | 3 | FT232H crystal: ABM8-272-T3 + 2 × 15 pF, so the board has one crystal part (×3). FTDI's ±30 ppm note is stricter than USB HS needs | accepted |
| 2026-09-25 | 3 | SCSI drivers: 14 × onsemi FDV301N (C15310), open-drain on every driven line (GPIO → 100 Ω → gate, 10 kΩ pull-down — 4.7 kΩ from 2026-09-25 for RP2350-E9 — DNP 22 pF). Meets V_OL ≤ 0.5 V at 48 mA hot; the RP2350's reset pull-downs keep them off. Fallback: 4 × SN74LVTH125PWR (C7042) if routing, placement cost or preference changes. Pin sharing and a serial input expander rejected: stays 32 dedicated GPIO | accepted |
| 2026-09-25 | 3 | SCSI receivers: 18 × Nexperia 74LVC1G17GW (C426705), one per line next to its driver cluster, 3.3 V, 100 nF each. I_OFF ±2 µA specified (R2). Thresholds guaranteed at 3.0 V, interpolated at 3.3 V (~0.16 V margin). Fallback: 3 × Nexperia 74LVC14APW (thresholds guaranteed, I_OFF unspecified). Rejected: TI LVC14A (VT− 0.6 V), Nexperia 2G17/3G17 (VT+ 2.2 V). BOM must name the vendor | accepted |
| 2026-09-25 | 3 | LA header tap: 100 Ω series resistor on each receiver output and marker pin (20 × C25076, basic). The 74LVC1G17 receivers serve as R4a's Schmitt buffers; a second buffer bank was rejected | accepted |
| 2026-09-25 | 3 | RP2350B pin map (`3-driver/blocks/5-rp2350-pinout.md`): SCSI inputs GPIO 0–17 and gates 18–31, both in SCSI-2 connector order; data + ACK on PIO0, ATN/BSY/SEL on the CPU, RST CPU-only; FT1248/I²C/SD/markers/CS1 on 32–47; 11 × 0 Ω links for the FT1248 → FIFO rework. Gate pull-downs 4.7 kΩ (RP2350-E9 needs ≤ 8.2 kΩ). Expander pins accepted (P01 = TERMPWR_EN_N) | accepted |
| 2026-09-25 | 3 | Debug: Tag-Connect TC2030-IDC footprint (1 VCC, 2 SWDIO, 3 RUN, 4 SWCLK, 5 GND, 6 NC) and the owner's J-Link EDU via an ARM20-CTX adapter. Rejected: ST-Link V2 (not a supported RP2350 path), Pi Debug Probe (no TC2030 adapter) | accepted |
| 2026-09-25 | 3 | Resistor values set (NOTES "Resistor and small-part values"). CC reference is now a CJ431 (C3113) with a 10 k/1 µF input filter; the rail-derived reference failed worst case. TERMPWR enable node pulled up to 3.3 V. 3.3 V LDO divider 1 % (47 k/27 k), not 0.1 %. R_ILM 2.4 k + 330 Ω replaces the extended 2.74 kΩ | accepted |
