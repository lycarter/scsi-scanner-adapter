# Prior art: BlueSCSI v2 front end

What we learned from reading the BlueSCSI v2 hardware and initiator firmware, and what it
means for our board. Read on 2026-09-23 at upstream commit `92db68f` (2026-08-22).

- Upstream: https://github.com/BlueSCSI/BlueSCSI-v2
- Local copy (untracked): `reference/third-party/BlueSCSI-v2/`, plus a schematic PDF and a
  KiCad netlist of the Desktop 50-pin board, exported with `kicad-cli` 9.0, next to it.
- Board analysed: `hardware/Desktop_50_Pin` (IDC50, Pico module, microSD). The Centronics,
  DB25 and PowerBook BOMs use the same front-end parts.

## Licences: read before reusing anything

| Part | Licence | What it means for us (our repo is MIT) |
|---|---|---|
| `hardware/` | **CERN-OHL-S v2** (strongly reciprocal) | If we copy or adapt their schematic or layout, our board design must be released under CERN-OHL-S too. Learning from the ideas and redrawing our own circuit is fine |
| Firmware (initiator code comes from ZuluSCSI, © Rabbit Hole Computing) | **GPL-3.0-or-later** | If we copy firmware code, our firmware becomes GPL. Studying it is fine |

This is my reading of the licences, not legal advice.

## Front-end circuit (Desktop 50-pin)

Everything on the SCSI side runs from a **2.85 V rail** (AMS1117-2.85 fed from the board's
5 V), not from 3.3 V or 5 V. That's the same voltage as the terminator reference.

| Function | Parts | How it works |
|---|---|---|
| Data bus DB0–7 + P | 2× 74LVT245 (`U4`, `U9`), `/OE` tied low, `DIR` from one MCU pin | **Push-pull, whole bus at once.** When transmitting, all 9 lines are actively driven high or low. The driven "high" is 2.85 V, about the level the terminator idles at, so it mostly acts like releasing the line. 1 kΩ series resistors to the MCU |
| BSY, SEL out | 74LVT125 gates with data input and `/OE` tied to the same MCU pin | **True open-drain.** The pin going low enables the gate, which drives low; the pin going high puts the output in high-Z |
| REQ, I/O, C/D, MSG out | 74LVT125, `/OE` = `oBSY` | Push-pull, enabled only while the board holds BSY (target role) |
| ACK out | 74LVT125, `/OE` = `!oBSY` (inverted by a 74HC14), through a jumper (`J11`) | Push-pull, enabled only when *not* in the target role, i.e. initiator |
| Receivers | 74LVT125 gates, bus → MCU, with `/OE` from `oBSY`/`!oBSY` | Each MCU pin is shared between "drive signal X" and "read signal Y" through 1 kΩ resistors. Which one is active depends on the role (`oBSY`). MSG and ATN receivers share one pin (GP28); the RST receiver drives into the `oSEL` pin |
| **ATN out, RST out** | none | **Not wired.** `BlueSCSI_platform_gpio_v2.h`: `SCSI_OUT_ATN 29 // ATN output is unused`. SW1 (a push button) can pull RST |
| Termination | 2× 74LVT245 (`U5`, `U6`) with all inputs tied high, `/OE` = termination jumper, plus 2× AO3401A P-FETs, feeding 18× 110 Ω to the bus lines | **A switchable 110 Ω-to-2.85 V active terminator made from logic chips.** Enabled outputs sit at 2.85 V and source up to ~26 mA per asserted line. Disabled (or unpowered, thanks to the LVT's Ioff feature) they go high-Z |
| TERMPWR (pin 26) | Diode D1, polyfuse F3, jumper J7 (`TERM_BCKF`) | D1 lets the board be powered *from* TERMPWR (diode-OR with the floppy connector). Closing J7 sends board 5 V back out to TERMPWR through the fuse |
| microSD | SOFNG SD-001 (LCSC C428452), **4-bit SDIO** on GP10–15 via PIO | Card-detect is not wired |

LCSC numbers from their JLC BOM: LVT245 C2652121, LVT125 C7042, AMS1117-2.85 C14791,
AO3401A C15127, polyfuse C883111, 74HC14 C5605. Stock not yet checked by us.

### Terminator detail (from the netlist, 2026-09-24)

Two '245s give 16 channels, and the bus has 18 lines. The two P-FETs (`Q1`, `Q2`) are
channels 17 and 18: source on +2V8, drain to a 110 Ω resistor (R6, R35), gate on `TRM_ON_J`.
`TRM_ON_J` also drives both '245 `/OE`s. R41 pulls it up to +2V8 (so the terminator is off by
default) and jumper J1 grounds it to switch it on. `DIR` and all A inputs are tied to +2V8.

