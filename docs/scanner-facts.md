# Howtek D4000: facts

Facts we have verified, each with its source. Anything inferred is marked **(inferred)**.
Paths are relative to `reference/HOWTEK/`.

## Physical and electrical

- Scan area: 11.0" (X, around the drum) × 11.8" (Y, along the carriage). Native
  resolutions are 4000/N dpi, from 4000 down to ~42 dpi (`D4000_4500/MISC/4500nativeres.PDF`).
- The aperture wheel has 12 apertures, 6.35–254 µm. The default aperture is matched to the
  dpi, e.g. 6.35 µm at 4000 dpi.
- Drum: DC servo motor at 300–1200 RPM, depending on resolution. **One RGB line per
  revolution.** The drum encoder is 2500 PPR according to a handwritten training note.
  The carriage is a stepper motor on a lead screw with a 4000-step codewheel
  (service guide §2.1.3, §3.4; training handouts p.8).
- The optics use three PMTs (R, G, B). Signals go to a log/linear amp and then a 12-bit ADC,
  giving a 12-bit or 8-bit output through a LUT (§2.1.2).
- Power: 300 W max. Internal rails are +5, ±12 and +24 V.

## Internal architecture

All boards sit on an ISA-bus motherboard (§3.3; training handouts pp.5, 8, 9):

| Board | CPU | Role |
|---|---|---|
| Motherboard (MB/MP) | 386SX-16, SCATsx chipset, 2 MB RAM | Main control. Boots from EPROM, then runs FLASH code held on the VDC board |
| IOC (I/O Controller) | 80C186-16 + **WD33C93A** SCSI controller | SCSI and GPIB host interface. Talks to the MP through dual-port RAM |
| SSC (Subsystem Controller) | 80C188-16 | Drum and carriage motion, timing to the VDC. Drives the SSD |
| SSD (Subsystem Driver) | — | Motor, lamp and sensor drivers |
| VDC (Video Digital Controller) | — | ADC data, LUT RAM, FLASH EPROMs, control panel, door and sled sensors, PMT HV control |
| IEC (Image Enhancement Controller) | Unknown DSP (see firmware) | USM sharpening, CMYK conversion. Optional ("CMYK only") |

- IOC status LEDs: both on = booting, green = OK, red = fault.
- LCD boot markers, in order: `v` (video board), `i` (IOC), `s` (SSC), `f` (firmware init),
  then `ONLINE`. A hang shows the letter in the lower-right corner of the LCD.
- The boot-status code on the LCD says where the firmware came from. `BCxx` = EPROM
  (no FLASH), `FBxx` = forced EPROM, `FFxx` = FLASH. Revision `R1xx` = EPROM, `R5xx` =
  FLASH (D4000).

## Host interface

- **SCSI:** narrow (8-bit) **single-ended**. The scanner has two 50-pin connectors and
  **no internal termination**. An active terminator must go on the unused port. The factory
  SCSI ID is **4**; it can be changed from the front panel.
- **GPIB:** some units also have a 24-pin GPIB connector. The firmware and tools support it,
  but it's irrelevant to us.
- WD33C93A: SCSI-2, supports async and sync transfers. The sync rate the D4000 actually
  negotiates is **unknown**; we'll find out from bus captures. The sibling 7500 uses up to
  10 MHz sync.
- INQUIRY vendor/product (from the IOC firmware strings): `HOWTEK  ` / `D4000           `,
  with a revision string built at runtime.
- The command set appears to be the **standard SCSI-2 Scanner device class**. The Howtek HSI
  library in MacUtil 4.0.1 names these CDBs: TEST UNIT READY, INQUIRY, REQUEST SENSE,
  MODE SELECT/SENSE, LOG SELECT/SENSE, RESERVE/RELEASE, SET WINDOW, GET WINDOW, SCAN, READ,
  SEND, GET (DATA BUFFER) STATUS, WRITE BUFFER (firmware download), SEND/RECEIVE DIAGNOSTIC.
  **(Opcodes and parameters are not yet verified.)**
- The Howtek service guide recommends that the scanner be the only device on the bus and
  lists Adaptec 1740/2740/2842 host adapters for PCs.

## Firmware

The D4000 FLASH image is `R535`, dated 1995-12-19 (`D4000_4500/Firmware/4000/R535.exe`,
a zip). `R535.HEX` is a text header followed by 5 Intel-HEX modules, one per processor:

| Module | Load range | Start (CS:IP) | Identity |
|---|---|---|---|
| 0 | 0x40000–0x51ECF | 4000:3AB0 | "Primary DownLoader FLASH (PLF) R309", the flash updater |
| 1 | 0x00020–0x1FE9F | 0000:0000 | MP main firmware: "D4000 R535", menus, command parser (`CMD_*` debug strings) |
| 2 | 0x00000–0x0AA9F | 0000:0000 | IOC R125: 80C186, WD33C93A driver, GPIB, **diagnostic terminal menu** |
| 3 | 0xF0000–0xF215F | F000:0000 | SSC version 112 (80C188), UART debug |
| 4 | 0xE9600–0xFFFFF | none | IEC R129. Not x86 code; architecture TBD |

The 4500 image (`R813`) has the same layout. **Don't flash 4500 firmware onto the D4000.**
The two models have different EPROM sets and checksums (training handouts p.6).

## Error codes

These come from the service guide (§4, §8). Codes 1–39 are "default" errors: parameter
validation failures such as the X/Y start/length limits, color channel, number of bits,
data packing, LUT and aperture. 400–600 are warnings. 700+ are fatal, e.g. F716 = undefined
IO command between MP and IOC. Expect these codes to show up in SCSI sense data.

## Data-rate estimate **(inferred, to be measured)**

At 4000 dpi, 11" × 4000 = 44,000 px per line. Assuming 300 RPM (5 lines/s), 16-bit RGB comes to
≈ 1.3 MB/s and 8-bit RGB to ≈ 0.66 MB/s. At lower dpi the drum spins faster, which gives
similar rates, so a **~1.5 MB/s sustained ceiling** is plausible. Measure this in Phase 2.
