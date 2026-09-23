# Phase 3: Driver PCB (USB-C ↔ SCSI initiator)

Goal: a board that plugs into a modern computer over USB-C and acts as the SCSI
**initiator** for the D4000. It also serves as the **bus snooper**. The separate snooper PCB
was dropped on 2026-09-23: the G4, the scanner and this board share one multi-initiator
chain (see `1-bus-capture/NOTES.md` for the topology).

## Requirements (draft)

- R1: **SCSI-2 narrow SE initiator.** Async is mandatory; sync (5–10 MB/s) is optional and
  only needed if the scanner negotiates it or async proves too slow. It handles selection,
  arbitration, message phases, disconnect/reselect, and parity generation and checking.
- R2: **SE electricals.** The drivers sink 48 mA, open-collector. The receivers have
  hysteresis. Active termination (switchable) is on board, and TERMPWR is supplied with a
  fuse and diode. It must be safe when unpowered (no backfeed, no bus clamping).
- R3: **Sustained throughput ≥ 1.5 MB/s** end to end, host to scanner, based on the estimate
  in `docs/scanner-facts.md`. Target 3–5 MB/s for margin. Phase 2 will measure the real number.
- R4: **Listen-only mode.** The receivers can monitor the bus without driving it, which makes
  the board a long-capture protocol sniffer for Phase 2.
- R4a: **Buffered LA header.** All 18 signals come out through Schmitt buffers
  (3.3 V CMOS), pinned to match the Digital Discovery's 2×16 input connector, plus marker
  pins driven by firmware (e.g. "CDB start", "error"). This replaces the old snooper board.
- R4b: **Multi-initiator friendly.** The SCSI ID is configurable (default 6). The board never
  asserts RST unless told to, tolerates another initiator's traffic, and its termination is
  switchable, so it works at the chain end or mid-chain.
- R5: **Host interface over USB-C** that needs no custom kernel drivers on macOS, Linux or
  Windows. That means vendor-class bulk with WinUSB/MS OS 2.0 descriptors, or CDC/NCM.
- R6: Firmware updates over USB without special hardware. SWD header for debugging.
- R7: Everything JLC-assemblable from LCSC stock where possible.

## Why USB speed is the deciding constraint

USB **full-speed** (12 Mbit/s) gives ~1.0–1.2 MB/s of real bulk throughput, which is **below**
our 1.3 MB/s estimate for 16-bit RGB at 4000 dpi. USB **high-speed** (480 Mbit/s) removes the
problem. Many popular MCUs, including the RP2040/RP2350 and most ESP32s, are full-speed only.
(Whether the scanner tolerates a slow host is still an open Phase-2 question. If it simply
pauses, full-speed would work but make big scans slower.)

## Decision: the "brains"

**Recommendation: an MCU, not an FPGA and not a Linux SBC. Specifically, an RP2350 as the
SCSI engine plus a high-speed USB path.**

### Can a Raspberry Pi Zero (2 W) do it?

Probably, yes: the PiSCSI/RaSCSI project drives SCSI from Pi GPIO through 74LS641
transceivers. But I'd not make it the SCSI engine:

- Linux scheduling jitter. Async SCSI is interlocked, so jitter only slows transfers rather
  than corrupting them. But selection timeouts, sync mode and sustained throughput all get
  harder.
- It boots from an SD card, takes tens of seconds to boot, and is a whole OS to maintain.
- It's not on LCSC and not JLC-assemblable. You'd hand-mount a module.

The good part: USB-gadget mode could make it a driverless "network scanner appliance",
and scanning software could run on the device. That's worth remembering as a Phase-4
architecture idea, not as the SCSI engine.

### Do we need an FPGA?

No. Narrow SCSI-2 at ≤10 MB/s is a few-MHz, 18-signal handshake. That is squarely what
PIO (RP2xxx) or FlexIO (i.MX RT) are designed for. An FPGA only earns its place for Wide/Ultra
SCSI or a custom high-rate logic analyzer, and we need neither.

### MCU options

| Option | SCSI side | USB | Pros | Cons |
|---|---|---|---|---|
| **RP2350 + FT232H** (recommended) | PIO state machines. There's prior art: the ZuluSCSI and BlueSCSI v2 open-source projects run SCSI (including an initiator mode) on RP2040/RP2350 | FT232H in FIFO mode: USB 2.0 HS, ~8 MB/s async FIFO | Well-trodden SCSI-on-PIO path you can study. Both chips on LCSC, QFN/LQFP, JLC-assemblable. RP2350 supports PSRAM for line buffering. Great for learning | Two chips. Host uses libftdi/D2XX (driverless on macOS/Linux; Windows auto-installs FTDI's driver) |
| RP2350 alone | PIO | Native full-speed only | Simplest, cheapest, one chip | ~1 MB/s ceiling (see above) |
| NXP i.MX RT1062 (e.g. a Teensy 4.1 module) | FlexIO or bit-bang at 600 MHz | Native HS with integrated PHY | One chip with HS. 1 MB SRAM, optional PSRAM on Teensy | BGA if designed in bare. The Teensy module isn't on LCSC. Less SCSI prior art |
| STM32 with integrated HS PHY (F723/F733, U5A5, H7R/S) | Bit-bang or timer/DMA | Native HS | One chip, LQFP, ST ecosystem, TinyUSB support | No PIO: cycle-exact handshakes are harder. Less SCSI prior art |
| WCH CH32V305/307 | Bit-bang | Native HS with PHY | Very cheap, LCSC-native | Younger ecosystem and docs. A tougher learning path |

**Open question**: this is a real fork. I lean RP2350 + FT232H for the SCSI prior art and
learnability. Teensy 4.1 is the strongest "one chip" alternative if you'd rather avoid the
FTDI. A neat variant is a small USB 2.0 hub chip (e.g. FE1.1s/CH334), so a single USB-C
cable carries both the FT232H (fast data) and the RP2350's own USB (console and firmware
update).

## SCSI electrical front end (candidates)

- The classic, proven choice: 74LS641-1 (open-collector, 48 mA sink) transceivers, as used by
  PiSCSI. It runs on 5 V and needs level care toward the 3.3 V MCU.
- Alternative: MOSFET/open-drain drivers plus Schmitt receivers (74LVC14 class). Study the
  ZuluSCSI and BlueSCSI schematics before choosing; check their licenses before reusing
  anything.
- Termination: switchable active terminator, same parts discussion as Phase 1.

## Open questions

1. RP2350 + FT232H vs. Teensy 4.1 vs. STM32 HS? Needs your preference, informed by Phase 2's
   throughput findings.
2. Connector: HD50 (compact, modern cables) vs. Centronics 50 (matches the scanner cable).
3. Enclosure / form factor?

## Log

- 2026-09-23: Initial requirements and brains analysis drafted.
- 2026-09-23: Absorbed the snooper role (R4a, R4b). There's no host switch; we rely on
  SCSI multi-initiator instead.
