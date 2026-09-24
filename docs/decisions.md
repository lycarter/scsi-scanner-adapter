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
| 2026-09-23 | 3/4 | Board firmware is a generic SCSI passthrough; the scanner logic lives on the host | proposed |
| 2026-09-23 | 3 | Over-spec USB: high speed via an external bridge (RP2350 USB is full-speed only); don't wait for Phase 2 | accepted |
| 2026-09-23 | 3 | Power: 5 V only, from USB-C (read the CC current advertisement; no PD controller), plus a protected bench 5 V input ORed via ideal diodes | accepted |
| 2026-09-23 | 3 | On-board PSRAM as a stall buffer (working choice: 8 MB QSPI) | accepted |
| 2026-09-23 | 3 | SCSI connector: IDC50 box header, plus an unpopulated HD50 footprint on the same nets | accepted |
| 2026-09-23 | 3 | MCU is the RP2350B (48 GPIO) | accepted |
| 2026-09-23 | 3 | microSD slot (SDIO), for spill-over and for standalone scan development | accepted |
| 2026-09-23 | 3 | Supply TERMPWR (required of initiators by SCSI-2 §5.4.3: 4.25–5.25 V, ≥900 mA) through an ideal diode, polyfuse and jumper | accepted |
| 2026-09-23 | 3 | SE front end: 74LVT family with per-bit open-drain data, following BlueSCSI v2 | proposed (owner researching) |
| 2026-09-23 | 3 | Hardware redrawn from scratch and kept MIT; BlueSCSI (CERN-OHL-S) and ZuluSCSI/BlueSCSI firmware (GPL-3) are reference only | accepted |
| 2026-09-23 | 3 | TERMPWR enable is hardware logic (CC ≥1.5 A OR bench present) with a status LED; no MCU pin | accepted |
| 2026-09-24 | 3 | USB 2.0 hub chip behind the USB-C: FT232H (HS data) + RP2350 native USB (FS: ROM-bootloader updates, CDC console replacing the debug UART) | accepted |
| 2026-09-24 | all | Parts lookup: pcbparts MCP (project `.mcp.json`) for JLC search/stock/tier, `tools/lcsc.py` for LCSC store stock/MOQ. Rejected jlcsearch-based tools (stale stock) and @jlcpcb/mcp (no preferred tier, keyword only) | accepted |
| 2026-09-24 | 3 | Switchable active terminator: 2.85 V LDO → 3 × 74LVT245 (inputs tied high, `/OE` = enable, 6 lines each, no P-FETs) → 18 × 110 Ω, following BlueSCSI v2 | accepted |
| 2026-09-24 | 3 | Terminator enable is a DIP switch. MCU `TERM_EN` is pencilled in only, if a GPIO expander has a spare pin. If it is fitted: DIP 1 = default on/off, DIP 2 = firmware may override | accepted |
| 2026-09-24 | 3 | GPIO budget: FT232H in 4-bit FT1248 (7 pins), microSD in 1-bit SDIO (3), I²C expander for LEDs/card detect/TERMPWR_OK (2): 47 of 48. PIO0 = SCSI (GPIO 0–31), PIO1 = FT1248, PIO2 = SDIO (both base 16). Revisit if the SE front-end decision frees pins | accepted |