### Why the 9 data lines are split 4 + 5 across two '245s

The two data '245s (`U4`, `U9`) each use only some of their 8 channels (U4: channels 1, 3, 6, 8;
U9: 1, 3, 5, 6, 8). There's no designer comment explaining it. Our best guesses (inferred):
- **Routing.** Skipping pins makes room to run traces between 0.65 mm-pitch pads. The
  irregular pattern looks layout-driven.
- **Ground current.** A '245 has one GND pin. A line driven low can sink ~50 mA (the far
  terminator plus BlueSCSI's own). Eight lines at once is ~400 mA through one pin, plus
  ground bounce when they all switch together. TI's SN74LVTH245A datasheet gives 128 mA
  absolute max per output but no per-GND-pin figure.

The unused inputs are left floating. That's only OK because these are **LVTH** parts, which
have bus-hold ("LVTH (bus-hold) style *required*" is noted on their schematic).
Lesson for us: spread the high-current drivers across packages and count GND pins.

## Initiator mode: what it can and can't do

From `lib/BlueSCSI_platform_RP2MCU/scsiHostPhy.cpp`:

> "We can't write individual data bus bits, so use a bit modified arbitration scheme. We
> always yield to any other initiator on the bus."

It asserts BSY, checks that the data bus stays at zero for ~10 µs, then selects. That's
**not SCSI-2 arbitration**: it never puts its own ID bit on the bus and compares priorities.
It works when BlueSCSI is the only initiator. It can race if another initiator arbitrates
at the same moment.

## What this means for our board

1. **Keep:** 74LVT on a 2.85 V (or 3.3 V) rail; the "tie data to `/OE`" open-drain trick;
   the logic-chip switchable terminator; SDIO microSD over PIO; a diode + fuse + jumper on
   TERMPWR. All are proven on RP2040/RP2350 and are JLC parts.
2. **Change: every data bit must be individually open-drain.** We share the bus with the
   G4 (R4b), so we need real arbitration: put our ID bit on the bus, then read back the
   others. A push-pull '245 with one `DIR` pin can't do that. Use LVT125-style per-bit
   `/OE` drive (or equivalent) on DB0–7 + P.
3. **Change: wire ATN and RST outputs.** ATN is needed for selection with IDENTIFY, message
   out, sync negotiation and ABORT. RST is needed for bus recovery (R4b only says we must
   never assert it *unless told to*).
4. **Change: no role-multiplexed pins.** Sharing pins between roles saves GPIOs, but it
   ties signals together in hard-to-debug ways, and we need all 18 inputs readable at all
   times for listen-only mode (R4). BlueSCSI's own docs mention an RST/SEL interaction on
   one board revision because of pin sharing. That's why we're choosing the RP2350B.
5. **Our TERMPWR path needs a diode in the backfeed direction too.** A USB device must
   never drive VBUS, so another device's TERMPWR must not reach our USB 5 V.
6. Check the unpowered behaviour (Ioff) and output current limits of the LVT125/LVT245
   on the datasheets ourselves before copying the idea.
