# Phase 4: Software

Two layers:

1. **Driver-board firmware** (RP2350 or similar): the SCSI initiator state machine, a
   transport to the host, and the listen-only sniffer mode.
2. **Host software**: a library that speaks the D4000 command set (identify, calibrate,
   focus, set window, scan, read lines), plus a scanning application.

## Decided

- **Generic SCSI passthrough (2026-09-24, with Phase 3).** The board knows nothing about
  scanners; all Howtek logic lives here on the host. Scan-area selection needs a preview UI,
  which is the main reason. **Protocol requirement:** make each command a self-contained
  message (CDB, data-out, expected data-in length). A "script" is then just saved messages,
  so the optional firmware script runner (Phase 3, open question 6, option B) can replay
  them from SD. The protocol must also let data-in arrive after the command completes,
  because the board may spill a large READ to PSRAM/SD and drain it later.

- **Host OSes: macOS and Windows (2026-09-24).** Linux isn't required, so a SANE backend drops
  to nice-to-have. On Windows, FTDI's D2XX driver installs through Windows Update.
  libusb-based access (pyftdi) would need WinUSB swapped in (Zadig), so prefer D2XX there
  (unverified for the FT1248 mode: check that D2XX treats it like the FIFO modes).
- **UI: a web UI served by the host tool (2026-09-24).** The host tool runs locally and serves
  a page for preview, scan-area crop and scan settings. One UI for both OSes, with no native
  toolkit. The scanner logic stays in the host library underneath (see "Generic SCSI
  passthrough").

## Early thoughts (not decisions yet)

- Design the host↔board protocol as "**SCSI passthrough**": the host sends a CDB, a data-out
  buffer and the expected data-in length, and gets back status, sense and data. Then all
  scanner knowledge lives in host software, where it's easy to iterate on. The firmware stays
  dumb and generic. It's the same split as Linux `sg` / ASPI, and it means the board could
  also drive other SCSI devices.
- The host library should be cross-platform, e.g. Python for exploration and Rust or C
  later if needed. Consider **SANE backend** compatibility so existing frontends (and
  VueScan-style workflows) could work.
- Output: 16-bit linear TIFF/DNG plus metadata. Drum-scanner users care about raw
  linear data and their own color pipeline.
- Nice-to-haves from the references: 8000 ppi addressing (see the aperture study),
  per-aperture native resolutions, and autofocus/interactive focus.

## Open questions

- ~~Which host OSes?~~ macOS + Windows (2026-09-24).
- ~~GUI, CLI or web UI?~~ Web UI served from the host tool (2026-09-24).

## Log

- 2026-09-23: Placeholder created.
- 2026-09-24: Passthrough accepted. Protocol notes: self-contained command messages (replayable), with data-in allowed after the command completes.
- 2026-09-24: Host OSes macOS + Windows; UI = web UI served by the host tool.
