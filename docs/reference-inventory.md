# Reference inventory and leads

This is what's in `reference/` (untracked) and how useful each item is.
Where each item came from, and how to rebuild the folder, is in `sources.md`.
★ = high-value lead for Phase 2.

## D4000 / 4500: our scanner family (`reference/HOWTEK/`)

| Path | What | Notes / leads |
|---|---|---|
| `D4000_4500/Scanmaster 4500 Service Guide/*.pdf` | Scanned service guide, no OCR text | 02 theory, 03 boards, 04 troubleshooting and error table, 08 error enum, 09 training handouts (block diagrams, CPU types, calibration flow). Covers the 4500, which is nearly identical to the D4000 |
| `D4000_4500/Firmware/4000/R535.exe` | ★ Zip: `R535.HEX` (D4000 FLASH R535), `SL4HTK.EXE` (DOS softloader R3.07), `FLASH.BAT` | The HEX splits into 5 per-CPU images (see `scanner-facts.md`). Main target for disassembly: MP and IOC are 16-bit x86 |
| `D4000_4500/Firmware/4500/R813.exe` | Self-extracting zip: `R813.HEX` (4500 FLASH) | Same layout. Diffing against R535 may help |
| `D4000_4500/Field_Service_Tests_D4000_4500/` | ★ DOS FST v3.2 (`FST4000.EXE`, `FST4500.EXE`), `ASPI8DOS.SYS`, `ZD16.HEX`, `ZD32.HEX` | FST talks to the scanner over ASPI and has 48 tests. It **uploads a debug monitor (ZDebug) into the scanner** with MEMRD/MEMWR/IORD/IOWR commands. That could let us dump the EPROM code we don't have. The DOS binaries could run under DOSBox (no SCSI) or be disassembled |
| `D4000_4500/Howtek Utilities for Mac/HowtekStuff/` | ★ MacUtil 3.7 / 4.0 / 4.0.1 (68k, code in resource forks), ZDebug HEX files, `HSI.INI`, `R813.HEX` | MacUtil 4.x statically links Howtek's **HSI library** (`hsicd*` API) and a `HASPI` SCSI layer with a CDB name table. **`HSI.INI` has `[HASPI] CDB DUMP=` and `DEBUG`/`VERBOSE` flags that log to `HSIDEBUG.TXT`.** We can try enabling them on the G4 for a free software-side CDB log. MacUtil runs on the G4 |
| `D4000_4500/Howtek Utilities for Mac/HowtekStuff.zip` | Same content, with resource forks preserved in `__MACOSX/` | The portable copy of the Mac apps |
| `D4000_4500/MISC/` | Native-resolution table, aperture study, battery replacement (3.6 V lithium on the MB, BBRAM), sample scans | The BBRAM battery could be dead on old units: check it. The aperture study says 8000 ppi addressing works, which is interesting for custom software |

## Sibling scanners, lower priority (`reference/HOWTEK/`)

| Path | What | Notes |
|---|---|---|
| `7500/ScanMaster7500-ServiceGuide.pdf` | 198 pages, OCR'd | Different board set (MCP, IOC, IEC1/2, SCD) but the same firmware lineage. Its IOC is 8-bit SE, sync up to 10 MHz, and it has an RS-232 diagnostic port. Its power-on self-test list is useful |
| `7500/Firmware_R014/` | `R014.exe` (zip: `R014.BIN` 7500 flash, `README.TXT`), `Loading_Firmware.txt` (forum post: flashing the 7500 from Trident on a Mac, OS 9.2 G4), `Trident4.0r46Drum.hqx` (Aztek Trident 4 scanning app, Mac), `scsi22.sea.hqx` (**Howtek Mac SCSI driver 2.2**) | ★ Trident is a third-party app that drives Howteks, with the command usage embedded. The Howtek driver 2.2 is what MacUtil needs. BinHex: decode with `macbinary`/`binhex` tools |
| `8000/` | HR8000 FST and firmware updater (Win32 PE) | Probably packed/installer. Low priority |
| `HTSAI10.DLL` | **0 bytes**, a placeholder | Need a real copy if it matters (Howtek TWAIN/SAI?) |
| `aspi_471a2.exe` | Adaptec ASPI 4.71 (zip, includes `scsidefs.h`, `srb32.h`) | Generic. The headers are handy for decoding the DOS/Win tools |
| `MISC/` | Shipping instructions, drum checklist, community notes | Operational only |

