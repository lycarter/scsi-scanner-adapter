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
- **macOS data path: Apple's serial node is an option (2026-09-26, decide on hardware).** Apple's
  built-in DriverKit FTDI driver (`com.apple.DriverKit-AppleUSBFTDI`) binds 0403:6014, so D2XX
  and libusb may need root. Instead, the host tool could open `/dev/cu.usbserial-*` raw and use
  it as the byte pipe. Read from the driver code on macOS 26 (Darwin 25.6), not tested:
  - The data path doesn't care about the chip mode; it strips 2 status bytes per packet.
  - It keeps only one 512 B read in flight, so throughput vs. R3's 1.5 MB/s is unknown. The
    guess is 3–10 MB/s before the tty layer. A slow host costs speed, not data (flow control).
  - The latency timer is set with `ioctl(IOSSDATALAT)`; firmware can also send the FT1248
    flush command (0x4) after short replies.
  - The driver opens the interface only while the tty is open, so unprivileged pyftdi might
    work when the port is closed. That's unverified.
  - FTDI's own VCP dext may also be installed and compete for the chip.

  Details: `docs/design-review-2026-09-26.md` R052. **Bench test when hardware exists:** measure
  `/dev/cu.*` throughput, and try pyftdi without sudo while the port is closed. Then choose
  between the serial node, root, and a custom PID.
- **Firmware rules from the Phase 3 design review (2026-09-26):** bus-release deadlines, SRAM-resident
  code, no flash writes during a SCSI session, FT1248 mode check, TERMPWR checks, sniffer modes.
  They live in `design_docs/3-driver/NOTES.md`, "Firmware rules from the design review", next to the PIO sketch.
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
- 2026-09-26: macOS data path via Apple's serial node recorded as an option (driver read from code, untested); decide after a bench test.
