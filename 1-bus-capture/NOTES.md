# Phase 1: Bus capture setup

**Scope change (2026-09-23):** there's no custom snooper PCB. The G4, the scanner and the
driver board share one multi-initiator SCSI chain. The Phase-3 driver board provides
"listen-only" capture and a buffered LA header. This phase now covers:

1. buying and setting up the logic analyzer (LA),
2. a cheap passive tap so we can capture SilverFast sessions **before** the driver board exists,
3. capture tooling: scripted capture plus a Python SCSI decoder.

## The bus we're tapping

Narrow single-ended (SE) SCSI on a 50-pin "A" cable. The odd pins are ground (pin 25 is open).
The signals are on the even pins:

| Pins | Signal |
|---|---|
| 2,4,…,16 | DB0–DB7 |
| 18 | DBP (parity) |
| 26 | TERMPWR (≈4.25–5.25 V terminator supply, not a logic signal) |
| 32, 36, 38, 40, 42, 44, 46, 48, 50 | ATN, BSY, ACK, RST, MSG, SEL, C/D, REQ, I/O |

That's 18 logic signals, all active-low and open-collector. Active termination pulls each
line to ~2.85 V through 110 Ω, and asserted means < 0.8 V. With the LA threshold at about
1.4–1.5 V, the LA can read the bus directly.

## Topology (multi-initiator)

```
G4 SCSI card (terminated, ID 7) ──cable── Scanner port 1 [ID 4]
                                          Scanner port 2 ──cable── [tap] ──── terminator
                          later:          Scanner port 2 ──cable── Driver board (terminated, ID 6)
```

The scanner has two connectors and no internal terminator, so it sits in the middle of the
chain. Exactly two terminators are on the bus, one at each end. The driver board's
terminator must be switchable so it can also sit mid-chain.

## Decision: LA purchase

Budget: up to ~$1k. Requirements: ≥ 24 channels (18 signals plus markers), ≥ 200 MS/s with
all of them, and **official** scriptable capture so an agent can run captures from the CLI.

**Recommendation: Digilent Digital Discovery (with its high-speed adapter), about $250–300.**
- It has 24 high-speed inputs plus 16 digital I/Os. Rates are 32 channels at 200 MS/s,
  16 at 400 and 8 at 800.
- The WaveForms SDK is official and documented for Python and C, so I can script captures
  from Bash.
- Its 16-channel pattern generator (1.2–3.3 V, 100 MS/s) could be useful later for exercising
  the driver board's receivers. That's unverified for this use.

Alternatives we rejected:
- **DSLogic U3Pro32** (~$400, 32 ch). The hardware is great value, but sigrok lists the U3Pro
  series only as "planned", and the CLI options are third-party wrappers.
- **Saleae Logic Pro 16** (~$1.5k). It has the best software, but 16 channels is too few
  (we'd lose RST and parity). It isn't worth going over budget for.
- **Kingst LA5032.** Its software is closed and can't be scripted.
- **Cheap FX2 clones.** Too slow, too few channels.

**Existing gear: Rigol DS1074Z (hacked to 100 MHz).** Digital channels need a "Plus"/MSO-ready
unit **and** the RPL1116 logic probe. A plain DS1074Z has no LA port. Even with the probe it's
only 16 channels, the same limitation as the Saleae. **Its real value here is analog.** We'll
use it for signal integrity on REQ/ACK (ringing, edge rates), termination voltages and
TERMPWR, and to check the driver board's 48 mA drivers. It can also be scripted over
SCPI (LAN/USB).

## Passive tap for early captures

We need no PCB to start: use a 50-pin IDC ribbon with an extra IDC connector crimped
mid-cable (or a 2×25 header adapter), plus LA flying leads, **grounds included** (use
several of the odd pins). Keep the leads short. If captures look glitchy, use the Rigol to
check the signals before blaming the protocol. A tiny buffered tap board (74LVC14-class
Schmitt inverters) is the fallback if the leads cause trouble.

Adapter cables still depend on the G4 card's connector (open question).

## Open questions

1. Which G4 SCSI card and connector? (Owner will check.)
2. Is the Rigol a "Plus"/MSO model, and do you have the RPL1116? (Check for the LA connector
   on the side panel.)

## Log

- 2026-09-23: Initial requirements and snooper-PCB analysis drafted.
- 2026-09-23: Owner approved merging the snooper into the driver board. LA budget ≤ $1k. The
  recommendation moved from DSLogic to the Digital Discovery after checking sigrok support.