## Standards (`reference/standards/`)

| Path | What | Notes |
|---|---|---|
| `SCSI-2_X3T9.2-375R_rev10L.pdf` | ★ SCSI-2 working draft X3T9.2/375R rev 10L (1993-09-07), the revision approved as ANSI X3.131-1994. Downloaded from t10.org (`ftp/x3t9.2/drafts/s2/s2-r10l.pdf`) | 502 pages. §5 covers the physical/electrical layer, §6 messages, §7 common commands, **§15 scanner devices** (the command set Phase 2 expects) |
| `SCSI-2_X3T9.2-375R_rev10L.txt` | The same draft as plain text (MIT SIPB mirror) | Easiest to grep. Section numbers match the PDF |

## Third-party projects (`reference/third-party/`)

| Path | What | Notes |
|---|---|---|
| `BlueSCSI-v2/` | Shallow clone of github.com/BlueSCSI/BlueSCSI-v2 @ `92db68f` (2026-08-22) | KiCad hardware (CERN-OHL-S v2) and RP2040/RP2350 firmware (GPL-3), including initiator mode and SDIO. Analysis: `3-driver/prior-art/bluescsi-v2.md` |
| `BlueSCSI-v2_Desktop_50_Pin_schematic.pdf`, `…_netlist.xml` | Exported with `kicad-cli` 9.0 | The quickest way to read the front end |

## Datasheets (`reference/datasheets/`)

Downloaded 2026-09-24. A text dump (PyMuPDF) greps well; regenerate it in a scratch directory
rather than storing it here.

| Path | What | Notes |
|---|---|---|
| `rp2350-datasheet.pdf` | RP2350 datasheet (1380 pp), datasheets.raspberrypi.com | §5.1 bootrom concepts (partitions, A/B, try-before-you-buy), §5.8 UART boot, §3.5.8 rescue reset, PIO GPIOBASE, GPIO function table |
| `hardware-design-with-rp2350.pdf` | Raspberry Pi "Hardware design with RP2350" (25 pp) | Reference schematic: crystal, core regulator, flash, USB |
| `DS_FT232H.pdf` | FTDI FT232H datasheet **v2.0** (FT_000288). Mirrored from github.com/standardsemiconductor/VELDT-info, because ftdichip.com blocks scripted downloads. FTDI's current version is 2.3 (`ftdichip.com/wp-content/uploads/2025/11/DS_FT232H.pdf`); fetch it in a browser if a detail matters | §3.5 per-mode pin tables, §4.5 async FIFO timing, §4.6 FT1248, §4.8 MPSSE, EEPROM (93LC56B; the 93LC46B won't work) |
| `AN_167_FT1248-Parallel-Serial-Interface-Basics.pdf` | FTDI AN_167 v1.1 (2018), FT1248 basics | SCLK ≤ 30 MHz, 30 MB/s at 8-bit; 1/2/4/8-bit waveforms; internal pull-ups on MIOSIO |

## Missing but useful (to acquire)

- The FT232H datasheet v2.3, fetched in a browser.

- The Windows Howtek HSI DLLs referenced by `HSI.INI` (`HCDD400.DLL`, `HCD4500.DLL`). Win32
  x86 decompiles far more easily than 68k.
- The D4000 User's Guide (P/N HTM092) and any Howtek SCSI programming reference.
- EPROM dumps for MP (U15), SSC (U10) and IOC (U29, U45). The boot and IOC low-level code may
  live partly in EPROM.
- The SilverFast Howtek plug-in, from the working G4 (its code shows the exact command usage).
