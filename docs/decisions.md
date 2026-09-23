# Decision log

One line per decision; details and rationale live in the phase `NOTES.md`.
Status: **proposed** (awaiting owner), **accepted**, **superseded**.

| Date | Phase | Decision | Status |
|---|---|---|---|
| 2026-09-23 | all | Four phases live in separate folders, each with its own `NOTES.md`. Shared facts go in `docs/` | accepted |
| 2026-09-23 | all | `reference/` stays out of git (43 MB, vendor copyright, Mac resource forks) | proposed |
| 2026-09-23 | 1 | Snooper v1 = buffered, Schmitt-input LA tap plus host switch. No MCU/FPGA on board | superseded (merged into driver board) |
| 2026-09-23 | 1 | Buy an external LA with ≥24 channels, ≥200 MS/s, scriptable (DSLogic U3Pro32) | superseded |
| 2026-09-23 | 1 | LA: Digilent Digital Discovery (32 ch at 200 MS/s, official WaveForms SDK), budget ≤ $1k | proposed |
| 2026-09-23 | 1 | Rigol DS1074Z is used for analog signal integrity, not as the LA | accepted |
| 2026-09-23 | 1 | "Loop-through-scanner" topology with switchable local terminators | superseded |
| 2026-09-23 | 3 | MCU-based driver, not FPGA or Linux SBC. Lean: RP2350 (PIO) + FT232H for USB HS | proposed |
| 2026-09-23 | 1+3 | No snooper PCB. The driver board gets listen-only mode plus a buffered LA header, and the G4, scanner and driver share one multi-initiator daisy chain | accepted |
| 2026-09-23 | 3/4 | Board firmware is a generic SCSI passthrough; the scanner logic lives on the host | proposed |
