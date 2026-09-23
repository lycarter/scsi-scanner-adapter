# scsi-scanner-adapter

Bringing a Howtek Scanmaster D4000 drum scanner (1990s, SCSI-2) to modern computers
with custom hardware (USB-C ↔ SCSI) and open scanning software.

## Status

Phase 0: requirements and architecture decisions.

## Phases

| # | Folder | What |
|---|--------|------|
| 1 | [`1-bus-capture/`](1-bus-capture/NOTES.md) | Logic analyzer, passive tap and capture tooling for watching the G4 ↔ scanner bus |
| 2 | [`2-reverse-engineering/`](2-reverse-engineering/NOTES.md) | Decode the command set and data flow (bus captures + firmware/software analysis) |
| 3 | [`3-driver/`](3-driver/NOTES.md) | USB-C ↔ SCSI initiator PCB that also works as a listen-only bus sniffer |
| 4 | [`4-software/`](4-software/NOTES.md) | Driver firmware and host scanning software |

Shared background: [`docs/scanner-facts.md`](docs/scanner-facts.md), [`docs/reference-inventory.md`](docs/reference-inventory.md), [`docs/decisions.md`](docs/decisions.md).

## Known-good baseline

A Power Mac G4 on Mac OS 9, running SilverFast, scans successfully with this scanner.
