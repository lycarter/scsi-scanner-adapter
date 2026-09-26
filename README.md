# scsi-scanner-adapter

Bringing a Howtek Scanmaster D4000 drum scanner (1990s, SCSI-2) to modern computers
with custom hardware (USB-C ↔ SCSI) and open scanning software.

## Status

Phase 0: requirements and architecture decisions.

## Phases

| # | Folder | What |
|---|--------|------|
| 1 | [`design_docs/1-bus-capture/`](design_docs/1-bus-capture/NOTES.md) | Logic analyzer, passive tap and capture tooling for watching the G4 ↔ scanner bus |
| 2 | [`design_docs/2-reverse-engineering/`](design_docs/2-reverse-engineering/NOTES.md) | Decode the command set and data flow (bus captures + firmware/software analysis) |
| 3 | [`design_docs/3-driver/`](design_docs/3-driver/NOTES.md) | USB-C ↔ SCSI initiator PCB that also works as a listen-only bus sniffer |
| 4 | [`design_docs/4-software/`](design_docs/4-software/NOTES.md) | Driver firmware and host scanning software |

Shared background: [`docs/scanner-facts.md`](docs/scanner-facts.md), [`docs/reference-inventory.md`](docs/reference-inventory.md), [`docs/decisions.md`](docs/decisions.md).

## Known-good baseline

A Power Mac G4 on Mac OS 9, running SilverFast, scans successfully with this scanner.
