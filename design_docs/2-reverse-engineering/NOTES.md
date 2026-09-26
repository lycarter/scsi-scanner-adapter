# Phase 2: Reverse engineering

Goal: document the D4000's SCSI command set and data flow well enough to write our own
driver. That means identification, setup (windows, modes, LUTs, calibration and focus), scan
start, data readout and formats, status/sense handling, and error recovery.

## Strategy: three independent sources that cross-check each other

1. **Bus captures** (needs Phase 1 and an LA). This is the ground truth for what SilverFast
   actually sends and in what order, plus the timing, sync negotiation, disconnects and
   data rates.
2. **Host-software analysis.** Howtek's own tools name the commands:
   - MacUtil 4.0.1 contains the HSI library and a CDB name table (68k; Ghidra handles 68k).
   - Aztek Trident 4 (Mac, in `7500/Firmware_R014/`).
   - The SilverFast Howtek plug-in on the G4.
   - The DOS FST / SL4HTK tools (16-bit x86, ASPI calls).
3. **Firmware analysis.** The R535 HEX splits into per-CPU images. The MP (386 real/protected
   mode?) and the IOC (80C186) are x86, so Ghidra works. The IOC has the WD33C93A driver and
   the CDB dispatch. The MP has the `CMD_*` parser with debug strings, which read like
   source-level names.

## Zero-hardware leads to try first

- [ ] **HSI CDB dump on the G4.** In MacUtil 4.0.1's `Resources/HSI.INI`, set `[HASPI]
      CDB DUMP=1` (and `DEBUG`/`VERBOSE`), then run MacUtil. `CDB SCSI IDS=24` looks like a
      bitmask (0x18 = IDs 3 and 4). Output should go to `Resources:HSIDEBUG.TXT`. This only
      covers MacUtil's traffic (download and FST), but it's free.
- [ ] Record the **INQUIRY data and firmware revision** the unit reports (the LCD shows it at
      boot; SCSIProbe on OS 9 shows it too). This tells us whether it's R535 or something else.
- [ ] Look for a **diagnostic serial port** on the IOC and SSC boards. The IOC firmware has a
      terminal menu ("Echo host GPIB I/O commands", "Echo all dual port memory command
      entries", "Report current IOC status"). **If that terminal is reachable, the scanner
      will log the host commands itself.** This needs photos of the IOC board.
- [ ] Split and disassemble R535 in Ghidra. Map the MP↔IOC dual-port-RAM command protocol
      and the CDB dispatch table.
- [ ] ZDebug (uploaded by FST/MacUtil) offers MEMRD/IORD peek. It could dump the boot EPROMs
      and the live state.

## Howtek-specific parameters known so far (names only, no wire format)

These are the internal command handlers in the MP firmware (R535 module 1 `CMD_*` debug strings,
with the argument names from their printf formats). SCSI CDBs and window/mode fields most
likely map onto these. **Opcodes, byte offsets and encodings are still unknown.**

| Group | Handlers (args) |
|---|---|
| Geometry | `scan_area` (Xoffset, Xlength, Yoffset, Ylength), `resolution` (X/Y dpi, iec_mode), `interpolation` / `replication` (Xdpi, Ydpi, mode), `drum_speed`, `drum_position` |
| Optics | `set_aperture` (n), `set_focus_position` (n), `autofocus` (Xo, Xl, Yo, S), `lamp_mode_select` (reflective/transmissive) |
| Data format | `number_of_bits` (8/12), `color_channel`, `data_packing` (line/pixel), `mono_percentage` (r,g,b), `lineart` |
| Tone | `analog_collection_mode` (linear/log amp), `build_linear_lut` / `build_log_lut` (Min, Max, Gamma), `download_user_lut`, `blktable` on/off, `blkcutoff` |
| IEC (optional board) | `fir5x5_enhancement` on/off, `proprietary_enhancement`, `no_enhancement`, `saturation` on/off/parms, `subtractive_color` (CMY/CMYK) on/off, `press_control` |
| Misc | `id`, `scan`, `download`, `check_mode_*` |

Calibration modes seen in strings: FULL, RELOAD, SKIP, TWEAK, and CALIBRATION CACHE.
The error enum 1–39 in `docs/scanner-facts.md` lines up with these validators.

## Tools here

- `tools/ihex_split.py` splits a Howtek multi-module Intel-HEX into per-CPU binaries.

## Open questions

- Is sync transfer negotiated (SDTR)? If so, at what period and offset?
- Does the scanner disconnect and reselect during scans, or hold the bus?
- How does it behave when the host is slow: does it pause the drum or carriage, or error out?
  This decides the USB bandwidth requirement in Phase 3.
- Pixel format on the wire: 12-bit in 16-bit, "MAC vs PC format" (endianness?), and line vs.
  pixel packing.

## Log

- 2026-09-23: Reference survey done. The command set appears to be the SCSI-2 Scanner class.
  See `docs/scanner-facts.md`.
