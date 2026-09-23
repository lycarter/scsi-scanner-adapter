# Phase 4: Software

Two layers:

1. **Driver-board firmware** (RP2350 or similar): the SCSI initiator state machine, a
   transport to the host, and the listen-only sniffer mode.
2. **Host software**: a library that speaks the D4000 command set (identify, calibrate,
   focus, set window, scan, read lines), plus a scanning application.

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

- Which host OSes matter to you: macOS, Linux, Windows?
- GUI app, CLI, or both? A web UI served from the host tool?

## Log

- 2026-09-23: Placeholder created.
