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

**Existing gear: Rigol DS1074Z (hacked; MSO options enabled).** The digital channels need the
~$200 RPL1116 probe, which the owner doesn't have, and it would only be 16 channels. **Its real value here is analog.** We'll
use it for signal integrity on REQ/ACK (ringing, edge rates), termination voltages and
TERMPWR, and to check the driver board's 48 mA drivers. It can also be scripted over
SCPI (LAN/USB).

## Decision: RP2350 (Pico 2) protocol sniffer first; the LA purchase is deferred (accepted)

The protocol is slow enough that a Pico 2 can log it at the **protocol level** rather than as
raw samples. We don't need a picture of every edge. We need a log of bus phases and bytes.

- One PIO state machine latches DB0–7 and DBP on each REQ/ACK handshake edge. Which edge
  depends on direction: I/O asserted = data-in, sampled at REQ; data-out, sampled at ACK.
  It pushes {byte, parity, phase lines} through DMA.
- A second state machine timestamps phase changes (BSY, SEL, C/D, MSG, I/O, ATN, RST).
- Bandwidth: commands, status and messages are tiny. Bulk image data (≤ ~1.5 MB/s) is more
  than full-speed USB can handle, so log counts plus the first N bytes and a checksum per data phase.
- **Self-checking:** every byte carries odd parity (DBP), and CDB length is implied by the
  opcode group. So the sniffer can flag its own mis-samples. A raw LA can't do that.
- Electrical: listen-only, never driving. Put buffers (74LVC14-class) or at least series
  resistors between the tap and the GPIOs. RP2350 inputs have Schmitt triggers and the bus
  idles at ~2.85 V, but don't rely on 5 V tolerance when the Pico is unpowered.
- Needs 18 GPIOs, contiguous per PIO `in` group. A Pico 2 has enough.
- Risks: a new tool can have its own bugs (parity checks mitigate this). Fast-sync timing
  margins at 150 MHz are unverified (overclocking helps). And it gives no edge-level timing;
  the Rigol's 4 analog channels at 1 GS/s can cover spot checks on REQ/ACK/BSY/DB0.
- **The work isn't wasted:** this is the Phase-3 board's listen-only mode, built early on a
  dev board.

## Passive tap for early captures

We need no PCB to start: use a 50-pin IDC ribbon with an extra IDC connector crimped
mid-cable (or a 2×25 header adapter), plus LA flying leads, **grounds included** (use
several of the odd pins). Keep the leads short. If captures look glitchy, use the Rigol to
check the signals before blaming the protocol. A tiny buffered tap board (74LVC14-class
Schmitt inverters) is the fallback if the leads cause trouble.

### Cabling plan (G4 card = Adaptec AHA-2930CU Mac)

The AHA-2930CU is a PCI **Ultra SCSI, narrow, single-ended** card with an **external HD50**
connector and an internal 50-pin IDC header. The card terminates itself when only one of its
connectors is used. It supplies TERMPWR.
- The chain: G4 card HD50 ─ HD50↔Centronics-50 cable ─ scanner port 1. The scanner's
  current external terminator on port 2 gets replaced by the tap assembly.
- **Tap assembly on scanner port 2:** Centronics-50 (male) to IDC-50 ribbon cable, an IDC
  tap connector crimped mid-ribbon for the LA leads, and an **IDC active terminator** at the
  ribbon's far end (the old internal-drive-chain style, powered from TERMPWR on pin 26).
  Keep the ribbon short, ≤ 0.5 m.
- Total bus length should stay **≤ 3 m**. That's the SE limit once sync above 5 MB/s is
  negotiated. The Adaptec can do Fast-20, but the scanner's WD33C93A will cap the negotiated
  rate; we'll see the actual SDTR in the captures.
- LA sample rate: at 10 MB/s sync, REQ/ACK pulses are ~30 ns. 200 MS/s (32 ch) gives 5 ns
  resolution, which is enough to decode. For edge-timing questions, drop to 8 channels at
  800 MS/s or use the Rigol.

Parts to buy: HD50↔CN50 cable (if you don't already use one), a CN50-male↔IDC-50 cable, a
50-pin IDC ribbon plus a spare IDC connector, and a 50-pin IDC active terminator.

## Open questions

1. Which cable connects the G4 to the scanner today, and where is the terminator?
   Photos would help.

## Log

- 2026-09-23: Initial requirements and snooper-PCB analysis drafted.
- 2026-09-23: Owner approved merging the snooper into the driver board. LA budget ≤ $1k. The
  recommendation moved from DSLogic to the Digital Discovery after checking sigrok support.
- 2026-09-23: Owner chose the **Digital Discovery**. G4 card is an Adaptec AHA-2930CU Mac. Cabling plan added.
- 2026-09-23: Owner asked about a Pico 2 sniffer as an LA stand-in. The option is written up above.
- 2026-09-23: Accepted. Start with a Pico 2 sniffer plus the Rigol. Buy the Digital Discovery at driver bring-up, or sooner if a capture confuses us.
