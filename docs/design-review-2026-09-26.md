# Design review, 2026-09-26

A full design check of the project so far, focused on Phase 3: RP2350 limits, USB, SCSI,
the bootstrapping and programming path, and the numbers against the datasheets. Phases 1, 2
and 4 are covered where they affect the board.

**Triage:** open `docs/design-review.html` in Chrome or Edge and load this file. Each finding gets
*Approve fix*, *Ignore* or a comment, written back here as `- **Owner decision:**` and
`- **Owner comment:**` lines at the end of the finding.

**Ground rules (from the owner):**
- Main topology: **driver board + scanner only**. The G4 with its Adaptec card is on the chain
  only during Phase 1/2 captures, so three-device cases are secondary.
- Accepted decisions are re-opened **only for real errors**, not for preference or cost.
- Trivial doc errors (typos, arithmetic slips) are fixed in place and logged as `[fixed]`.
  Design changes are only logged, never applied.

**Severity:**
- **Blocker:** the board won't work, or something gets damaged.
- **High:** likely needs a respin or a bodge.
- **Med:** spec margin or bring-up risk.
- **Low:** doc issue or nice-to-have.
- **Info:** checked and OK (logged so the check isn't repeated).

There's no schematic yet. The review checks `3-driver/NOTES.md`, `3-driver/blocks/`,
`3-driver/parts-list.md` and the other phase notes, against the datasheets in
`reference/datasheets/` and SCSI-2 rev 10L.

## Summary

Reviewed by one lead plus four parallel reviewers: SCSI front end, power, USB/bootstrap and RP2350/firmware. The raw log has 113 entries. **No Blockers.** One High, which is a single-part swap. Everything else is spec margin, schematic detail, firmware rules or docs. Duplicate entries from different reviewers are merged below; each `Rnnn` is a finding ID in the raw log.

### High

| # | Finding | Fix (suggested) | Log |
|---|---|---|---|
| H1 | **110 Ω terminator resistors (0402, 62.5 mW) run at 100–110 % of rating** on any asserted line; BSY stays asserted for a whole scan | 0603 100 mW, e.g. C2906985 | R006 |

### Med: hardware (settle before or during the schematic)

| # | Finding | Fix (suggested) | Log |
|---|---|---|---|
| M1 | **Bench present enables TERMPWR even when U1 is feeding the board from USB.** A USB port a little higher than the bench supply then carries TERMPWR, even a 500 mA Default port | Drive the enable node from LM66200 ST (open-drain, low while the bench supplies the board) instead of the bench-present FET | R068 |
| M2 | Bench eFuse **EN/UVLO pin passes its 6.5 V absolute maximum above 22.6 V in**; a 24 V adapter is a stated design case | Clamp EN with a ~5.1–5.6 V Zener | R057 |
| M3 | The bench **over-voltage trip (5.56–5.93 V) passes more than 5.5 V** to LM66200, the TPS73701s, FT232H VREGIN and TERMPWR (SCSI max 5.25 V) | Lower OVLO to ~5.5 V worst case, or accept it and document it | R061, R070 |
| M4 | **USB VBUS plug-in ringing can exceed the LM66200's 6 V absolute maximum**; the SMF6.0A only starts clamping at 6.67 V | Damp VBUS (a bulk electrolytic or RC snubber, within the 10 µF rule), or put an eFuse in the USB path | R074 |
| M5 | The TERMPWR eFuse **OVLO pin is driven to 3.3 V**; the recommended range is 0.5–1.5 V (absolute maximum 6.5 V, and TI's text allows GPIO drive) | Probably fine. Optionally clamp the node high level with a divider | R062 |
| M6 | **TERMPWR_OK can read high with TERMPWR absent**: the TCA9555 pull-up can be ~33 kΩ, not 100 kΩ | Lower the divider impedance, or add a pull-down on the node | R066 |
| M7 | **TERMPWR minimum on a 1.5 A USB port is ≈4.23–4.26 V** against SCSI-2's 4.25 V, and the eFuse's rising UVLO can reach 4.47 V | Measure at bring-up; lower the UVLO divider slightly; recommend the bench input for long scans | R069 |
| M8 | The **terminator rail (worst case 2.69 V) is below the SN74LVTH245A's 2.7 V minimum**, and its **output-high resistance is unspecified**, so the "100–132 Ω" and "≥ 2.5 V" claims aren't guaranteed | Centre the rail higher (~2.85 V still passes the 44.8 mA total rule); measure R_out at bring-up | R023, R025, R024 |
| M9 | **3.3 V rail margins**: VREG_AVDD/USB_OTP_VDD need ≥ 3.135 V; the CH334's low-voltage reset trips at up to 3.2 V; the rail's worst case is 3.16–3.44 V | Centre the rail at ~3.35–3.37 V (the CH334's maximum is 3.4 V); add 10 µF at the hub; measure under load | R078, R030 |
| M10 | **PSRAM CS1 pull-up (10 kΩ)** doesn't guarantee the APS6404L's VIH against the RP2350's reset pull-down (36 kΩ min) → 2.58 V vs 2.9 V | 3.3 kΩ (C25890, already on the BOM) | R079 |
| M11 | **FT232H power wiring**: VCCIO on the board 3.3 V rail while VREGIN = 5 V isn't an FTDI-documented configuration | Copy DS Fig. 6.2: VCCD (an output) feeds VCCIO/VPHY/VPLL/EEPROM | R016 |
| M12 | **FT232H support passives are missing**: REF 12 kΩ 1 %, TEST to GND, ferrites, decoupling, EEPROM resistors, RESET RC | Add them per DS Fig. 6.2 (values in the log) | R017 |
| M13 | FT232H outputs **can fight RP2350 outputs on the FT1248 lines** (blank EEPROM, wrong mode, a host bit-mode call) | 33–47 Ω series resistors; firmware checks the mode before driving | R021 |
| M14 | Bench-powered with the host off, the **CH334's D+ pull-up back-drives the cable** (no VBUS detect) | Hold the hub in reset when VBUS is absent (check that this removes the pull-up) | R032 |
| M15 | **Parts list isn't schematic-ready**: most support passives and rail capacitors are missing | Add a per-IC support-passives section | R003, R097 |

### Med: firmware and host (no hardware change)

| # | Finding | Log |
|---|---|---|
| F1 | **macOS: Apple's DriverKit FTDI driver claims 0403:6014**, so D2XX and libusb need root. Conflicts with R5 → owner decision (see Q1) | R052 |
| F2 | **Programming the FT232H EEPROM on macOS**: `ftdi_eeprom` can't set the FT1248 polarity, bit-order or flow-control bits and needs `eeprom_type=0x56` plus root. Suggest FT_PROG once on Windows, then `flash_raw` from the Mac | R044 |
| F3 | **PIO sketches**: `out pins, 9 [8]` won't assemble (max [7]); the setup time before ACK should be ≥ ~100 ns, not 55 ns; there's no phase-change check (a STATUS byte would be ACKed as data); release data in PIO after the last byte; REQ ringing can double-clock; ATN on the last MESSAGE OUT byte (put ATN on `out pins, 10`, since GPIO 27 sits next to DBP) | R007–R011, R100–R102 |
| F4 | **Hard real-time deadlines** (bus set 1.8 µs, bus clear or RST 800 ns, data release 400 ns) need SRAM-resident, top-priority code, ideally on a dedicated core | R014, R103 |
| F5 | **QMI sharing**: run from SRAM (`PICO_COPY_TO_RAM`), keep SCSI DMA in SRAM rings, never write flash during a bus session | R092 |
| F6 | **Sniffer**: can't follow 10 MB/s sync, produces 60–80 MB/s at the edge level, and its two FIFOs can desync → use Phase 1's protocol-level design for long captures | R012, R104 |
| F7 | **1-bit SDIO spill** is marginal at 25 MHz and can't write and drain at the same time; run it at 50 MHz and treat it as "extends the stall buffer" | R108 |

### Low (selection)

These are all in the raw log:
- **Connector:** IDC50 pin 25 / HD50 pin 13 must stay open; ground the RESERVED pins at the chain end (R002).
- **'245 terminator:** tie DIR and the A inputs explicitly (R039). Add a bleed load on the 2.80 V rail, ~1–3 mA (R042, R086).
- **Disabled terminator:** its bus-hold and ~9 pF load show up mid-chain only (R026, R027).
- **RP2350 caps:** the exposed pad is the only GND (R072); a second DVDD 4.7 µF is recommended (R081).
- **LDOs:** the 2.80 V divider impedance (R083); TPS73701 EN pins undefined (R084); LDO thermal tighter than stated (R085).
- **CC reference:** CJ431 is 2.500 V nominal and its margin shrinks to ~6–11 mV, still inside the window (R087). Keep capacitance off its cathode (R088).
- **CH334:** the RESET#/CDP pull-up may enable charging-port mode, so leave it floating (R031).
- **FIFO fallback:** pull SIWU# up (R022).
- **TERMPWR details:**
  - FLT goes low on reverse blocking; don't report that as a fault (R064).
  - Our sink current can exceed 1.0 mA (R065).
  - The TERMPWR_OK divider back-feeds into the unpowered 3.3 V rail (R067).
  - It can pulse on at power-up (R096).
- **Current limits:**
  - The bench eFuse's minimum limit can be exceeded when TERMPWR is at its limit (R095).
  - Power-budget rows are low: RP2350 core ~115 mA, microSD up to 200 mA (R093).
  - A 10 kΩ A-to-C cable reads as "3 A" (R090).
- **Firmware rules:**
  - Watchdog and fail-safe bus release (R004).
  - A "TERMPWR absent" rule (R049).
  - USB suspend current: document it as an accepted deviation (R005).
- **Phase 1:** the "≤ 3 m" claim and stubs from LA leads / Pico taps (R109, R110).
- **Doc slips:** listed at R051, R055 and R099. The trivial ones were fixed (R001, R056).

### Info (verified OK, don't recheck)

- **Pin map and PIO:** the RP2350B QFN-80 pin map, GPIO functions, PIO windows, and side-set/`wait` reach.
- **RP2350 errata:** the E9 mitigation (and E9 is fixed on A3/A4); the full errata sweep.
- **RP2350 support circuit:** core regulator, inductor, crystal, flash, BOOTSEL/RUN.
- **SCSI parts:** FDV301N V_OL, I_DSS, C_oss and C_rss; 74LVC1G17 thresholds at 3.3 V (≤ 1.90 / ≥ 0.93 V interpolated), I_OFF.
- **SCSI bus:** H5VUD5BB on the bus; parity, DB(P) and listen-only; edges and stubs.
- **eFuse settings:** both recompute correctly, apart from the Med items above.
- **Power ICs:** LM66200 ON/ST/soft start; TPS73701 feedback; CC front end and cable cases.
- **Supply ranges:** every 3.3 V part's V_DD maximum. The APS6404L is rated 2.7–3.6 V; LCSC's 2.7–3.3 V is wrong.
- **USB parts:** 93LC56B choice; ABM8 drive level; CH334 pinout and mode; RP2350 USB behind the hub.
- **FT232H:** the FT1248 ↔ FIFO rework map; it can't be bricked by bad EEPROM contents.
- **Bootstrap:** a blank board enumerates the hub, FT232H and RP2350 BOOTSEL with no firmware. UF2 family 0xE48BFF59.
- **Throughput:** the FT1248 4-bit master fits PIO1 at ~12 MB/s MCU-side. PIO, DMA and IRQ budgets fit.

### Bootstrapping verdict

Yes, everything can be programmed on a blank board.
1. On power-up the hub enumerates with no firmware.
2. The RP2350 comes up in ROM BOOTSEL (blank flash) through the hub, and takes UF2 or picotool. SWD via the TC2030 and J-Link is the fallback.
3. The FT232H enumerates with default descriptors and a blank EEPROM, and its EEPROM can be written over USB. Bad contents can't brick it.

The friction is on the host side, not the board: on macOS, Apple's FTDI driver (F1, F2) means root or a Windows machine for the first EEPROM write. On the board side, keep the RP2350 off the FT1248 lines until the FT232H is known to be in FT1248 mode (M13).

### Questions for the second review pass

1. **R5 / macOS (F1):** which path should the host tool use on macOS?
   - root;
   - Apple's `/dev/cu.usbserial` node as the data pipe (needs a bench test);
   - a custom PID (which loses the automatic Windows Update driver).

   Should R5 be reworded to "FTDI's own driver on Windows is OK"?
2. **RP2350 stepping:** which one does JLC fit (A2 vs A3/A4)? It decides whether E9, E10 (UF2 drag-and-drop after a partition table) and E14 apply. `picotool info -a` shows it at bring-up; asking JLC before the order is better.
3. **Sniffer scope:** must the on-board sniffer trace *sync* DATA phases, or is the logic analyzer the tool for those? This decides whether F6 is a firmware item or a non-goal.
4. **Bench OVLO (M3):** lower it so nothing sees more than 5.5 V (tighter margin to a 5.5 V bench setting), or keep 5.73 V and document "set the bench to 5.0–5.3 V"?
5. **Windows machine:** do you have one for FT_PROG (F2)? If not, we plan the macOS `ftdi_eeprom` route with a hand-built image.


### Pre-KiCad resolutions (2026-09-26, from the owner's triage)

The owner triaged every finding in `design-review.html`; the per-finding decisions are in the raw log.
The answers to the follow-up questions, and the resolutions that follow from the notes:

- **R068 (bench role):** the bench must *take over* when it's connected, not just add to USB. The
  LM66200 picks whichever input is higher, so it can't do that. **Replace U1 with a TI TPS2116DRLR
  (C3235557, SOT-583, the same package, extended, $0.40)** in priority mode:
  - VIN1 = bench eFuse output, VIN2 = USB VBUS, MODE tied to VIN1, PR1 divider from VIN1 set
    below the bench eFuse UVLO (datasheet SLVSFG1A §7.6 truth table: PR1 > VREF → VIN1, whatever VIN2 is).
  - The bench eFuse output is either 0 V or ≥ 4.05 V, so "bench present" = "bench in use", and the
    existing bench-present 2N7002 stays the right TERMPWR enable.
  - ST (open-drain, low when VIN1 isn't in use) → expander PWR_SRC.
  - Still one ideal-diode part type (the LM66200 leaves the BOM).
  - Abs max is still 6 V, so the approved R074 VBUS damping stays. There's no mux current limit;
    the bench eFuse limits the bench side.
  - Check at schematic time: the VREF/PR1 tolerance, and the output dip on switchover when the
    bench is removed (§7.5), against the +5V_SYS bulk capacitance.
- **R078 vs R030 (3.3 V setpoint):** keep **3.30 V (47 k / 27 k)**, plus a **DNP 0603 in parallel with
  R2** for rework trim. Raising it to 3.37 V would overshoot the CH334's 3.4 V maximum. Measure at bring-up.
- **R006 (terminator resistors):** each 110 Ω becomes **2 × 220 Ω 0402 in parallel (C25091, basic,
  62.5 mW)**. That's ≤ 35 mW (55 %) each, and it drops the extended 110 Ω part (one fewer loading fee).
- **R066 / R069 (TERMPWR sensing):** **GPIO 46 (ADC6) reads TERMPWR through a divider**. The digital
  TERMPWR_OK input (expander P05) and its 22 k/33 k divider are dropped, which also removes the
  R067 back-feed. GPIO 46 loses its two DNP links: expander INT (firmware polls) and SIWU# in the
  FIFO fallback (SIWU# is tied high instead, R022). Keep TERMPWR UVLO as it is; firmware warns
  from the ADC reading.
- **R111 (bench test):** an FT232H breakout + Pico 2 W test of FT1248 and the macOS
  `/dev/cu.usbserial` path runs **in parallel with the KiCad schematic, and must finish before
  the JLC order**.
- **R034 / R111:** plan for **A4 silicon**, and stay safe on A2 (keep the E9 pull-downs and the
  E14 notes).
- **R013:** the protocol-mode sniffer must also trace DATA phases (per-handshake records).
- **Still undecided, no schematic impact:** R102, R105, R113 (firmware notes), R109, R110 (Phase 1 docs).

**Applied (2026-09-26).** All approved fixes are now in `3-driver/NOTES.md` (sections updated in
place, a new "Power mux" section, and "Firmware rules from the design review" after the PIO
sketch), `3-driver/parts-list.md` (rewritten), the block pages and diagram sources (rebuilt),
`3-driver/USAGE.md` (power, first programming, bring-up checks), `docs/decisions.md` and
`4-software/NOTES.md`. Values chosen while applying them (all from JLC's no-fee range):
bench string 510 k / (39 k + 3.9 k) / (150 k + 10 k), OVLO 5.35 V (5.14–5.59 V); terminator
divider (39 k + 5.6 k) / 33 k = 2.831 V; OVLO divider 56 k / 47 k; LDO EN 100 k / 75 k; PR1
100 k / 39 k; ADC divider 100 k / 100 k; CJ431 bias 470 Ω (430 Ω isn't no-fee); bench ILIM 1.5 k
(2.22 A).

**Questions for the second review pass (raised while applying the fixes):**
1. **R059 vs R061 conflict.** Scaling the bench eFuse string to ≥ 1.5 MΩ (< 10 µA reverse
   current, as approved) makes the pins' ±0.1 µA leakage move the OVLO trip by ±0.16 V, so
   the trip spreads to ~5.0–5.7 V, which breaks R061. I kept 510 k (~28 µA at −15 V; meets
   TI's ≥ 350 kΩ footnote, and the new EN Zener takes most of it forward-biased) and
   prioritised over-voltage accuracy. OK, or do you want a different trade?
   **Owner (2026-09-26): OK.**
2. **EN Zener leakage.** The BZT52C5V6's datasheet only bounds leakage at 2 V (≤ 1 µA). At our
   1.42 V it's typically nA, but 1 µA through 510 kΩ would raise UVLO by up to 0.5 V. Bring-up
   measures UVLO; is a datasheet-guaranteed clamp worth a different part?
   **Owner: no; far from anything we care about. If it's a problem, bodge in a different part.**
3. **Power ceiling.** With the corrected RP2350 (115 mA) and SD (200 mA, unverified) maxima, the
   every-maximum ceiling is 1.55 A against a 1.5 A USB port (realistic worst ~1.3 A), and a
   TERMPWR overload plus maximum logic (~2.05 A) can touch the bench eFuse's minimum limit
   (2.0 A). Both are accepted in NOTES; flag if you disagree.
   **Owner: accepted.**

## Raw log (in the order found)

Format: `### Rnnn [Severity] Area: title`, then evidence (with citations), impact, and a
suggested fix.

### R001 [Low] Docs: stale values fixed in place `[fixed]`
- **Evidence:** leftovers from superseded decisions:
  - NOTES R2a still said "resettable fuse".
  - The FDV301N circuit sketch showed a 10 kΩ gate pull-down; it's 4.7 kΩ since 2026-09-25 (E9).
  - The terminator `/OE` sketch and the TERM_EN limitation said 2.85 V; the rail is 2.80 V.
  - Open question 4 still named LM66200 U2 as the TERMPWR part.
  - The power budget still had a "TERMPWR polyfuse" requirement.
  - The FT232H section said AN_167 was "not yet downloaded".
  - `blocks/1-power.md` said "2.85 V regulator" and listed the TERM_EN default and resistor values as open. Both are decided.
  - `USAGE.md` called the expander "optional", but it's fitted as standard.
- **Fix:** edited in place (NOTES, `blocks/1-power.md`, `USAGE.md`). Historical log lines and superseded rationale sections were left as history.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R002 [Low] SCSI connector: RESERVED and OPEN pins need explicit handling in the schematic
- **Evidence:** SCSI-2 rev 10L Table 2 (SE, A cable):
  - IDC50 (set 1) pin 25 / HD50 (set 2) pin 13 is **OPEN**, not ground.
  - Pins 24 and 28 (HD50 37 and 39) are **RESERVED**.
  - Several even pins are **GROUND**, not signals: 20, 22, 30, 34 (HD50 35, 36, 40, 42).
  - §5.4.4: RESERVED lines "shall be connected to ground in the bus terminator assemblies or in the end devices", and "should be open in the other SCSI devices".
- **Impact:** NOTES describes the pinout as "odd pins ground, even pins signal", which is almost right. If pin 25 is grounded with the rest of the odd pins, a reversed cable (possible on the HD50 side only through a bad cable) shorts TERMPWR to ground. The eFuse survives that, but the bus is dead. The RESERVED lines should be grounded when our board is an end device, which is the main topology.
- **Fix:** in the schematic, leave IDC50 pin 25 and HD50 pin 13 unconnected. Tie the RESERVED pins to GND through a 0 Ω link each (fit for end-of-chain, remove if the board ever sits mid-chain), or simply ground them. Wire both connectors from Table 2 by signal name, as NOTES already says.
- **Confidence:** high (read directly from the standard).
- **Owner decision:** approved (2026-09-26)

### R003 [Med] Parts list: not yet "schematic-ready"; many support passives are missing
- **Evidence:** `parts-list.md` calls itself "schematic-ready", but it has no rows for:
  - FT232H: REF resistor, per-pin decoupling, any VPHY/VPLL filtering, EEPROM pull-ups.
  - CH334P: VDD33/V5 decoupling.
  - TPS73701 ×2: input and output capacitors. The datasheet has minimum C_OUT and ESR guidance.
  - TPS259470A ×2: IN/OUT capacitors.
  - Bulk capacitance on +5V_SYS, TERMPWR and the 2.80 V rail.
  - Decoupling for the TCA9555, LM393, 3 × LVTH245 and W25Q128 (the MCU table has "+ flash"; check it's counted once).
  - microSD: decoupling and bulk (card insertion inrush).
  - USB-C shell/shield connection.
  - Test points.
  Some of these are covered in the agents' sections below (FT232H, LDOs).
- **Impact:** the schematic step turns into more part selection. A missed REF resistor or LDO output cap stops the board working.
- **Fix:** at schematic time, add a "support passives" section per IC, checked against each datasheet's typical application. Prefer basic 100 nF/1 µF/4.7 µF/10 µF parts that are already on the list.
- **Confidence:** high that the rows are missing; the exact values are in the per-area findings.
- **Owner decision:** approved (2026-09-26)

### R004 [Low] Error states: firmware must fail safe on the bus (watchdog)
- **Evidence:** ATN, BSY and SEL are driven by the CPU (SIO), and data/ACK by PIO. A firmware hang (hard fault, deadlock, a stall on flash erase) with BSY or data gates asserted holds the SCSI bus busy until the board resets. The scanner would then time out or wait for ever. After a watchdog reset or a RUN reset, all pads return to their reset state (pull-down, isolated), and the 4.7 kΩ gate pull-downs release every line.
- **Impact:** a hung board wedges the scanner mid-command, which may need a scanner power-cycle.
- **Fix (firmware):** enable the RP2350 watchdog in the SCSI engine, and have the host protocol expose a "bus reset" command (assert RST ≥ 25 µs, SCSI-2 reset hold time) for recovery. Hard-fault handler: release all 14 gates first.
- **Confidence:** high (design logic).
- **Owner decision:** approved (2026-09-26)

### R005 [Low] Error states: USB suspend current
- **Evidence:** USB 2.0 §7.2.3 limits a suspended device to 2.5 mA. This board draws ~0.2 A of logic current (NOTES power budget) and keeps TERMPWR up in suspend. This is the same class of deviation as the accepted "100 mA before configuration" one.
- **Impact:** in practice, hosts don't police it. A laptop going to sleep with the board attached keeps powering it (or cuts VBUS). The scanner session is lost either way.
- **Fix:** document it as an accepted deviation next to the 100 mA one. Optionally, firmware can gate LEDs and the SD card in suspend. No hardware change.
- **Confidence:** high on the rule; the impact is benign.
- **Owner decision:** approved (2026-09-26)

### R006 [High] SCSI: 110 Ω terminator resistors in 0402 run at or above their 62.5 mW rating
- **Evidence:** parts-list row "18 × 110 Ω 1 % 0402 (FOJAN)", C2909312 = FRC0402F1100TS, **62.5 mW** (pcbparts/JLC record). An asserted line puts (V_term − V_OL) across the resistor: nominal (2.81 − 0.18 V [FDV301N 3.8 Ω typ × 48 mA]) → 2.63²/110 = **63 mW**; worst (2.93 V LDO max − 0.18) → 2.75²/108.9 = **69 mW** (110 %). BSY is held asserted for a whole connection (a scan lasts minutes), RST for ≥ 25 µs, and a data line can sit asserted indefinitely between bytes. Thick-film 0402 ratings are also derated above ~70 °C.
- **Impact:** resistors run at 100–110 % of rating continuously on the busy lines; drift/early failure, and the resistor tolerance that the 22.4 mA budget depends on is no longer guaranteed.
- **Fix:** use 0603 (100 mW): e.g. FOJAN FRC0603F1100TS **C2906985** (143k stock, extended, same loading-fee count as the 0402) or UNI-ROYAL C22781. Update parts-list and NOTES.
- **Confidence:** high (arithmetic + part record). Real V_OL varies, but the nominal case alone is at the rating.
- **Owner comment:** Rather than use an extended part, use basic parts in parallel to spread the power around and keep each individual component under its limits.

### R007 [Med] SCSI: PIO data_out `out pins, 9 [8]` does not assemble with `.side_set 1 opt`
- **Evidence:** the PIO delay/side-set field is 5 bits. `.side_set 1 opt` uses 1 side-set bit + 1 enable bit, leaving 3 bits of delay, so the maximum is **[7]** (RP2350 datasheet §11.4 "Delay/side-set" field; same as RP2040). NOTES "PIO0 sketch" uses `[8]`.
- **Impact:** pioasm error. If "fixed" by just trimming to [7], the data→ACK setup drops to 8 cycles = 53 ns at 150 MHz, under the 55 ns (deskew 45 + cable skew 10) target (see next finding).
- **Fix:** either use non-optional `.side_set 1` (4 delay bits, max [15]) and put `side 0/1` on every instruction, or add a `nop [n]`, or run the SM at a clock divider. Choose the delay after reading the rising-edge finding below.
- **Confidence:** high.
- **Owner comment:** approved. I think the `nop [n]` makes the most sense to me, but we can figure it out in firmware later.

### R008 [Med] SCSI: data_out deskew margin ignores slow release edges and FET turn-off delay; make it ≥ ~100 ns
- **Evidence:** SCSI-2 Table 7 (§5.7): **deskew delay = 45 ns** (not 55 ns: 55 ns is deskew + cable skew 10 ns). §6.1.5.1 async DATA OUT: drive DB, wait ≥ deskew + cable skew (55 ns), then assert ACK, measured at our connector (§5.7). The sketch gives 9 cycles = 60 ns from `out` to the ACK side-set, all of it inside the chip. On the wire, ACK assertion is a FET **turn-on** (t_d(on) typ 3.2 ns, t_r 6 ns; FDV301N DS switching table, at 4.5 V / 50 Ω), while a data bit going 1→0 is a FET **turn-off**: the gate (≈15 pF C_iss at low V_DS, Fig. 8) must discharge from ~3.2 V through 100 Ω + pad (~150 Ω) past the Miller plateau (≈2.1 V, Fig. 7; Q_gd 0.07 nC ≈ 5 ns at ~14 mA), then the line rises through the terminators and the cable (incident step to ~2.4–2.6 V at our end, plus lumped C ≈ 18 pF × ~50 Ω). Estimate ≈ 15–25 ns for a released bit vs ≈ 5–10 ns for ACK: ~10–15 ns of the 60 ns is eaten, leaving ~45–50 ns (< 55 ns). Unverified estimate; no bench data.
- **Impact:** marginal setup on the target side during DATA OUT / COMMAND / MESSAGE OUT; a WD33C93A usually samples later, so it will probably work, but it isn't compliant by design.
- **Fix:** delay ≥ 15 cycles (100 ns) between `out` and the ACK assertion. Async throughput cost is negligible (the scanner is the bottleneck). Verify on the scope: DBx release crossing 2.0 V vs ACK crossing 0.8 V at the connector.
- **Confidence:** med (timing estimate from typical figures).
- **Owner decision:** approved (2026-09-26)

### R009 [Med] SCSI: data_out leaves the last byte on the bus; release it in PIO, not firmware (400 ns data release delay)
- **Evidence:** SCSI-2 §6.1.10(b): when the target turns the bus around (I/O false→true, e.g. COMMAND → DATA IN/STATUS), "the initiator shall release the DATA BUS no later than a data release delay [400 ns, Table 7] after the transition of the I/O signal to true." The data_out sketch loops back to `pull block side 0`, so after the last byte DB0–7/P stay driven until firmware notices. NOTES says "Firmware must release all 9 data gates within the 400 ns". A Cortex-M33 IRQ (12-cycle entry ≈ 80 ns) can do it only if the ISR and its data are in SRAM, nothing higher-priority is running, and no XIP cache miss happens (a miss on QSPI flash/PSRAM costs ~0.5–1 µs).
- **Impact:** a bus fight with the target's first DATA IN / STATUS byte (target starts driving ≥ 800 ns after I/O; our open-drain drivers pull its 1-bits low → wrong status/data/parity errors). Open-drain means no damage, only corruption.
- **Fix:** §6.1.5.1 allows the initiator to "change or release the DB signals" once REQ is false. Add `mov pins, null` (release all 9) with ACK negation after `wait 0 pin 16`, so the bus is always released between bytes. Costs one instruction; removes the firmware deadline completely.
- **Confidence:** high on the rule; med on how hard the firmware deadline would be.
- **Owner decision:** approved (2026-09-26)

### R010 [Med] SCSI: last MESSAGE OUT byte: ATN (CPU-owned) can't be negated in the REQ-true/ACK-false window
- **Evidence:** SCSI-2 §6.2.1: the initiator "shall not negate the ATN signal while the ACK signal is asserted during a MESSAGE OUT phase. Normally, the initiator negates the ATN signal while the REQ signal is true and the ACK signal is false during the last REQ/ACK handshake." With the data_out SM, that window is only the ~60–100 ns between REQ detection and ACK assertion. NOTES "Who drives what" gives ATN to the CPU (SIO).
- **Impact:** firmware can't hit the window; negating ATN earlier (before the last REQ) is allowed by the letter but some targets then leave MESSAGE OUT early (vendor behaviour, the WD33C93A's is unknown); negating later (after ACK negated) is legal only if ACK is false, but then the target may request another message byte. Multi-byte messages (IDENTIFY + SDTR/EXTENDED, ABORT sequences) are where this bites.
- **Fix (firmware/PIO only, no hardware change):** ATN is GPIO 27, right after DBP (GPIO 26), so `OUT_BASE = 18`, `out pins, 10` can carry ATN as bit 9 of each FIFO word: firmware queues the last message byte with ATN = 0 and PIO drops it at the right moment. That means ATN's funcsel is PIO0 during MESSAGE OUT (or always). Alternatively do MESSAGE OUT byte-by-byte from the CPU (slow but only a few bytes).
- **Confidence:** high on the rule; the ATN bit-9 trick relies on the accepted pin map (verified: outputs 18–26 data, 27 ATN).
- **Owner decision:** approved (2026-09-26)

### R011 [Med] SCSI: data_in / data_out can double-clock on REQ ringing; add a minimum ACK-assert time before `wait 0 pin 16`
- **Evidence:** data_in: `in pins, 9 side 1` then immediately `wait 0 pin 16`. data_out: `wait 0 pin 16 side 1` right after asserting ACK. The PIO input path has a 2-flop synchronizer (≈13 ns at 150 MHz). REQ's assertion is a fast falling edge from the target's open-collector/three-state driver into a ribbon; ringback above the receiver's VT+ (≤ ~1.9 V, 74LVC1G17 Table 8, interpolated) for even one sample is enough to satisfy `wait 0` and release ACK, and the next `wait 1` then re-samples the same byte. The 1G17 hysteresis (≥ 0.31 V at 3.0 V, 0.25 V at 125 °C; Table 8) helps but doesn't bound ringing amplitude. This is the classic SCSI "double REQ" failure.
- **Impact:** duplicated or dropped bytes in DATA IN, silently corrupt scan data (no parity error, because the byte itself is valid).
- **Fix:** hold ACK asserted for a minimum time (e.g. `[7]`/`nop [n]` ≈ 50–100 ns) before looking for REQ negation, and/or require REQ negated for 2 consecutive samples (`wait 0 pin 16` followed by `jmp pin` re-check). Costs 1–2 slots, negligible throughput. Also scope REQ at the connector at bring-up.
- **Confidence:** med (depends on real ringing; cheap to guard).
- **Owner decision:** approved (2026-09-26)

### R012 [Med] SCSI: the sniff loop can't follow 10 MB/s fast-sync (and is marginal at 5 MB/s)
- **Evidence:** sniff = 3-instruction poll (20 ns at 150 MHz) + 4-instruction emit (mov y / mov isr / push / irq) → after each change the SM is blind for ≈ 7 cycles ≈ **47 ns**. SCSI-2 §5.8 / Table 7 fast sync: transfer period ≥ 100 ns, fast assertion/negation ≥ 30 ns, fast hold 10 ns, fast deskew 20 ns. So in each 100 ns period there are ≥ 3 distinct bus states ~10–30 ns apart (data change, REQ assert, REQ negate; plus ACK pulses offset by up to the REQ/ACK offset). Edges closer than ~47 ns after an event are merged or missed, and any state shorter than 20 ns can be missed outright. At 5 MB/s sync (200 ns period, 90 ns assertion/negation) it mostly works but data changes within 45 ns of REQ (hold time 45 ns) can still merge. Also: the two SMs (sniff + stamp) push to separate FIFOs with `push noblock`; if one FIFO overflows and the other doesn't, samples and stamps silently desynchronize. scanner-facts: the D4000's WD33C93A supports sync, rate unknown; the sibling 7500 uses up to 10 MHz.
- **Impact:** listen-only captures of the G4/Adaptec session will be wrong exactly in the DATA IN phase, if it negotiates fast sync.
- **Fix:** keep the Digital Discovery as the reference for sync phases; or make the sniffer loop 2 instructions with the timestamp embedded (e.g. count loop iterations in the same SM and push `{state, delta}` together, one FIFO, one DMA); or detect SDTR in the capture and flag data phases as "sync, not traced". Log the negotiated SDTR from the MESSAGE phases, which the sniffer does catch (async).
- **Confidence:** high on the arithmetic; whether it matters depends on what the Adaptec negotiates (Phase 1 will show).
- **Owner decision:** approved (2026-09-26)

### R013 [Question] SCSI: is the on-board sniffer required to trace sync DATA phases, or is the LA the tool for that?
- **Evidence:** see previous finding. R4 (listen-only) doesn't say which transfer modes it must cover.
- **Impact:** decides whether the sniff program needs redesign now or can stay "async only".
- **Fix:** owner to decide; I'd write "async + messages; sync data via the LA" into R4.
- **Confidence:** —
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** in protocol mode it should also trace DATA

### R014 [Med] SCSI: CPU-side hard deadlines (bus set 1.8 µs, bus clear 800 ns, RST response 800 ns) need SRAM-resident, IRQ-masked code; write it down as a firmware rule
- **Evidence (SCSI-2 Table 7, §5.7):** arbitration delay ≥ 2.4 µs; bus free delay ≥ 800 ns; **bus set delay ≤ 1.8 µs** (assert BSY + ID after detecting BUS FREE); bus settle 400 ns (BUS FREE = BSY and SEL false for ≥ 400 ns, §6.1.1); **bus clear delay ≤ 800 ns** after BUS FREE detected / SEL seen during arbitration / RST true (and ≤ 1200 ns from BSY+SEL false, §5.7.3); data release 400 ns; reset hold ≥ 25 µs; selection abort ≤ 200 µs; selection time-out 250 ms (recommended); deskew 45 ns; cable skew 10 ns; hold 45 ns; assertion/negation (sync) ≥ 90 ns. So arbitration has a window of [800 ns, 1.8 µs] after BUS FREE detection, and the losing/reset paths have an 800 ns ceiling. BSY, SEL, ATN, RST are on SIO (CPU).
- **Impact:** a flash XIP cache miss (QSPI at ~≤ 75 MHz: tens of cycles per line, ~0.5–1 µs worst with PSRAM contention on the same QMI) or a USB/FT1248/DMA IRQ preempting the arbitration loop can blow the 1.8 µs / 800 ns limits. In the main topology (only us + scanner) arbitration loss only happens if the D4000 reselects (it disconnects? unknown); RST is only asserted by us. In the G4 capture topology we're listen-only. So the practical risk is low, but the requirement should be explicit.
- **Fix (firmware rule, NOTES):** arbitration/selection/bus-free/RST handlers `__not_in_flash` (SRAM), run with interrupts masked (or at the highest NVIC priority on the core that owns SCSI, with USB on the other core), no PSRAM access inside. For RST-true and SEL-during-arbitration, consider a small PIO watcher: `wait 1 pin RST` → `irq` so the CPU is told within ~13 ns, and let the data_out SM release its own pins (`mov pins, null`) on that IRQ. Also filter RST glitches per §6.2.2 NOTE 30 (e.g. ≥ 2 samples).
- **Confidence:** high on the numbers; latency figures for XIP misses are typical, not measured.
- **Owner decision:** approved (2026-09-26)

### R015 [Info] SCSI: PIO data_in handshake order and REQ index checked
- **Evidence:** `wait 1 pin 16` (REQ, IN_BASE 0, GPIO 16 per the pin map) → `in pins, 9` (DB0–7, DBP on GPIO 0–8) with ACK asserted on the same cycle → `wait 0 pin 16` → ACK negated at the top of the loop. Matches §6.1.5.1 (read after REQ true, then ACK; negate ACK after REQ false). Target provides deskew before REQ, so sampling ~13 ns (sync) + ≤ 5.5 ns receiver skew (1G17 tpd 0.7–5.5 ns, Table 9) after REQ is fine. INOVER-invert gives 1 = asserted for both data and REQ. Side-set ACK = GPIO 29 is inside PIO0's window. `.side_set 1 opt` delay limit (≤ 7) is only an issue in data_out.
- **Confidence:** high.

### R016 [Med] USB: FT232H VCCIO on the board 3.3 V rail while VREGIN = 5 V is not an FTDI-documented configuration; follow the datasheet (VCCD feeds VCCIO/VPHY/VPLL/EEPROM)
- **Evidence:** DS_FT232H v2.0 Table 3.1 and §6.1/§6.2 (pp. 10, 43–44): with VREGIN = 5 V, pin 39 **VCCD becomes an output** and "supplies 3.3V to the VCCIOs, VPLL and VPHY". Both 5 V examples (Fig. 6.1 bus-powered, Fig. 6.2 self-powered) tie VCCIO (12, 24, 46), VPHY (3) and VPLL (8) to the VCCD net, and power the 93LC56B from VCCIO. §7.1 (p. 47): the EEPROM must be "powered from the same net as the core supply". Only Fig. 6.3 (VREGIN = 3.3 V) feeds VCCIO from an external 3.3 V LDO, and then VCCD is an *input*. NOTES "Supply choices" says "VCCIO stays on the 3.3 V rail … Check the VPHY/VPLL wiring … at schematic time."
- **Impact:** the planned mix (VREGIN = 5 V, VCCIO from the board LDO) isn't shown anywhere by FTDI. The real danger is at schematic time: if VCCD (an LDO *output* in this mode) gets tied to the board 3.3 V net, two regulators fight. If VCCIO is on the board rail but VPHY/VPLL/EEPROM on VCCD, the I/O ring and the core-side 3.3 V come from different sources with unspecified sequencing.
- **Fix (suggestion):** copy Fig. 6.2 exactly: VREGIN = +5V_SYS (4.7 µF + 0.1 µF); VCCD = local "FT_3V3" net (4.7 µF + 0.1 µF), which feeds VCCIO ×3 (0.1 µF each), VPHY and VPLL each through a 600 Ω@100 MHz / 0.5 A ferrite + 0.1 µF (4.7 µF pads DNP), and the 93LC56B VCC. **Never connect VCCD to the board 3.3 V.** The FT232H's I/O is then at its own 3.3 V, which talks to the RP2350's 3.3 V fine (same 5 V source, so no sequencing problem; FT232H inputs are 5 V tolerant). The FT232H's ~70 mA then comes off 5 V instead of the board LDO, a slight power-budget improvement.
- **Confidence:** high on what the datasheet shows; medium that the external-VCCIO mix would actually misbehave (not stated as forbidden, just never shown).
- **Owner decision:** approved (2026-09-26)

### R017 [Med] USB: FT232H support passives (values to add to the parts list, per DS Fig. 6.2)
- **Evidence:** DS_FT232H v2.0 Table 3.2 (p. 10): **REF = 12 kΩ 1 % to GND** ("Current reference"), **TEST (pin 42) must be connected to GND**. Fig. 6.2 (p. 44): RESET# = 10 kΩ to 3.3 V + **10 nF to GND**; VCCA (37) and VCORE (38) = 0.1 µF each, "Should not be used" (DS Table 3.1); crystal caps; EEPROM: DO → **2.2 kΩ** (text) / 2 kΩ (figure) → DI/EEDATA, **10 kΩ pull-up on DO** to VCCIO (Table 3.3 "for correct operation"); CS/CLK pull-ups are N.F. in the figure. ACBUS7/PWRSAV# (pin 31) left open is fine as long as "Suspend on ACBus7 Low" stays disabled (its default is TriSt-PD, so enabling that option with the pin open would hold the chip in suspend; DS pp. 10, 48). None of these rows are in `parts-list.md` §4 (the existing [Med] "Parts list" finding lists them generically).
- **Impact:** a missing REF resistor or TEST left floating gives a dead or flaky HS PHY.
- **Fix:** add: 1 × 12 kΩ 1 % 0402 (JLC basic C25752, unverified C-number), 2 × ferrite 600 Ω/0.5 A 0603, 2 × 4.7 µF (VREGIN, VCCD) + 2 DNP pads, ~8 × 100 nF, 1 × 10 nF (RESET#), 1 × 2.2 kΩ, 1 × 10 kΩ. Keep "Suspend on ACBus7 Low" off in the EEPROM.
- **Confidence:** high (datasheet values).
- **Owner decision:** approved (2026-09-26)

### R018 [Info] USB: 93LC56BT-I/OT (C190271) is the right EEPROM
- **Evidence:** DS_FT232H §7.1 (p. 47): "The EEPROM must be 16 bits wide (93LC56B)". 93LC56B.pdf p. 1: "128 x 16-bit Organization 'B' Version (no ORG)"; SOT-23-6 ("OT") exists for A/B only, ORG is NC. JLC: C190271 = 93LC56BT-I/OT, SOT-23-6, 2.5–5.5 V, 11,203 in stock (pcbparts, 2026-09-26). FTDI's own Fig. 6.2 uses "93LC56BT-I/OT". Pinout (SOT-23-6): 1 DO, 2 VSS, 3 DI, 4 CLK, 5 CS, 6 VCC (matches the FTDI figure).
- **Confidence:** high.

### R019 [Info] USB: ABM8-272-T3 on the FT232H and CH334 oscillators: drive level is inside the crystal's 200 µW
- **Evidence:** ABM8-272-T3.pdf p. 1: CL 10 pF, ESR ≤ 50 Ω, C0 ≤ 3 pF, drive level 10–200 µW. Worst case with a full 3.3 V swing on the crystal: I_rms ≈ 2π·12 MHz·(10+3) pF·1.17 V ≈ 1.1 mA, P = I²·ESR ≈ 65 µW at 50 Ω. So even without a series resistor (FTDI's Fig. 6.4 has none) it stays under 200 µW. FT232H: 2 × 15 pF gives ≈ 7.5 + ~3 pF stray ≈ 10 pF, matching CL; FTDI's 27 pF is only an example (§6.3). The ±30 ppm in DS Table 6.1 is for an external oscillator input; USB HS allows ±500 ppm. The CH334 English reference schematic (V2.5 §6.1, p. 27) shows the crystal with no load caps, consistent with "DNP" pads.
- **Confidence:** medium-high (the estimate is an upper bound; neither chip specifies its oscillator gain).
  (Checked afterwards: C25752 = UNI-ROYAL 12 kΩ ±1 % 0402, JLC **basic**, 1.17 M stock, pcbparts 2026-09-26.)

### R020 [Info] USB: FT1248 ↔ 245 FIFO pin mapping and directions in `5-rp2350-pinout.md` are correct
- **Evidence:** DS_FT232H Table 3.13 (p. 17): MIOSIO0–7 = pins 13–20 (I/O), SCLK = 21 (in), SS_n = 25 (in), MISO = 26 (out). Table 3.8 (pp. 14–15): D0–7 = 13–20, RXF# = 21 (out), TXE# = 25 (out), RD# = 26 (in), WR# = 27 (in), SIWU# = 28 (in). So after the swap GPIO 41 and 42 turn from outputs into inputs and GPIO 43 from input into output, exactly as the page says. AN_167 §2.2 (p. 3): "Each pin of the FT232H has an internal pull up … no external pullup or down is required"; §2.1: "Unused MIOSIO lines may be left unterminated", so MIOSIO4–7 on DNP stubs are fine for 4-bit bus-width decoding (DS §4.6.1).
- AN_167 facts for the firmware: SCLK ≤ 30 MHz (§1, §2.2); only **CPHA = 1** is supported, CPOL selectable in EEPROM (§8, Table 2); bus width is chosen **per transaction by the command phase** (low on MIOSIO[3:2] = 4-bit; §4, Fig. 4.1), not by the EEPROM; commands 0x0 write, 0x1 read, 0x2/0x3 modem status, 0x4 write-buffer flush (§6, Table 1); per byte, MISO = ACK/NAK, and on NAK the master must end the transfer by raising SS_n and retry later (§5.5); with SS_n high the FT232H **drives** MIOSIO0 (= TXE#) and MISO (= RXF#) unless "no flow control during SS_n inactive" is set in the EEPROM (§3, §5.6). The master must release MIOSIO before raising SS_n after a write (§5.1). Note AN_167 §5.3 says the 4-bit data phase "requires 3 clock cycles", but Fig. 5.8/5.9 show 2 per byte; the NOTES' 15 MB/s at 30 MHz assumes 2.
- **Confidence:** high.

### R021 [Med] USB: FT232H outputs can fight RP2350 outputs on the FT1248 lines (blank EEPROM, wrong mode, or a host bit-mode call)
- **Evidence:** blank/absent EEPROM = UART mode (DS §7.1, p. 47). In UART mode ADBUS0 (pin 13 = MIOSIO0 = GPIO 32) is TXD **output**, ADBUS2 (pin 15 = GPIO 34) is RTS# **output**, ADBUS4 (pin 17) DTR# output (DS Table 3.4, p. 11); ACBUS0–2 (SCLK/SS_n/MISO pins) default to TriSt-PU inputs (Table 7.1). In FT1248 mode the FT232H also drives MIOSIO0 whenever SS_n is high (AN_167 §3). Any host program can also switch ADBUS to outputs at any time with FT_SetBitMode (MPSSE/bit-bang). GPIO 32/34 are driven by the RP2350 during command/write phases. There are no series resistors on these nets.
- **Impact:** push-pull contention (tens of mA per pin) at first power-up with the blank EEPROM if firmware starts polling the FT1248 link, during bring-up with a mis-programmed EEPROM (UART or FIFO while firmware speaks FT1248: in FIFO mode GPIO 41/42 would drive RXF#/TXE#), or after the fallback rework. Unlikely to destroy either chip quickly, but it can latch confusing states and it stresses both.
- **Fix (suggestions):** (1) 33–47 Ω series resistors on the 7 FT1248 nets at the RP2350 end (also damps ringing at 25 MHz; with the FIFO fallback they stay useful); (2) firmware: only drive MIOSIO after checking the FT232H is in FT1248 mode (e.g. MISO/MIOSIO0 behave as RXF#/TXE# while SS_n is high, or the host confirms over the CDC console), and keep the PIO pins as inputs otherwise; (3) host tool: never call FT_SetBitMode except reset (0x00).
- **Confidence:** high on the pin behaviour; medium on the severity.
- **Owner decision:** approved (2026-09-26)

### R022 [Low] USB: FIFO fallback: SIWU# (FT232H pin 28) must not float when its optional link is unfitted
- **Evidence:** DS Table 3.8 (p. 15): SIWU# "Tie this pin to VCCIO if not used." The 245-FIFO fallback makes the GPIO 46 → pin 28 link optional (page 5). ACBUS4 has an internal ~75 kΩ pull-up only as a TriSt-PU default in *other* modes (DS p. 11 note **); in FIFO mode the pin is SIWU# and FTDI asks for a tie. NOTES says "with a pull-up/down as the FT232H needs for unused inputs", but no part is listed.
- **Fix:** fit a 10 kΩ pull-up from pin 28 to the FT232H VCCIO (harmless in FT1248 mode). WR# (pin 27) is always linked in FIFO mode, so it needs none; a 10 kΩ pull-up there too keeps WR# idle during the swap.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R023 [Med] SCSI: terminator rail can fall below the SN74LVTH245A's 2.7 V minimum VCC, and the ≥ 2.5 V released level is then not guaranteed
- **Evidence:** SN74LVTH245A (SCBS130T p.3, recommended operating conditions): **VCC 2.7–3.6 V**. TPS73701 worst case with 20 k/15 k 1 %: 2.809 V × (1 ± 3 % legacy-silicon accuracy, TPS737 DS §6.5 "over VIN, IOUT, T", 10 mA ≤ IOUT ≤ 1 A) ± 1.1 % divider → **2.69–2.93 V**. At the low end the LVTH is outside its rated range, so none of its table values apply. Even taking them at face value, V_OH = VCC − 0.2 V at I_OH = −100 µA (p.4) → 2.69 − 0.2 = **2.49 V**, 10 mV under SCSI-2 §5.4.1(b)(4) "released lines ≥ 2.5 V". Also note the TPS737 accuracy is specified only for I_OUT ≥ 10 mA; the idle bus draws ~0.7 mA (3 × I_CC 0.19 mA + 80 µA divider).
- **Impact:** a spec-guarantee gap, not a likely field failure: typical LVTH V_OH at 100 µA is within tens of mV of VCC, and the far terminator also holds released lines up. Worth knowing because (b)(4) must hold "with any legal configuration".
- **Fix (options, owner's choice):** (a) set the rail to ~2.85 V (e.g. 20 k / 14.7 k → 2.842 V, worst ~2.72–2.96 V): the (b)(3) current bound still holds because it's 44.8 mA for *both* terminators together (see Info below) and the LVTH output drop reduces our share; (b) keep 2.80 V and accept, recording it as a known datasheet gap; (c) add a ~5–10 mA bleed on the rail (it was already suggested in NOTES "Terminator LDO") so the TPS737 runs inside its ≥ 10 mA accuracy spec.
- **Confidence:** high on the numbers; low on practical impact.
- **Owner decision:** approved (2026-09-26)

### R024 [Info] SCSI: SCSI-2 §5.4.1(b)(3) is a 44.8 mA two-terminator total, not a per-terminator 22.4 mA rule
- **Evidence:** §5.4.1 b) 3): "The current available to any signal line driver shall not exceed 48 mA when the driver asserts the line and pulls it to 0,5 V d.c. Only 44,8 mA of this current shall be available from the two terminators." NOTES "Terminator LDO" reads it as "each terminator ≤ 22.4 mA". Ours: (2.93 − 0.5)/108.9 Ω = 22.3 mA max (ignoring LVTH output drop), so it satisfies either reading. With a typical 2.85 V/110 Ω external active terminator at the far end (21.4 mA) the total is ≤ 43.7 mA.
- **Fix:** doc wording only (Low). Useful if the rail is ever raised (previous finding).
- **Confidence:** high.

### R025 [Med] SCSI: LVTH output-high resistance isn't specified; "110 Ω + R_out lands in 100–132 Ω" is unverified
- **Evidence:** §5.4.1 b) 1): "each supply a characteristic impedance between 100 ohms and 132 ohms". SN74LVTH245A gives only: V_OH ≥ 2.4 V at −8 mA with VCC 2.7 V (implied ≤ 37 Ω incl. offset), and ≥ 2.0 V at −32 mA with VCC 3.0 V (≤ 31 Ω) (p.4). There is no V_OH figure at ~−21 mA and VCC 2.7–2.9 V. With a bounding R_out of 30 Ω the terminator is **~140 Ω, outside 132 Ω**; with a plausible typical 5–15 Ω it's 115–125 Ω (inside). BlueSCSI v2 uses the same topology (LVT245 + 110 Ω) successfully, which suggests the typical is fine.
- **Impact:** only the bounding case violates; typical is compliant. Also, a larger R_out lowers the sink current and raises nothing dangerous.
- **Fix:** bench-measure one line: V at 110 Ω node open vs loaded with ~21 mA (asserted line) → R_out; log it in scanner-facts/NOTES. If > 22 Ω, drop the resistor to 100 Ω (and recheck the 22.4 mA share: (2.93−0.5)/(100+R_out)). No design change now.
- **Confidence:** med.
- **Owner decision:** approved (2026-09-26)

### R026 [Low] SCSI: a disabled terminator is not "LVT Ioff": the LVTH is still powered from bus TERMPWR, so its B-port bus-hold keepers load each line through 110 Ω
- **Evidence:** the LDO runs from TERMPWR, so whenever *any* device supplies TERMPWR the '245s have VCC ≈ 2.8 V, even with our board off (blocks/1-power.md notes this). With `/OE` high (DIP 00, mid-chain) the B pins are inputs with **bus hold** ("H"; SCBS130T p.1 and p.2 "Active bus-hold circuitry"). I_I(hold): ≥ +75 µA at 0.8 V and ≤ −75 µA at 2.0 V (VCC 3 V); max overdrive **+500 / −750 µA** (VCC 3.6 V) (p.4). Ioff (±100 µA) applies only at VCC = 0, which only happens when nobody supplies TERMPWR (then the bus is dead anyway). NOTES "Termination" says "with `/OE` high or the chip unpowered, the outputs go high-Z (LVT Ioff), so a powered-off board doesn't load the bus".
- **Impact:** compared with SCSI-2 §5.4.1.2 (I_IL 0 to −0.4 mA at 0.5 V; I_IH 0 to +0.1 mA at 2.7 V), the keeper current has the *wrong sign* (it sinks at 0.5 V, sources near 2.7 V) and, during a transition, up to 0.5–0.75 mA peak; through 110 Ω that's ≤ 83 mV of pull. Electrically harmless against 20+ mA terminators and 48 mA drivers, but strictly outside §5.4.1.2 in the mid-chain case. Main topology (terminator on) is unaffected, because §5.4 excludes termination from these measurements.
- **Fix:** correct the NOTES wording; no hardware change. (A non-bus-hold '245, e.g. SN74LVT245B, would avoid it, but that's preference given the magnitude.)
- **Confidence:** high on the datasheet values; the "harmless" judgement is an estimate.
- **Owner decision:** approved (2026-09-26)

### R027 [Low] SCSI: disabled terminator adds ~9 pF (C_io) to each line, pushing the mid-chain case past 25 pF
- **Evidence:** SN74LVTH245A C_io = 9 pF (p.4). Series 110 Ω doesn't isolate it at the 1 MHz where capacitance is specified (X_C ≈ 18 kΩ). Our per-line estimate: FDV301N C_oss ≈ 9–10 pF at V_DS = 2.8 V (Fig. 8, read from the curve: ~12 pF at 1 V, ~10 pF at 2 V, ~7.5 pF at 5 V) + 74LVC1G17 C_I 5 pF typ (Table 7; no max given) + H5VUD5BB C_J 0.3 typ / **0.5 pF max** + trace ~3 pF ≈ 18 pF; + 9 pF = **~27 pF** > 25 pF (§5.4.1.2) when the terminator is disabled. With it enabled, §5.4 ("termination is assumed to be external") excludes it, so the main topology is ≈ 18 pF: OK.
- **Impact:** only the secondary mid-chain topology, by ~2 pF, on typical numbers. Practically negligible at async/5 MB/s speeds.
- **Fix:** note it in NOTES "ESD protection" capacitance budget; no change.
- **Confidence:** med (typical values; no max C_I for the 1G17).
- **Owner decision:** approved (2026-09-26)

### R028 [Info] SCSI: FDV301N C_oss / C_rss at 2.8 V checked against Fig. 8
- **Evidence:** Fig. 8 (fdv301n.pdf p.4, V_GS = 0, 1 MHz, typical): at V_DS ≈ 2.8 V, **C_oss ≈ 9–10 pF**, **C_rss ≈ 2.2 pF**, C_iss ≈ 11 pF; at V_DS ≈ 0.3 V (asserted) C_oss ≈ 16 pF, C_rss ≈ 6 pF, C_iss ≈ 18 pF. NOTES' "C_oss ~10 pF, C_rss ~2.5 pF at 2.8 V" is consistent (slightly conservative on C_rss). Table values (6 / 1.3 pF) are at 10 V and don't apply.
- **Confidence:** med (read from a log-scale plot).

### R029 [Info] USB: CH334P pinout, ports and external-3.3 V wiring checked
- **Evidence (CH334DS1_en V2.5):** Fig. 1-1 (p. 1): CH334P QFN-16 = 1 XO, 2 XI, 3 DM4, 4 DP4, 5 DM3, 6 DP3, 7 DM2, 8 DP2, 9 DM1, 10 DP1, 11 DMU, 12 DPU, 13 RESET#/CDP, 14 PGANG, 15 V5, 16 VDD33, EPAD (0) = GND. So it **has** RESET#, XI/XO and all four downstream ports. Table 1-1 (p. 2): CH334P is **MTT**, no over-current detection, no power control, no external EEPROM, crystal-free optional. §4.2 (p. 20): with no internal LDO, **V5 = 3.2–3.4 V and VDD33 = 3.2–3.4 V** ("External supply voltage @ V5, no internal LDO required"), so tying V5 and VDD33 to the 3.3 V rail is the documented mode; §6.1 (p. 27) recommends exactly this for industrial use. Decoupling (Table 1-3, p. 4): V5 "external 1 µF or larger"; VDD33 "0.1 µF + 10 µF, or 1 µF". Any two downstream ports work; leave the unused DP/DM pins open (built-in pull-downs, §Features).
- **PGANG (pin 14)** is not mentioned in the notes. It is an I/O with an internal pull-up that is sampled during reset (high = ganged mode, the only mode the P supports anyway) and then becomes a static Active/Suspend **output** (§3.3.5, p. 14–15). Leave it unconnected, or use it for a hub "active" LED (≈1 kΩ, per Fig. 3-3-5 left). Don't tie it to a rail.
- **Hub power descriptor:** the CFG default 0x57 has SELF_POWER = 1 (Table 3-5-2, p. 17), so the hub reports self-powered. That's convenient: the host then doesn't limit downstream devices to 100 mA as it would behind a bus-powered hub (so an FT232H or RP2350 asking for > 100 mA still gets configured). No action needed; don't try to change it.
- **Confidence:** high.

### R030 [Med] USB: CH334 low-voltage reset threshold (up to 3.2 V) sits on the 3.3 V rail's worst case
- **Evidence:** CH334DS1_en V2.5 §4.2 (p. 21): **V_lvr = 2.5 / 2.9 / 3.2 V (min/typ/max)**; §3.2.1: below V_lvr the chip resets. External-3.3 V mode allows 3.2–3.4 V. NOTES "Resistor and small-part values": 3.3 V rail worst case **3.16–3.44 V** (legacy TPS737 silicon) or 3.21–3.39 V (new). NOTES already accepted the 3.2 V *operating* minimum risk; the LVR number wasn't considered.
- **Impact:** on a low-corner LDO plus a load step (SD write, TERMPWR enable), a max-LVR hub resets and the host sees the FT232H and RP2350 drop off the bus mid-scan. §6.1 (p. 27–28) warns about exactly this LVR-triggered disconnect.
- **Fix (no redesign):** measure the rail at bring-up as planned, and under load (SD write + TERMPWR on). If it reads < 3.28 V, move the divider up (e.g. R2 27 k → 26.7 k-class, if a no-fee value exists) to centre near 3.33 V; staying ≤ 3.4 V still matters because of the upper limit. Put generous local caps on VDD33 (10 µF + 0.1 µF, as §6.1 advises to ride through dips).
- **Confidence:** medium (depends on the LDO's actual corner, which JLC doesn't let us choose).
- **Owner comment:** Sounds good - leave me an unpopulated 0603 footprint to add a resistor to parallel into R2 so that I can fix it with some local rework

### R031 [Low] USB: CH334 RESET#/CDP: the external 10 kΩ pull-up may enable CDP and disable hub sleep; WCH wants the pin left undriven
- **Evidence:** CH334DS1_en §3.2.2–3.2.3, Table 3-2 (p. 11–12): RESET# has an internal ~25 kΩ pull-up. "Drive is high during power-up → Enable CDP and turn off low-power sleep"; "No drive or no connection (default) → No CDP, low-power sleep support". Table 1-3: "It is recommended to be completely suspended [floating] when not reset." WCH's fix for an MCU-driven reset is a series Schottky (Fig. 3-2-2). Low-drive requirement: ≤ 800 Ω source, pulse > 4 µs, V_ILRST ≤ 0.75 V. The NOTES table puts a 10 kΩ pull-up on "CH334 reset" and a push-pull TCA9555 pin (P14) on it.
- **Impact:** probably benign (our downstream devices don't use BC1.2 charging), but it's an undocumented state and it raises suspend current (adds to the existing "USB suspend current" finding). A 10 kΩ external pull-up might or might not count as "drive high"; WCH doesn't say.
- **Fix:** don't fit the 10 kΩ (the internal 25 kΩ already defaults to "run", which satisfies the fallback rule). Drive the pin from P14 through a small Schottky (cathode at the expander) or keep P14 as input (hi-Z) except when pulsing low. P14 powers up as an input, so the power-up state is already "no drive".
- **Confidence:** medium (depends on how the CDP sampler reads a 10 kΩ pull-up).
- **Owner decision:** approved (2026-09-26)

### R032 [Med] USB: bench-powered with the host off, the hub's upstream D+ pull-up back-drives the cable (no VBUS detect on CH334P)
- **Evidence:** CH334DS1_en: "Built-in 1.5KΩ pull-up resistor on the upstream port" (Features, p. 0); the CH334P has no VBUS-sense pin (Fig. 1-1; the V5 pin is on the 3.3 V rail in our mode, so it can't sense VBUS either). USB 2.0 §7.1.5.1 (quoted from memory, unverified wording): "the voltage source on the pull-up resistor must be derived from or controlled by the power supplied on the USB cable such that when VBUS is removed, the pull-up resistor does not supply current on the data line". Our board runs from the bench input (R8a) with VBUS absent, e.g. the laptop asleep/off with the cable still plugged in. The FT232H and RP2350 pull-ups face the hub, which is powered, so only the hub's upstream port matters. FTDI handles the same case with PWRSAV# from VBUS via 39 kΩ (DS Table 3.2), which doesn't apply here because the FT232H is behind the hub.
- **Impact:** ~2 mA through 1.5 kΩ into a powered-off host's D+ (and its ESD/body diodes). A spec violation rather than a likely failure; some hosts wake or misdetect.
- **Fix (suggestion):** hold the hub in reset when VBUS is absent. Cheapest: a VBUS_PRESENT divider (e.g. 10 k / 15 k from the USB-C VBUS, before the ORing diode) into a spare expander input (P06), and firmware drives HUB_RESET_N low while it reads 0. Hardware-only option: a divider from VBUS straight to RESET#: the pin is 5 V tolerant ("5I") and the bottom resistor must be ≤ ~7 kΩ to beat the internal 25 kΩ pull-up below V_ILRST = 0.75 V. **Unverified:** whether the CH334 disconnects its 1.5 kΩ pull-up while in reset. Check it on the bench (measure DPU with RESET# low).
- **Confidence:** medium.
- **Owner comment:** Realistically I'm only going to use the bench supply if my usb-c is insufficient, and I'll probably turn the bench supply off before I turn off my laptop or desktop. note it as a very minor design flaw and we can move on.

### R033 [Low] Bootstrap: CS1 re-pad erratum is RP2350-**E14**, not E15
- **Evidence:** rp2350-datasheet.pdf, Appendix E (errata, p. ~1358): **RP2350-E14** "The bootrom connect_internal_flash() function always uses pin 0, ignoring any configured CS1 pin … Manually configure the CS1 pads registers to remove the isolation". **RP2350-E15** is "otp_access() applies incorrect access permission to pages 62 & 63". NOTES line 439 (GPIO budget table) cites E15.
- **Fix:** change "E15" to "E14" in the NOTES table.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R034 [Question] Bootstrap: which RP2350 stepping will JLC fit (A2 vs A3/A4)?
- **Evidence:** rp2350-datasheet.pdf errata: **RP2350-E9 affects A2 only**; E10 (UF2 drag-and-drop fails with a partition table) is A2 only; E19 fixed by the A3 bootrom; the A4 bootrom fixes E18 and more. The 4.7 kΩ gate pull-downs and the "clear input enable" firmware rule exist only because of E9.
- **Impact:** none if we keep the E9 mitigations (they cost nothing on A4). But on A2 silicon, UF2 drag-and-drop stops working as soon as we add an A/B partition table (the "later, optional" in-app update plan), and picotool must be used instead.
- **Question for the owner:** check the date code/stepping of JLC's C42415655 stock before ordering (or read it at bring-up with `picotool info -a`, which prints the chip revision). Keep the E9 mitigations regardless.
- **Confidence:** high on the errata scope; unknown stepping.
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** Let's assume A4. A3 is impossible. A2 is possible but unlikely.

### R035 [Info] USB: RP2350 native USB behind the hub: 27 Ω, VBUS detect, errata, ESD
- **27 Ω:** "Hardware design with RP2350" §5.1: USB_DP/DM need no extra pull-ups; 27 Ω series close to the chip. OK as planned.
- **VBUS detect:** there is no VBUS_DETECT pin in our pin map. That's fine: the RP2350 datasheet §12.7 (USB, p. ~1180, `usb_hw->pwr = USB_USB_PWR_VBUS_DETECT_BITS | …_OVERRIDE_EN_BITS`) shows the forced-VBUS override, which the SDK/TinyUSB and the bootrom use. Behind an always-powered on-board hub, "VBUS" is effectively always present. Side effect (datasheet §12.7.3.8.4): the RP2350 can't tell "host unplugged" from "suspended". Firmware shouldn't care.
- **Errata:** RP2350-E12 (USB status signals not synchronised) bites only when clk_sys ≤ clk_usb (48 MHz); we run 150 MHz. No other USB-device erratum affects us.
- **ESD at HS:** H5VUD5BB 0.3 pF typ (h5vud5bb.pdf p. 1), one per line; negligible for 480 Mbit/s. V_RWM 5 V > the 3.6 V D± maximum. OK.
- **USB-C:** both D+/D− pairs tied at the receptacle (the stub is < 1 mm on the HRO footprint if tied at the pads); CC1/CC2 each with its own 5.1 kΩ Rd (parts list §1) → correct sink. OK.
- **100 mA before configuration:** confirmed as a deviation (USB 2.0 §7.2.1: one unit load until configured); already accepted. Behind the hub nothing else changes.
- **Confidence:** high.

### R036 [Info] SCSI: FDV301N V_OL, real sink current, I_DSS, gate drive checked
- **Evidence (fdv301n.pdf p.2):** R_DS(on) ≤ 5 Ω at V_GS 2.7 V, 25 °C; ≤ 9 Ω at T_J 125 °C (I_D 0.2 A). Our V_GS = 3.3 V × 4.7k/4.8k ≈ 3.2 V (≥ 3.1 V at the 3.16 V worst rail), so the 2.7 V row is conservative. Real load: our terminator ≤ 2.93 V/108.9 Ω + a far 2.85–2.9 V/110 Ω active terminator: I = 53.5 mA/(1 + 2R/109) → **49 mA, V_OL 0.25 V** at 5 Ω; **46 mA, V_OL 0.41 V** at 9 Ω. Meets §5.4.1.1 (≤ 0.5 V at 48 mA). Self-heating 48 mA² × 5 Ω = 12 mW → +4 °C (R_θJA 357 °C/W). I_DSS ≤ 1 µA (10 µA at 55 °C) at V_DS 20 V, far under I_IH 0.1 mA. Gate: Q_g to ~3.2 V ≈ 0.37 nC (Fig. 7), plateau 2.1 V, through 100 Ω + pad → turn-on/off ≈ 5–15 ns; static pull-down load 0.69 mA per asserted pin (≤ 9.6 mA for all 14). V_GS abs max 8 V, V_DS 25 V: fine.
- **Confidence:** high.

### R037 [Low] SCSI: gate-kick concern is real in size but self-limiting; the "fit 22 pF above 0.4 V" rule is stricter than needed
- **Evidence:** integrating C_rss(V) from Fig. 8 over a 0.3→2.8 V rising edge gives ≈ 8 pC; into C_gs + C_gd ≈ 12–14 pF (Fig. 8) held by 4.7 kΩ (τ ≈ 60 ns ≫ a ~5–10 ns incident-wave edge) → **≈ 0.55–0.65 V** kick, matching NOTES' ~0.6 V. But V_GS(th) (0.70–1.06 V, −2.1 mV/°C) is defined at I_D = 250 µA, so a kick to ~0.7 V for tens of ns sinks at most a few hundred µA from a 20+ mA terminator, and it acts *against* the rising edge (negative feedback), so it can't latch or glitch the line. With the board powered, the gate sees ~150 Ω and the kick is ~0.
- **Impact:** none expected; bench check still worthwhile. If fitted, 22 pF slows our own switching only to τ ≈ 150 Ω × 37 pF ≈ 5.5 ns: harmless.
- **Fix:** reword the bench criterion to "fit the caps if the kick produces a visible dip/step on the bus edge", not a gate-voltage number.
- **Confidence:** med (typical curves).
- **Owner decision:** approved (2026-09-26)

### R038 [Info] SCSI: 74LVC1G17 thresholds, I_OFF, input tolerance, output drive re-checked; small doc slip
- **Evidence (74LVC1G17.pdf Rev 16.1, Table 8 p.6):** at V_CC 3.0 V: VT+ 1.29–1.71 V (−40…85 °C) / **1.26–1.71 V (−40…125 °C)**; VT− 0.88–1.24 V / **0.88–1.27 V**; V_H ≥ 0.31 / 0.25 V. At 4.5 V: VT+ ≤ 2.36, VT− ≥ 1.32. Linear interpolation to 3.3 V: VT+ ≤ 1.84, VT− ≥ 0.97 (NOTES correct). At the 3.3 V rail's own worst case (3.16–3.44 V, NOTES resistor table): **VT+ ≤ 1.90 V, VT− ≥ 0.93 V**: still inside SCSI-2's 2.0/0.8 V, margin 0.10/0.13 V (interpolated, not guaranteed). I_OFF ±2 µA and I_I ±1 µA at 5.5 V (Table 7); V_I rated 0–5.5 V (Table 6), so 5.25 V bus is fine. Output: V_OH ≥ 2.3 V at −24 mA/3.0 V (≈ ≤ 29 Ω); a shorted LA pin draws ≤ 3.3/(100+~25) ≈ 26 mA (abs max ±50 mA, P_tot 250 mW): fine. tpd 0.7–5.5 ns → channel skew ≤ 4.8 ns: negligible. NOTES' "VT+ 1.29–1.71, VT− 0.88–1.24 (−40…125 °C)" quotes the 85 °C columns under a 125 °C label (Low doc slip).
- Fallback 74LVC14A (Nexperia Rev 11, Table 9): VT+ 1.2–**2.0** V at 3.0 and 3.6 V: meets VIH ≤ 2.0 V with **zero** margin; VT− ≥ 0.8 (zero margin); V_H 0.3–1.2 V. "Guaranteed" is right but it's at the edge; worth saying in NOTES.
- **Confidence:** high.

### R039 [Low] SCSI: '245 DIR pin and A inputs must be tied explicitly; say so in NOTES
- **Evidence:** SN74LVTH245A function table (p.2): /OE L + DIR **H** = A→B; DIR L = B→A. NOTES/parts-list only say "A inputs tied high, /OE = enable"; DIR isn't mentioned. With DIR low, the A pins become outputs fighting the tie to VCC whenever the bus is asserted (≈ 64–128 mA-class short per pin) and the B side stops terminating. Datasheet note 5 (p.3): unused control inputs at VCC or GND; bus-hold inputs shouldn't use pull resistors (p.2), so tie A1–A8 and DIR straight to the 2.8 V rail. Unused A7/A8/B7/B8 (6 of 8 used): B7/B8 leave unconnected (they'll just drive high).
- **Fix:** add to NOTES "Termination" and the schematic checklist.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R040 [Info] SCSI: /OE network levels checked (DIP / 10 k / 1 k / TCA9555)
- **Evidence:** DIP1 on: 2.8 V × 1k/11k = **0.25 V** (V_IL ≤ 0.8 V). With TCA9555 inputs' internal 100 kΩ pull-ups to 3.3 V (I_IL −100 µA at GND, tca9555.pdf p.7) still ≈ 0.28 V. Off: ≈ 2.8–2.85 V (V_IH ≥ 2.0 V). Expander driving high against DIP1: ~3.1 mA, V_OH ≥ 2.6 V at −8 mA/3 V (p.7) → node ≈ 3.1 V: /OE high. LVTH control inputs tolerate 5.5 V even at VCC 0 (I_I 10 µA, p.4), so 3.3 V on /OE with VCC 2.8 V is fine; ≤ 50 µA flows back into the 2.8 V rail via the 10 k, less than the rail's ~0.7 mA idle load. Enable/disable times t_PZH/t_PHZ ≤ 7.4 ns (p.5): irrelevant for a static switch.
- **Confidence:** high.

### R041 [Info] SCSI: per-package current and power-up ramp of the LVTH terminator
- **Evidence:** 6 lines × ≤ 22.3 mA = 134 mA through one VCC pin. SCBS130T has **no** continuous VCC/GND pin current rating (only per-output I_OH −32 mA recommended, p.3); each output at ~22 mA is inside that. Dissipation ≈ 6 × 22 mA × ~0.3 V ≈ 40 mW → +3 °C (θ_JA 83 °C/W PW). BlueSCSI v2 runs 8 per package. Power-up ramp: SCBS130T recommends Δt/ΔV_CC ≥ 200 µs/V (p.3); TPS737 start-up ≈ 431–600 µs to 3 V with 1 µF (tps737.pdf §6.5) ≈ 150–200 µs/V, at the edge; more C_OUT slows it. Effect is only a possible sub-ms glitch at power-up while I_OZPU keeps outputs high-Z below 1.5 V. Acceptable.
- **Confidence:** med (no package-current spec exists to check against).

### R042 [Low] SCSI: our 2.8 V terminator rail can be pumped up by a push-pull / active-negation driver elsewhere on the bus
- **Evidence:** SCSI-2 §5.4.1.1 allows three-state drivers with V_OH up to 5.25 V. SN74LVTH245A abs max note 2 (p.3): "current into any output in the high state … flows only when … V_O > V_CC" (64 mA max per output), i.e. there is a path from an output pin to VCC. A line driven high to V > ~2.8 V + ~0.5 V pushes up to (V − 3.3)/110 Ω into our rail per line (e.g. 3.8 V active negation → ~4.5 mA per line, ×9 data lines ≈ 40 mA). The TPS737 can't sink, and the rail's own load is ~0.7 mA idle, so the rail would rise toward the bus level, raising every released line's terminator voltage (and VCC abs max for the LVTH is 4.6 V). NOTES "Terminator LDO" already flags "LDO can't sink" as a to-check.
- **Impact:** unlikely in our topologies (WD33C93A and most SCSI-2 SE drivers are open-drain, active-negation parts typically negate to ~2.5–3.3 V), unverified for the G4's Adaptec card.
- **Fix:** fit the bleed NOTES already suggests: e.g. 270 Ω to GND on the 2.8 V rail (~10 mA, 29 mW; also puts the TPS737 inside its ≥ 10 mA accuracy spec). Scope the rail during the G4 captures.
- **Confidence:** low (V_O > V_CC path magnitude not characterised in the datasheet).
- **Owner decision:** approved (2026-09-26)

### R043 [Info] Bootstrap: first power-up of a fresh JLC board (blank flash, blank EEPROM) works without any firmware
Walk-through, USB-C to a Mac or a Windows PC:
1. **Hub:** the CH334P is fixed-function (config in internal ROM, CFG default 0x57; CH334DS1_en §3.5), so it enumerates as a USB 2.0 HS hub as soon as 3.3 V and its crystal are up (POR delay 5–14 ms, §3.2.1). No driver on either OS (inbox hub class).
2. **FT232H:** blank EEPROM → built-in defaults: VID 0403, PID 6014, "Single RS232-HS", UART mode, no serial number (DS §7.1, Table 7.1). It enumerates at HS behind the hub. macOS: Apple's DriverKit `AppleUSBFTDI` dext binds it (see the Host finding). Windows: the FTDI CDM driver comes from Windows Update (internet needed on first plug; offline machines need FTDI's installer).
3. **RP2350B:** blank flash has no valid IMAGE_DEF, so the bootrom falls through to BOOTSEL: USB mass storage ("RP2350" drive) + the PICOBOOT vendor interface, VID 2E8A PID 000F (rp2350-datasheet §5.6.1). QSPI SD1 is pulled down by default → USB boot, not UART boot (§5.2.4.1, §5.8); nothing on our bus drives SD1 while CS0 is low with no clock, and the PSRAM's CS1 is held high by the fitted 10 kΩ on GPIO 47. It needs the 12 MHz crystal (the bootrom assumes 12 MHz unless OTP says otherwise, §5.8.1); we have it. Behind the hub, full speed through the hub's TT; nothing special.
4. **Flashing:** drag a UF2 onto the drive (macOS and Windows, no driver), or `picotool load`. picotool uses libusb: macOS needs nothing; on Windows the RP2350 bootrom carries WCID/MS OS descriptors so WinUSB binds without Zadig (picotool README, https://github.com/raspberrypi/picotool; unverified on our board). The SDK's default UF2 family is `rp2350-arm-s` 0xE48BFF59 (RP2350A and B share family IDs; datasheet Table 455). **No partition table is needed**: without one, a non-absolute UF2 is written to the start of flash (datasheet §5.1.18 ≈ p. 399, "The UF2 is always downloaded to the start of flash").
5. **Back to BOOTSEL later without a button:** `picotool reboot -f -u` uses the app's reset interface. With `pico_stdio_usb`, `PICO_STDIO_USB_RESET_INTERFACE_SUPPORT_MS_OS_20_DESCRIPTOR` defaults to 1, so Windows binds WinUSB automatically (pico-sdk `stdio_usb.h`, https://github.com/raspberrypi/pico-sdk/blob/master/src/rp2_common/pico_stdio_usb/include/pico/stdio_usb.h). **If we write our own TinyUSB descriptors** (CDC + reset + anything else), we must carry the BOS/MS OS 2.0 descriptor ourselves, or Windows will need Zadig for picotool (R5). Firmware can also call the ROM `reboot()` with BOOTSEL directly on a CDC command.
6. **Buttons and SWD:** BOOTSEL = QSPI_SS → 1 kΩ → button (guide §3.1) is right, and it stays right with the PSRAM because the PSRAM is on CS1. SWD via TC2030: pad 1 VCC gives the J-Link its VTref; pad 3 → RUN. J-Link supports RP2350 flash programming; the PSRAM on CS1 doesn't interfere.
- **Confidence:** high, except the Windows WCID detail (from the picotool README, not tested).

### R044 [Med] Bootstrap: FT232H EEPROM first programming on macOS: `ftdi_eeprom` can set FT1248 mode but not its clock-polarity / bit-order / flow-control bits, and needs `eeprom_type=0x56` and root
- **Evidence:**
  - Blank EEPROM is programmable over USB, by design: DS §7.2 (p. 47) "This allows a blank part to be soldered onto the PCB and programmed as part of the manufacturing and test process." FT_PROG (Windows) exposes FT1248 mode and its three options (DS Table 7.1 "FT1248 Settings … Clock Polarity High; Bit Order LSB and Flow Control"; AN_167 §3, §7, §8).
  - libftdi 1.5 (latest release; source read from https://www.intra2net.com/en/developer/libftdi/download/libftdi1-1.5.tar.bz2): `ftdi_eeprom/main.c` accepts `cha_type = FT1284` (libftdi's name for FT1248; `CHANNEL_IS_FT1284`, written as type 0x08 for the FT232H), but has **no config keys** for the FT1248 options. The library itself supports them (`ftdi_set_eeprom_value(ftdi, CLOCK_POLARITY | DATA_ORDER | FLOW_CONTROL, …)`, bits 0x01/0x02/0x04 at EEPROM byte 0x01), with the source comment `FT1284_DATA_LSB 0x02 /* DS_FT232H 1.3 and ftd2xx.h 1.0.4 disagree here */`.
  - `ftdi_eeprom_build()` sets the image size to 0x100 only if `chip == 0x56 || 0x66`; `ftdi_eeprom`'s `eeprom_type` defaults to 0, which builds a 128-byte (93x46) image. An FT232H with a 93LC56B needs `eeprom_type = 0x56`.
  - On macOS the Apple dext holds the interface, so libftdi can only open the device as root (it auto-detaches the kernel driver; see the Host finding).
- **Impact:** not a bricking risk (see next finding), but the first programming on a Mac needs a small custom program, not just a config file, and the LSB bit meaning is ambiguous between FTDI's own documents.
- **Fix (suggestions):** (a) do the first programming once with FT_PROG on any Windows PC and read the result back with `ftdi_eeprom --read-eeprom` to capture a golden 256-byte image; afterwards macOS can write that image with `flash_raw = true`. Or (b) write a ~30-line libftdi (or pylibftdi) program that sets CHANNEL_A_TYPE = FT1284, CLOCK_POLARITY, DATA_ORDER, FLOW_CONTROL, VID/PID, strings, and `CHIP_TYPE = 0x56`, then builds and writes. Either way, **verify the FT1248 bits on the bench**: with SS_n high and flow control on, MISO should follow RXF# and MIOSIO0 TXE#; clock polarity shows in the first command-phase edge. Also set "Suspend on ACBus7 Low" = off, self-powered = on (the hub is self-powered), and max power ≈ 100 mA.
- **Confidence:** high on the libftdi source; the FT1248 bit semantics are unverified.
- **Owner decision:** approved (2026-09-26)

### R045 [Info] Bootstrap: the FT232H can't be bricked by bad EEPROM contents
- **Evidence:** EEPROM reads/writes are vendor control requests on endpoint 0, which work in every interface mode. A bad checksum makes the chip ignore the EEPROM and fall back to the defaults (0403:6014, UART) (DS §7.1). The worst self-inflicted case is a custom VID/PID that no driver matches: libusb/libftdi opens any VID/PID; D2XX needs `FT_SetVIDPID` on macOS (on Windows, an INF edit). If all else fails, shorting the 93LC56B DO to GND via a pad during power-up forces a blank read (unverified trick; not needed normally).
- **Confidence:** high.

### R046 [Info] SCSI: H5VUD5BB on a 2.8–5.25 V bus
- **Evidence (h5vud5bb.pdf p.2):** V_RWM 5.0 V; V_BR 6.0–10 V at 1 mA; I_R ≤ 0.2 µA at 5 V; C_J 0.3 typ / 0.5 pF max; bidirectional. The terminated bus idles at 2.7–3.2 V (active or 220/330 passive from ≤ 5.25 V TERMPWR). Only a push-pull driver at the SCSI-2 V_OH ceiling (5.25 V, §5.4.1.1) exceeds V_RWM, by 0.25 V, still 0.75 V below min breakdown; leakage there is µA-level at most vs I_IH 100 µA. OK.
- **Confidence:** high (datasheet), leakage at 5.25 V inferred.

### R047 [Info] SCSI: rise/fall and stubs
- **Evidence:** releasing our FET removes ~47 mA from a node that sees our 110 Ω terminator in parallel with the cable (ribbon Z0 ≈ 90–100 Ω, typical, unverified): the incident step at our connector is ≈ 47 mA × ~50 Ω ≈ 2.3 V, i.e. to ≈ 2.5 V in one step, then RC with ~18 pF × 50 Ω ≈ 1 ns. So the released edge at our end is incident-wave, not "terminator into cable capacitance" RC; NOTES' "slower rising edge" is pessimistic (the real delay is FET turn-off, see the data_out deskew finding). Falling: 5 Ω FET into ~50 Ω → one step to ~0.25 V in the FET's ~5–10 ns switching time; 100 Ω gate resistor is the slew knob. Stub: §5.2.1 ≤ 0.1 m incl. inside the device; with per-line clusters by the IDC50 the on-board stub is ≲ 30–50 mm (layout to confirm); at the end-of-chain position the on-board run to the terminator is part of the end, not a stub.
- **Confidence:** med (cable Z0 assumed).

### R048 [Info] SCSI: RP2350-E9 handling and the 4.7 kΩ pull-down
- **Evidence:** RP2350 datasheet p.1366–1367: leakage (~120 µA, source ≈ 2.2 V) occurs only with IE = 1, output disabled, and the pad voltage in the undefined region; a pull ≤ 8.2 kΩ keeps it low, and clearing IE removes it. 4.7 kΩ holds a floating gate at ~0 V (below VIL) so the leakage never starts. Reset state IE = 0 (NOTES cites Table 853). The firmware rule (clear IE on the 14 gate pins) is correct: PIO never needs to read them (IN_COUNT = 18 masks GPIO 18–31 from `mov x, pins` in the sniffer anyway).
- **Confidence:** high.

### R049 [Low] SCSI: no firmware rule for "TERMPWR absent"; floating inputs with no termination
- **Evidence:** with TERMPWR off (USB port < 1.5 A and no bench supply, jumper out, or eFuse fault) and no other device supplying it, both terminators are dead: released lines float (only FET I_DSS and 1G17 ±1 µA leakage), so the 1G17 inputs sit at undefined levels (ΔI_CC up to 500 µA each, Table 7) and read random data; the '245 has VCC = 0 (Ioff ±100 µA). SCSI-2 §5.4.1(b)(5) needs "at least one device supplying TERMPWR". TERMPWR_OK (expander P05) and TERMPWR fault (FLT) exist.
- **Impact:** firmware may see phantom BSY/SEL/REQ and try to run phases on a dead bus.
- **Fix:** firmware rule: no arbitration/selection unless TERMPWR_OK; report "no TERMPWR" to the host; sniffer marks captures invalid while TERMPWR_OK is low.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R050 [Info] SCSI: parity, DB(P) in arbitration, listen-only
- **Evidence:** §5.6/Annex (NOTES table): DB(P) odd parity required in SCSI-2, undefined during arbitration, must not be driven false then. Open-drain can't drive "false" at all, and the arbitration step writes only our ID bit (the injected instruction must write a 9-bit word with only that bit set, or use `set`, so DBP stays released). data_out carries precomputed parity in bit 8; data_in captures DBP in bit 8, so firmware can check it (SCSI-2 makes checking optional for the initiator; recommend checking and logging). Listen-only: all gates held low by firmware + 4.7 k; receivers always on; nothing drives: OK.
- **Confidence:** high.

### R051 [Low] SCSI: remaining doc inconsistencies in the terminator/PIO text
- **Evidence:** NOTES "Termination" still says "8 × 24 mA ≈ 190 mA through one '245 Vcc pin" (now 6 × ≤ 22.3 mA ≈ 134 mA) and "the 2.85 V idle"; blocks/2-scsi-frontend.md says "3 × 74LVT245" (the part is SN74LVTH245A, bus-hold variant, which matters for the bus-hold finding above); NOTES PIO sketch comment "≥ 55 ns deskew" (SCSI-2 Table 7 deskew = 45 ns; 55 ns = deskew + cable skew); NOTES "Terminator LDO" "(b)(3) allows each terminator ≤ 22.4 mA" (the text is a 44.8 mA two-terminator total). Log entry 2026-09-24 "2.85 V LDO → 74LVT245" is history, fine as is.
- **Fix:** wording only.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R052 [Med] Host: on macOS, Apple's built-in FTDI DriverKit driver claims the FT232H (0403:6014), so libusb/pyftdi and D2XX can't open it without root
- **Evidence:**
  - On the owner's own Mac (Darwin 25.6): `/System/Library/DriverExtensions/com.apple.DriverKit-AppleUSBFTDI.dext/Info.plist` has a personality **"DriverKit-AppleUSBFTDI-6014"** matching idVendor 1027 (0x0403), idProduct 24596 (0x6014), bInterfaceNumber 0 (checked with `plutil -p`, 2026-09-26). It ships with macOS; it is not the old kext that pylibftdi's docs say was removed in Monterey.
  - A 2025/26 report of exactly this: "macOS's DriverKit FTDI driver (`com.apple.DriverKit-AppleUSBFTDI`) claims the FT232H's only interface", unprivileged libftdi tools see no device, and the workaround is `sudo` (https://github.com/thejefflarson/little-cpu/pull/358).
  - FTDI's own macOS answer for D2XX is `D2xxHelper.kext`, a codeless kernel extension that stops VCP drivers matching (FTDI AN_134, https://www.ftdichip.com/Support/Documents/AppNotes/AN_134_FTDI_Drivers_Installation_Guide_for_MAC_OSX.pdf). That's a third-party kext: against R5, and on Apple Silicon it needs Reduced Security. Whether it even pre-empts a DriverKit dext is unverified.
  - The EEPROM "Load VCP driver" / "D2XX direct" bit is only honoured by FTDI's Windows driver, not by Apple's matching (Apple matches on VID/PID/interface).
- **Impact:** R5 ("no custom kernel drivers on macOS") and the plan "D2XX/pyftdi on the host" conflict on macOS with the default PID. The host tool would have to run as root, or use a different path.
- **Options (for the owner, see the Question below):**
  1. **Keep 0403:6014 and use Apple's serial node** (`/dev/cu.usbserial-<serial>`) as the data pipe on macOS. In FT1248/FIFO modes the bulk endpoints carry the data regardless of baud settings, so this can work driverlessly. Follow-up research (below) makes this the leading option; throughput is still unmeasured.
- **Follow-up (2026-09-26): what the Apple dext actually does.** Disassembled on the owner's Mac (Darwin 25.6, arm64e). `AppleUSBFTDI` is a thin subclass of Apple's generic `IOUserUSBSerial` (USBSerialDriverKit, extracted from the DriverKit dyld shared cache); the USB plumbing is all in the base class.
  - **Data path is mode-agnostic.** `AppleUSBFTDI::handleRxPacket` strips the 2 FTDI status bytes at the start of each IN transfer (reports modem/line-error bits) and passes the rest through. Nothing checks the chip mode, so FT1248 data should flow. It drops XON/XOFF bytes only if software flow control is on, so open the port raw (`cfmakeraw`, no IXON/IXOFF; pyserial does this).
  - **Throughput limit: one 512-byte read in flight.** `IOUserUSBSerial_IVars::rxSubmit` issues one `IOUSBHostPipe::AsyncIO` of wMaxPacketSize bytes (read from the endpoint descriptor at start: 512 at HS). It won't submit another until `rxComplete` has run in the dext and copied the data **byte by byte** into the ring buffer. So each 510 payload bytes pay a full kernel → dext → kernel round trip. Estimate (**unverified**): 50–150 µs per trip ≈ 3–10 MB/s, plus the tty layer above it, whose limit is unknown. R3's 1.5 MB/s looks plausible, not certain. If the host lags, the dext stops resubmitting (backpressure), the FT232H's 1 KB buffer fills and TXE#/flow control holds the RP2350 off. **Slowness costs speed, not data.**
  - **Interface opened only while the tty is open.** `IOUSBHostInterface::Open` is called only from `ConnectQueues` (the tty open) and `Close` from `DisconnectQueues`. While nobody has `/dev/cu.*` open, the dext holds no open on the interface. This fits PyFtdi's docs ("from Mojave the Apple kernel extension peacefully co-exists with libusb and PyFtdi") and conflicts with the little-cpu report above. Whether unprivileged libusb/pyftdi can claim it while the tty is closed is **unverified**; needs a bench check.
  - **Latency timer:** `AppleUSBFTDI::HwProgramLatencyTimer_Impl` sends vendor request 0x09 (SET_LATENCY_TIMER). User space reaches it with `ioctl(fd, IOSSDATALAT, &v)` (OpenBCI forum, https://openbci.com/forum/index.php?p=%2Fdiscussion%2F3108; reports that the unit is really ms, not µs, and that 0 misbehaves). We barely need it: FT1248 has a **write-buffer-flush command (0x4)** that flushes "rather than wait for any latency timers to expire" (AN_167 Table 1, p. 19). Firmware sends it after each short reply.
  - **FTDI's own dext is also installed on this Mac:** `com.ftdi.vcp.dext` 1.1 (from `FTDIUSBSerialDextInstaller_1_5_0`, dmg dated 2024-08-27), active per `systemextensionsctl list`. It has an "FT232H" personality (0403:6014, bcdDevice 0x0900) in a different `IOMatchCategory` (`com.qa.driverkit`), and its class (`NullDriver`, a leftover sample name) also subclasses `IOUserUSBSerial`: same one-packet read engine. It has no `HwProgramLatencyTimer_Impl` (the latency comes from its plist `ConfigData`), so IOSSDATALAT probably does nothing with it. Which dext binds, or whether both try to, is **unverified**. Check with `ioreg -l -w0 -r -c IOUSBHostInterface` when a board is plugged in. Removing FTDI's dext (System Settings › General › Login Items & Extensions › Driver Extensions) is optional.
  2. **Keep 0403:6014 and run the host tool as root** (libusb ≥ 1.0.25 can detach a kernel driver on macOS as root, or with the `com.apple.vm.device-access` entitlement, which needs Apple's approval). Works, but poor for a web-UI tool.
  3. **Custom PID in the EEPROM** (an FTDI-assigned PID under 0403, free on request, DS §7.2; or pid.codes). macOS then leaves it alone: libusb/pyftdi work unprivileged, D2XX via `FT_SetVIDPID`. **But on Windows** the FTDI driver from Windows Update only matches FTDI's standard PIDs, so the device gets no driver; a modified INF breaks FTDI's signature, and WinUSB needs Zadig (a user-installed INF). That trades a macOS problem for a Windows one.
- **Confidence:** high that the dext matches the device (plist). Now medium-high that option 1 carries FT1248 data correctly and that the latency timer can be controlled (code read). Throughput vs. R3 is still unmeasured; the bench test (FT232H module in 245 FIFO fed by a Pico PIO, `cat /dev/cu.usbserial-* | pv`) settles it and the libusb-coexistence question for ~$15.
- **Owner comment:** we talked about this in another thread and I think it's fine.

### R053 [Question] Host: which OS gets the "driverless" FT232H path, and is R5 still the requirement as written?
- **Evidence:** R5 (NOTES Requirements) says "no custom kernel drivers on macOS, Linux or Windows. That means vendor-class bulk with WinUSB/MS OS 2.0 descriptors, or CDC/NCM." The FT232H provides neither: its descriptors are fixed (no BOS/MS OS 2.0), and on Windows it relies on FTDI's own kernel driver (ftdibus.sys), which `4-software/NOTES.md` already accepted because it installs from Windows Update. So R5 is already relaxed in practice on Windows, and the previous finding shows macOS needs a decision too.
- **Question:** (a) Update R5 to "no *user-installed* drivers: FTDI's Windows Update driver is OK", and (b) pick one macOS path: Apple serial node (test early), root, or a custom PID with a Windows-side cost. A bench test of option 1 on the first board (or on any FT232H module in FIFO mode now, for ~$15) would settle it cheaply.
- **Confidence:** n/a (owner's call).
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** prefer MacOS. Yes I think R5 is still true.

### R054 [Info] Host: D2XX and the RP2350's interfaces on Windows
- **D2XX with FT1248:** FT1248 is selected in the EEPROM and moves data over the same bulk endpoints as the 245 FIFO, so `FT_Read`/`FT_Write` apply unchanged (the D2XX `FT_EEPROM_232H` structure has FT1248Cpol/Lsb/FlowControl fields). Use `FT_SetBitMode(0, 0x00)` (reset) only, never MPSSE/bit-bang modes (see the contention finding). Tune `FT_SetLatencyTimer` / `FT_SetUSBParameters` for throughput. **Unverified** on hardware; no FTDI document found that states FT1248 + D2XX explicitly.
- **RP2350 app side:** CDC ACM binds to inbox drivers on Windows 10+ (usbser.sys) and macOS; the pico-sdk reset interface carries MS OS 2.0 descriptors by default (see the bootstrap walk-through). Both meet R5 as written.
- **Custom PID and Windows:** FTDI's WHQL driver matches only FTDI's standard VID/PIDs; a custom PID needs an edited INF, which invalidates the signature (from memory: FTDI's driver-customisation notes; unverified wording).
- **Confidence:** medium.

### R055 [Low] USB: stale text in NOTES "FT232H pins in detail"
- **Evidence:** NOTES "FT232H pins in detail" still says "Async 245 FIFO, which is the mode we plan to use" and "FT1248 … Its throughput at each width is unverified (it's in AN_167, not yet downloaded)". AN_167 is in `reference/datasheets/` and FT1248 4-bit was decided 2026-09-24 (GPIO budget). Its EEPROM line ("`ftdi_eeprom` on macOS/Linux") also needs the caveats in the EEPROM-programming finding above.
- **Fix:** mark that section as "reference for the FIFO fallback" and point to the FT1248 decision.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R056 [Low] Docs: CS1 erratum number `[fixed]`
- **Evidence:** NOTES cited "RP2350-E15" for the CS1 re-pad. The RP2350 datasheet erratum about the bootrom's `connect_internal_flash()` ignoring the configured CS1 pin is **RP2350-E14** (datasheet p. 1356/1359). E15 is about `otp_access()`.
- **Fix:** NOTES corrected to E14.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R057 [Med] Power: bench eFuse EN/UVLO pin exceeds its 6.5 V absolute maximum with a 24 V adapter
- **Evidence:** String R1 510 k / R2 56 k / R3 150 k: EN tap = V_IN × 206/716 = 0.2877 × V_IN. At 12 V: EN 3.45 V (OK). At **24 V: EN 6.91 V**; at 28 V: 8.06 V. TPS25947 SLVSFC9C §6.1: V_EN/UVLO abs max **6.5 V** (reached at V_IN = 22.6 V); §6.3 recommended max 5 V (reached at 17.4 V). OVLO tap = 0.2095 × V_IN → 5.03 V at 24 V, 5.87 V at 28 V, inside its 6.5 V abs max. Any UVLO near 4.2 V forces the same EN ratio, so re-ratioing can't fix it. NOTES "Bench 5 V input protection" lists "a 12 V or 24 V adapter" as a design case.
- **Impact:** The one scenario the part was chosen for (24 V adapter) puts the EN pin 0.4 V above abs max through a 147 kΩ Thevenin source (~3 µA if an internal clamp exists; the datasheet shows none). Probably survives, but not by the datasheet.
- **Fix:** Clamp EN: a small Zener (≈5.1–5.6 V, SOD-323, basic) from EN/UVLO to GND. At normal input (EN ≈ 1.44 V) its leakage is negligible. With EN clamped at 5.6 V, OVLO = 4.1 V, so OV lockout still holds. Alternatively, split into separate EN and OVLO dividers with a clamp on EN only.
- **Confidence:** high on the arithmetic and ratings. Damage threshold unverified.
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** use the zener

### R058 [Info] Power: bench eFuse thresholds recomputed (UV, OV, hysteresis, ILIM, dVdt)
- **Evidence (SLVSFC9C Eq. 1/2, §6.5):** V_UVLO(R) 1.183/1.20/1.223 V, V_UVLO(F) 1.076/1.09/1.116 V; OVLO has the same numbers. With 1 % resistors: **UV rising 4.17 V nom (4.05–4.31 V)**, UV falling 3.79 V nom (3.69–3.93 V). **OV rising 5.73 V nom (5.56–5.93 V)**, which matches NOTES. OV falling 5.20 V nom (**5.06–5.41 V**). R_ILM 1.5 k + 150 = 1650 Ω, which is exactly the datasheet row (1.800/2.028/2.200 A), so **1.78–2.22 A** incl. 1 % R. dVdt: Eq. 4 SR = 2000/2200 pF = 0.91 V/ms; I_dVdt 0.81/2.21/3.82 µA gives 0.33–1.57 V/ms, so a 5 V ramp takes 3.2–15 ms. Inrush into 47 µF ≤ 74 mA. The dVdt cap must be rated V_IN + 5 V (§6.3 note 3), i.e. ≥ 29 V for a 24 V case: C1531 is 50 V, OK. −15 V / 28 V ratings: §6.1 IN min max(−15, V_OUT − 21), max 28 V.
- **Note for USAGE.md:** after an OV trip the input must fall below 5.06–5.41 V to recover, so "turn the knob back down to 5.0 V". FLT does **not** report OV, UV or reverse polarity (Table 7-3: FLT stays H for those); it only reports over-temperature, persistent current limit and ILM faults. The expander's BENCH_FLT_N therefore can't say "bench supply rejected". If that diagnosis matters, AUXOFF (open-drain, high = input valid and inrush done, §7.3.10) is the right signal; it's currently unused.
- **Confidence:** high.

### R059 [Low] Power: reverse-polarity current into EN is ~25 µA; TI's §8.3 asks for < 10 µA
- **Evidence:** §6.1 note 2 / §6.3 note 2 say ≥ 350 kΩ pull-up (510 k meets it). §8.3 says pins derived from the input "must have a sufficiently large pull-up resistor to limit the current through those pins to < 10 µA during reverse polarity". At −15 V with EN clamped near −0.6 V: I = (15 − 0.6)/510 k − 0.6/206 k ≈ **25 µA**. (A 350 k pull-up would give ~41 µA, so TI's two statements disagree with each other.)
- **Impact:** Probably none; the NOTES claim "meets the reverse-polarity rule" is true only for the footnote version.
- **Fix:** Accept (document), or scale the string ×3 (≈1.5 M / 169 k / 453 k) at the cost of ~±1 % extra threshold error from the ±0.1 µA pin leakage.
- **Confidence:** med (clamp voltage assumed).
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** I think scale the string

### R060 [Low] Power: bench input needs a specified input capacitor and bidirectional/no TVS for reverse polarity
- **Evidence:** SLVSFC9C §8.3.1: C_IN ≈ 1 µF ceramic rated ≥ 2× input voltage; §8.4 ≥ 0.1 µF at IN. §6.1 SR_IN(R) max 100 V/µs. The note under §8.3.1: "If there is a likelihood of input reverse polarity … use a bi-directional TVS". The DNP SMF15A is unidirectional: fitted, it forward-conducts on reversed leads and takes the supply's full current.
- **Impact:** Unspecified input cap means the 24 V case can ring past 28 V on hot-plug (Eq. 24), and a hot-plug edge can exceed 100 V/µs.
- **Fix:** Specify ≥ 1 µF 50 V X7R at the eFuse IN (plus 0.1 µF close). If the TVS footprint ever gets fitted, use the bidirectional SMF15CA or note that it sacrifices reverse protection.
- **Confidence:** high (datasheet text); ringing magnitude unverified.
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** use the input capacitor

### R061 [Med] Power: bench OVLO (5.56–5.93 V) lets through voltages above the 5.5 V recommended maximum of LM66200, both TPS73701s and FT232H VREGIN, and above SCSI TERMPWR's 5.25 V
- **Evidence:** OV rising worst 5.93 V (above). LM66200 §6.3 VIN max 5.5 V (abs max 6 V). TPS737 §5.3 VIN max 5.5 V (abs max 6.0 V; V_OUT abs max 5.5 V). FT232H DS v2.0 Table 5.2 VREGIN (5 V mode) 3.6–5.5 V. SCSI-2 §5.4.3 VTerm 4.25–5.25 V; TERMPWR follows +5V_SYS minus ~50 mV. The OVLO response itself is fine: 1.2 µs (§6.6), and a hot-plugged 12/24 V adapter trips OVLO long before the dVdt ramp moves OUT.
- **Impact:** A bench supply at 5.5–5.9 V runs four parts outside their recommended range, leaves 70 mV to U1's and the LDOs' 6 V abs max, and puts up to ~5.9 V on TERMPWR. Not immediate damage; a spec-margin error in the "5.5 V bench setting is fine" claim.
- **Fix:** Lower OV to ≈ 5.40 V nominal (e.g. R3 up to ~160 k with R1/R2 re-trimmed; worst case ≈ 5.25–5.56 V), and state in USAGE.md "set the bench supply to 5.0–5.1 V". Or accept and document that 5.5 V is the absolute top setting and 5.0 V is the intended one.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** 5.0-5.1 is achievable w/ bench supply.

### R062 [Med] Power: TERMPWR eFuse OVLO pin is driven to 3.3 V (recommended range 0.5–1.5 V)
- **Evidence:** SLVSFC9C §6.3: V_OVLO **0.5–1.5 V** recommended; §6.1 abs max 6.5 V. §6.5 I_OVLKG ±0.1 µA is specified only for 0.5 V < V_OVLO < 1.5 V. The enable node is pulled to 3.16–3.44 V (10 k to 3.3 V) when off. TI does allow logic drive in prose: pin table "can also be used as an Active Low Enable", §8.1.1 "EN/UVLO or OVLO can also be driven from the host GPIO". Low side: the node sits at 0–0.7 V (LM393 V_OL ≤ 0.4 V at 25 °C, ≤ 0.7 V over 0–70 °C, onsemi LM393/D p.3); §6.5 is characterised with V_OVLO = 0 V, so low is fine and 0.7 V < V_OV(F) min 1.076 V.
- **Impact:** Inside abs max, outside recommended; leakage in the high state is unspecified (the 10 k pull-up makes that irrelevant). Unlikely to fail, but it's the only non-datasheet operating point on the TERMPWR path.
- **Fix (if strict compliance wanted):** feed OVLO from the node through a divider that lands in 1.25–1.5 V at 3.16–3.44 V, e.g. 14.3 k over 10 k (ratio 0.412 → 1.30–1.42 V high, ≤ 0.29 V low). The node itself stays at 3.3 V for the expander and LED. Otherwise ask TI (E2E) and accept.
- **Confidence:** high on the numbers; the practical risk is low.
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** divider sgtm

### R063 [Info] Power: TERMPWR eFuse settings recomputed
- **Evidence:** EN/UVLO 39 k/15 k: 1.20 × 54/15 = **4.32 V rising (4.20–4.47 V)**, falling 3.92 V nom (**3.82–4.08 V**). EN pin at 5.93 V in = 1.65 V (< 5 V recommended). R_ILM 2.4 k + 330 = 2730 Ω → 3334/2730 = **1.22 A**; using the nearest datasheet row (3.32 kΩ: 0.850/1.007/1.150 A, −15.6 %/+14.2 %) plus 1 % R: **1.02–1.41 A** (NOTES 1.06–1.39 A used a narrower interpolation; both satisfy ≥ 0.9 A and ≤ 1.5 A). Recovering from OVLO bypasses dVdt: confirmed, §7.3.3 "While recovering from a OVLO event, the TPS259470x variants bypass the inrush control (dVdt) and start up in a current limited manner", t_SWOV 90 µs (§6.6). Reverse blocking when unpowered: I_REVLKG(OFF) ≤ 4.86 µA at V_OUT = 12 V, V_IN = 0 (§6.5). Short-circuit: fast trip at 2 × I_LIM then foldback limit below V_OUT 1.9 V (§7.3.5.3 note 2, §6.5 V_FB). R_ILM node must stay < 50 pF (§7.3.6 note): layout.
- **Confidence:** high.

### R064 [Low] Power: TERMPWR eFuse FLT goes low whenever another device's TERMPWR is higher than ours (reverse-current blocking)
- **Evidence:** SLVSFC9C Table 7-3: "Reverse Current ((V_OUT − V_IN) > V_REVTH) → Reverse Current Blocking, FLT **L**". V_REVTH −22.3 to −36.5 mV (§6.5). Another initiator (e.g. the G4's Adaptec, or a target that supplies TERMPWR) at 5.0 V while our USB-fed +5V_SYS sits at 4.6 V triggers it.
- **Impact:** TERMPWR_FLT_N reports a "TERMPWR fault" that is really "someone else is supplying more". Firmware would mis-diagnose.
- **Fix:** Firmware rule: FLT low with TERMPWR_OK high and no over-temperature symptoms = reverse blocking, not a short. Document it in NOTES next to the existing "ignore FLT for a few ms after enable" rule.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R065 [Low] Power: our TERMPWR sink current can exceed SCSI-2's 1.0 mA while our board is on but TERMPWR is disabled
- **Evidence:** SCSI-2 rev 10L §5.4.3: "SCSI devices shall sink no more than 1,0 mA from TERMPWR … except to power an optional internal terminator" (so the 2.80 V LDO is exempt). Non-terminator loads on our TERMPWR node: present-LED (5.25 − ~1.7 V)/6.8 k ≈ 0.52 mA (0.56 mA at 5.5 V); TERMPWR_OK divider 5.25/55 k = 0.095 mA; SMF6.0A leakage (I_R ≤ 400 µA at 6.0 V V_RWM, smf6.0a.pdf p.2; much less at 5.25 V, unverified); eFuse OUT leakage **I_OUTLKG(OVLO) 319/443 µA** when disabled by OVLO with V_OUT > V_IN, or I_OUTLKG(RCB) 234 µA when on and reverse-blocking (SLVSFC9C §6.5). Worst: 0.52 + 0.10 + 0.44 ≈ **1.06 mA + TVS leakage**. With our board off: 0.52 + ~0.2 (divider into the unpowered expander, see next entry) ≈ 0.72 mA, OK.
- **Impact:** A paper violation only in the "we're powered, we're not supplying, someone else is" case; no functional effect on a bus that has a ≥ 900 mA supplier.
- **Fix:** Raise the LED resistor to ~10 k (≈ 0.35 mA; still visible with a high-efficiency red) or drive the present-LED from our 3.3 V rail via the TERMPWR_OK signal. Update NOTES' "total ≤ 0.61 mA" to include the eFuse and TVS leakage.
- **Confidence:** high on datasheet numbers; TVS leakage at 5.25 V unverified.
- **Owner decision:** approved (2026-09-26)

### R066 [Med] Power: TERMPWR_OK can read HIGH with TERMPWR absent; the TCA9555 pull-up is not 100 kΩ worst case
- **Evidence:** TCA9555 SCPS200E §7.5: P-port I_IL (V_I = GND) up to **−100 µA** (no min/typ), i.e. the internal pull-up can be as low as ~33 kΩ at 3.3 V. V_IL max = 0.3 × V_CC = 0.95–1.03 V (§7.3). Divider 22 k (to TERMPWR) / 33 k (to GND).
  - TERMPWR held at 0 V: node = 3.3 × 13.2 k/(13.2 k + R_pu) = 0.39 V (R_pu 100 k, NOTES' figure) but **0.94 V** at R_pu 33 k: ~10–90 mV from V_IL.
  - TERMPWR **floating** (nobody supplies it; the line only sees our disabled eFuse OUT, the TVS, the LDO input and the reverse-biased LED): node = 3.3 × 33/(33 + R_pu) = 0.82 V (100 k) to **1.65 V** (33 k), i.e. reads HIGH = "TERMPWR present".
  - High side is fine: 4.25 V → ≥ 2.55 V vs V_IH 2.41 V at 3.44 V.
- **Impact:** Firmware may report "TERMPWR present" on a dead bus, which is exactly the case TERMPWR_OK exists to diagnose.
- **Fix:** Lower the divider impedance (e.g. 10 k/15 k: 6 k Thevenin → ≤ 0.6 V floating-worst; TERMPWR draw 0.21 mA, then trim the LED so the total stays < 1 mA), or add a 100 k pull-down from TERMPWR to GND, or use the spare ADC-capable GPIO (NOTES already suggests it) instead of the expander.
- **Confidence:** med (depends on the actual TCA9555 pull-up, which TI only bounds by I_IL).
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** it does seem like we wound up with a spare ADC-capable GPIO pin, so hook that up to TERMPWR through an appropriate divider.

### R067 [Low] Power: TERMPWR_OK divider back-feeds ~0.2 mA into the unpowered 3.3 V rail
- **Evidence:** Board off, another device supplies TERMPWR at 5 V: 22 k into P05; the P-port has clamp paths to V_CC (TCA9555 §7.1 I_IOK for V_O > V_CC). Node clamps near 0.6 V: (5 − 0.6)/22 k ≈ 200 µA, minus ~18 µA in the 33 k → **~180 µA into the dead 3.3 V rail** through the expander.
- **Impact:** A partly-powered 3.3 V rail (few hundred mV; could approach the TCA9555's 1.2–1.5 V POR if the rail's other loads are light). No damage (I_IOK limit ±20 mA), but a classic source of odd power-up states.
- **Fix:** Same as above (ADC pin with a larger divider, or a small FET/comparator), or a series resistor large enough that the clamp current is < 10 µA.
- **Confidence:** med (clamp structure inferred from I_IOK).
- **Owner decision:** approved (2026-09-26)

### R068 [Med] Power: "bench present enables TERMPWR" can draw TERMPWR from a Default-current USB port
- **Evidence:** LM66200 SLVSG04 §7.3.1 truth table: V_IN1 > V_IN2 → VOUT = VIN1 (USB) with ON low. The bench-present 2N7002 is driven from the bench eFuse **output**, which is live whenever the bench supply is valid, regardless of which U1 input actually supplies +5V_SYS. USB VBUS may be 4.75–5.5 V (Type-C vSafe5V, unverified here) and a bench at 5.0 V can be lower. Standby conditions in §6.5 ("VIN2 > VIN1 + 0.2 V", "VIN1 > VIN2 + 0.1 V") suggest the switchover is not defined for near-equal inputs.
- **Impact:** Bench 5.0 V + a 5.1 V Default (500/900 mA) USB port → U1 selects USB, TERMPWR is enabled by "bench present", and up to 0.5 A logic + 0.9–1.41 A TERMPWR is drawn from a 500 mA port: host over-current shutdown or brown-out. The same happens at equal voltages if U1 dithers.
- **Fix:** Enable TERMPWR on "bench actually in use", i.e. U1's ST: ST is open-drain and pulls **low** when VIN2 (bench) powers VOUT (§7.3.3), so ST can join the wired-OR node directly (ST abs max 6 V, V_OL ≤ 0.1 V at 1 mA; also low on a U1 fault, which is harmless). PWR_SRC then reads the same node, so keep a separate copy if firmware needs it. Also tell users to set the bench ≥ 0.3 V above USB, or unplug USB power, when bench-powering.
- **Confidence:** high on the logic; switchover hysteresis unverified.
- **Owner comment:** we would never unplug USB when bench-powering, that's our data port as well. the bench power should just supply additional juice. I also wouldn't set bench > 0.3V above USB, because of the note above about 5.0-5.1V.

### R069 [Med] Power: TERMPWR minimum on a USB 1.5 A port lands right at SCSI-2's 4.25 V; eFuse UVLO rising can exceed a sagging VBUS
- **Evidence (Type-C figures unverified; from memory of the USB Type-C spec):** source vSafe5V min 4.75 V; cable IR drop budget ≤ 500 mV on VBUS (+ 250 mV on GND) at the cable's rated 3 A → ≈ 0.25 Ω round trip. At the board's worst 1.4 A: 4.75 − 0.35 = **4.40 V** at the receptacle. Then U1 R_ON 55 mΩ (−40–85 °C, LM66200 §6.5) × 1.4 A = 77 mV → 4.32 V; eFuse R_ON ≤ 45 mΩ (§6.5) × 0.9 A = 41 mV (plus V_FWD regulation 4.7–16.9 mV at light load); jumper/traces ~20–30 mV → **≈ 4.23–4.26 V** vs SCSI-2 §5.4.3 4.25 V min. Separately, TERMPWR eFuse UVLO **rising** is up to 4.47 V worst: with a 4.75 V source and a long cable already carrying ~0.5 A of logic, +5V_SYS ≈ 4.55–4.6 V, which clears it, but a source at the low end of a sloppy 5 V can leave TERMPWR off (falling threshold 3.82–4.08 V is fine once on).
- **Impact:** Worst-case compliant source + worst-case cable + full terminator load sits ~0–20 mV under the 4.25 V TERMPWR minimum. The terminators themselves still work (2.8 V LDO needs ~3.0 V), so this is a spec margin, not a functional failure.
- **Fix:** Measure TERMPWR at the connector under full load at bring-up with a long cable; document "use a short C-to-C cable or bench power for full compliance". Lowering UVLO to ~4.0 V rising (e.g. 39 k/16.9 k, not a must) removes the start-up risk.
- **Confidence:** med; Type-C voltages/IR drop must be verified against the spec text.
- **Owner comment:** I think keep UVLO as it is. We're going to hook TERMPWR up to an ADC so we can easily measure this and warn. In practice it should be ok, I use quality C-to-C cables

### R070 [Low] Power: TERMPWR maximum exceeds SCSI-2's 5.25 V whenever the source is above ~5.3 V
- **Evidence:** SCSI-2 §5.4.3 VTerm ≤ 5.25 V. TERMPWR ≈ +5V_SYS − (10–50 mV). USB VBUS may be up to 5.5 V (Type-C vSafe5V max, unverified; USB 2.0 host port 5.25 V) and the bench path passes up to 5.93 V (see the OVLO entry).
- **Impact:** Terminators and targets see up to ~5.5–5.9 V. Harmless for regulated active terminators; outside the letter of the spec.
- **Fix:** Document; the OVLO fix above bounds the bench case.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R071 [Info] RP2350: QFN-80 pin numbers, GPIO functions and PIO windows all check out
- **Evidence:** `5-rp2350-pinout.md` compared pin by pin with `rp2350-datasheet.pdf` §1.2.1.2, Figure 3 (p.16) and Table 1427/1430 (§14.8.2.2). All 80 pin numbers and names match: IOVDD 5/15/24/29/41/50/60/76, DVDD 10/32/51, ADC_AVDD 59, USB_OTP_VDD 68, QSPI_IOVDD 69, VREG_AVDD/PGND/LX/VIN/FB 61–65, USB_DM/DP 66/67, QSPI 70–75, XIN/XOUT 30/31, SWCLK/SWDIO/RUN 33/34/35. Function table (Table 645, pp.589–592): every GPIO 0–47 has PIO0/PIO1/PIO2 on F6/F7/F8; GPIO 36 = I2C0 SDA and GPIO 37 = I2C0 SCL (the right way round); QMI CS1n (F9) on GPIO 0, 8, 19 and 47 only. PIO0 at base 0: inputs 0–17, outputs 18–26, ACK side-set 29, `wait pin 16` = REQ, C/D (15) usable as JMP_PIN; all inside 0–31. PIO1 at base 16: MIOSIO 32–35, SCLK/SS_n 41/42 (consecutive, so a 2-pin side-set works), MISO 43; all inside 16–47. PIO2 at base 16: SD CLK/CMD/D0 38/39/40, the same CLK-CMD-D0 order as BlueSCSI's RP2350 SDIO (`sdio_rp2350_config.h`). After the 8-bit rework, MIOSIO0–7 = GPIO 32–39, consecutive. RUN has an internal pull-up (Table 1430), so no external one is needed.
- **Impact:** none.
- **Confidence:** high.

### R072 [Low] RP2350: pinout page omits the exposed pad (the chip's only GND)
- **Evidence:** RP2350 datasheet Figure 3 / Table 2: "GND: Single external ground connection, bonded to a number of internal ground pads". The QFN-80 has no GND pins; ground is only the ePad. `5-rp2350-pinout.md` lists pins 1–80 and never mentions the pad.
- **Impact:** a hand-made KiCad symbol or footprint without pin 81/EP would leave the chip unground. The regulator layout (§6.3.8.1) also needs PGND and CIN/CFILT vias straight into that pad.
- **Fix:** add "EP (81): GND, via array; VREG_PGND and CIN/CFILT return here per §6.3.8.1" to the page.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R073 [Low] RP2350: the CS1 "re-pad" erratum is E14, not E15, and it only affects A2 silicon
- **Evidence:** NOTES "GPIO budget" table: "erratum RP2350-E15: firmware must re-pad CS1 when it isn't on GPIO 0". In the datasheet (Appendix E, p.1359): **E14** = "bootrom connect_internal_flash() always uses pin 0, ignoring any configured FLASH_DEVINFO CS1", affects **A2 only**, fixed in the A3 bootrom. **E15** is about `otp_access()` page 62/63 permissions (unrelated). pico-sdk handles CS1 itself: `gpio_set_function(47, GPIO_FUNC_XIP_CS1)` clears ISO, and `hardware_flash/flash.c` saves and restores the QMI M1 (CS1) setup around every flash erase/program (`flash_rp2350_save_qmi_cs1` / `restore`, or a user `flash_set_qmi_cs1_setup_function()`).
- **Impact:** doc only. One real A2 corner case: if FLASH_DEVINFO in OTP ever names a CS1 device, an A2 bootrom configures the pads for **GPIO 0**, which is our DB0 receiver input. The QMI would then drive a pin that a 74LVC1G17 is also driving.
- **Fix:** correct the erratum number. Add a firmware note: never program FLASH_DEVINFO CS1 in OTP (not needed; the app configures the PSRAM), and use `flash_set_qmi_cs1_setup_function()` so the PSRAM timing survives flash writes.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R074 [Med] Power: USB VBUS hot-plug ringing can exceed U1's 6 V abs max; the SMF6.0A doesn't start clamping until 6.67–7.37 V
- **Evidence:** LM66200 §6.1 VIN1 abs max **6 V**. SMF6.0A (smf6.0a.pdf p.2): V_RWM 6.0 V, V_BR **6.67–7.37 V** at 10 mA, V_C 10.3 V at 19.4 A. VBUS goes straight into U1 VIN1 with only ceramic capacitance (TI recommends ~1 µF, LM66200 §9). An LC hot-plug (cable inductance + low-ESR MLCC) can ring toward 2 × VBUS (general TI hot-plug guidance; magnitude unverified for our cable/source). Any TVS that stands off 5.5 V breaks down above 6 V, so no TVS can protect a 6 V part here.
- **Impact:** Occasional over-stress of U1 on USB plug-in; failures would be intermittent and hard to trace.
- **Fix (pick one):** add damping on VBUS: a 4.7–10 µF polymer/tantalum or an MLCC with a ~0.5–1 Ω series R, keeping total VBUS capacitance ≤ 10 µF; or put the USB path through the TPS259470A as well (28 V abs max, and it adds OV protection). Scope VBUS at U1 during plug-in at bring-up either way.
- **Confidence:** med.
- **Owner decision:** approved (2026-09-26)

### R075 [Info] Power: LM66200 U1 ST, ON, inrush and VBUS capacitance
- **Evidence (SLVSG04):** ST is open-drain (§7.3.3), high = VIN1 (USB), low = VIN2 (bench) **or a fault**; V_OL ≤ 0.1 V at 1 mA; the TCA9555's internal pull-up is enough (no external pull-up needed; ST abs max 6 V). ON has V_ON 0.8/1.0/1.2 V (§6.5), so ON = GND is solidly "on". (NOTES "Ideal diodes" says ON thresholds "aren't in the datasheet": they are; moot now that U2 is gone.) Soft start (§7.3.2) runs whenever an input appears with VOUT < 1 V: t_SS 1.7 ms typ at 5 V (typ only, no min). Inrush = C × V / t_SS: 47 µF → ~140 mA; 100 µF → 294 mA (TI's example, §8.2.2). With soft start, only U1's VIN1 cap + the TVS sit directly on VBUS, so the USB 10 µF rule is easy: keep VIN1 ≤ ~4.7 µF. Switchover (no soft start) takes ~8 µs at 5 V. Dissipation 1.4 A² × 55 mΩ ≈ 0.11 W, θ_JA 111.5 °C/W → +12 °C.
- **Confidence:** high; t_SS spread unverified.

### R076 [Info] RP2350: E9 mitigation is correct, the firmware rule really matters, and E9 is fixed on A3/A4 silicon
- **Evidence:**
  - Reset state: datasheet Table 853 (PADS_BANK0 GPIO0, p.787): ISO = 1, OD = 0, **IE = 0**, DRIVE = 4 mA, PUE = 0, **PDE = 1**, SCHMITT = 1. The NOTES claim "PDE = 1, ISO = 1, IE = 0" is right (the table number is 853 in this edition). E9 text (p.1367): "This doesn't affect the pull-down behaviour of the pads immediately following a PoR or RUN reset because the input enable field is initially clear."
  - E9 workaround (p.1368): clear IE, or "an external pull-down of 8.2 kΩ or less". 4.7 kΩ at the gate plus 100 Ω series gives 4.8 kΩ at the pin. That meets it. At the ~120 µA leakage figure the pad would sit ≈ 0.58 V, but the datasheet says a ≤ 8.2 kΩ pull "will drive the voltage below the level where the leakage current occurs", so it doesn't stay there.
  - pico-sdk (master) `gpio_set_function()` does `hw_write_masked(&pads_bank0_hw->io[gpio], PADS_BANK0_GPIO0_IE_BITS, IE|OD)`, i.e. it **sets IE = 1**, then clears ISO. `pio_gpio_init()` just calls `gpio_set_function()`. So every gate pin handed to PIO or SIO comes up with IE = 1 and, until the SM sets its pindir, output disabled. That's exactly the E9 condition. The firmware rule ("clear IE on all 14 gates") is needed, and the order should be: preset PIO pin values and pindirs to 0/out (`pio_sm_set_pins_with_mask` + `pio_sm_set_pindirs_with_mask`) → `pio_gpio_init()` → clear IE.
  - **Stepping:** E9 "Affects RP2350 A2", "Fixed by RP2350 A3" (Appendix C, p.1354: "The pad circuit is modified to eliminate the erroneous leakage path"). A4 is the current stepping (CHIP_ID.REVISION 0x8). Parts bought from JLC in late 2026 are probably A4, so E9 probably doesn't apply. Unverified: check the package marking or `rp2350_chip_version()` at bring-up. Keeping the 4.7 kΩ costs nothing and covers A2.
  - Only the 14 gate pins are exposed. The other inputs are driven by push-pull parts (1G17, FT232H) or have ≤ 10 kΩ pull-ups (I²C, SDIO, CS1, INT), so E9 at worst biases a floating input, harmlessly.
- **Impact:** none if the rule is followed.
- **Confidence:** high.

### R077 [Info] RP2350: full errata sweep (E1–E28): only E12, E11, E27, E5/E8 and E2 touch this design, all firmware-only
- **Evidence:** datasheet Appendix E (pp.1357–1376) and Appendix C (steppings):
  - **E12 (USB, all steppings):** status signals mis-synchronised unless clk_sys ≥ 1.1 × clk_usb (≥ 52.8 MHz). We run at 150 MHz. OK; just never down-clock clk_sys below ~53 MHz while USB is live.
  - **E11 (XIP, all):** cache "clean by set/way" re-tags dirty lines, so PSRAM data can alias flash. Use the SDK `xip_cache_clean_all()`, or do DMA to the PSRAM's uncached alias (0x15xx_xxxx), never hand-rolled cache maintenance.
  - **E27 (bus fabric, all):** BUS_PRIORITY bits are mis-wired on the APB and FASTPERI arbiters. If firmware raises DMA priority to keep PIO FIFOs served, the effect at the peripheral arbiter isn't what the register name says. Prefer SRAM striping and avoid polling peripherals.
  - **E5, E8 (DMA, all):** CHAIN_TO fires after ABORT or on zero-length transfers. Relevant to ring-buffer chains for the SCSI/FT1248 streams: clear EN on both channels before ABORT; never trigger zero-length.
  - **E2 (SIO spinlocks, all):** the SDK already uses software locks on RP2350.
  - **E9 (A2), E14 (A2), E10 (A2, UF2 with partition tables), E16 (A2, USB_OTP_VDD disruption corrupts OTP reads), E19 (A2):** fixed in A3/A4.
  - Not relevant: E1 (interpolator), E3 (QFN-60 only), E4/E6/E7 (Hazard3 RISC-V), E13/E15/E17/E18/E20–E26/E28 (secure boot, OTP, bootrom glitching).
  - There are **no PIO or ADC errata** in this edition (29 July 2025).
- **Impact:** none on hardware.
- **Fix:** carry the E12/E11/E27/E5/E8 notes into Phase 4 firmware notes.
- **Confidence:** high.

### R078 [Med] RP2350: VREG_AVDD and USB_OTP_VDD have a 3.135 V minimum; the 3.3 V rail's worst case leaves ~20 mV
- **Evidence:** RP2350 datasheet Table 1441 (§14.9.5, pp.1343–1344): VREG_AVDD 3.135–3.63 V, USB_OTP_VDD 3.135–3.63 V (IOVDD and QSPI_IOVDD go down to 1.62 V, so they're fine). §6.3.7 says the same for VREG_AVDD. NOTES "Resistor and small-part values": the 3.3 V LDO (TPS73701, 47 k / 27 k) is 3.300 V nominal, but **3.16–3.44 V on legacy silicon (±3 %)**. VREG_AVDD then loses another 33 Ω × ~0.2 mA ≈ 7 mV in its filter, plus PCB IR drop and load-step dips on a rail shared with the FT232H, CH334, 18 × 1G17 and the SD card.
- **Impact:** at the low corner, VREG_AVDD ≈ 3.15 V leaves ~15 mV to the minimum before any ripple, so the chip would run outside its spec. On A2 silicon, E16 also says USB_OTP_VDD disruption can corrupt OTP reads. Probably works on a real part; not guaranteed.
- **Fix (no new parts):** centre the rail higher, e.g. 3.35–3.40 V. With R2 = 27 k, R1 = 48.7 k (E96, C-number to check) gives 1.204 × (1 + 48.7/27) = 3.376 V, so 3.27–3.48 V at ±3 %. That stays under every 3.6 V/3.63 V ceiling on the rail: RP2350 3.63, APS6404L 3.6, W25Q128JV 3.6, FT232H VCCIO 3.63 (FT232H limit unverified; check DS_FT232H). Or accept it and measure at bring-up, as NOTES already plans.
- **Confidence:** high on the limits; the rail tolerance comes from the NOTES, not re-derived.
- **Owner decision:** approved (2026-09-26)

### R079 [Med] RP2350/PSRAM: the 10 kΩ CS1 pull-up doesn't guarantee APS6404L VIH against the RP2350's reset pull-down
- **Evidence:** at reset, GPIO 47 has its pull-down on (Table 1427 "Reset State: Pull-Down"; Table 853 PDE = 1). RP2350 pull-down resistance is 36–113 kΩ at IOVDD 3.3 V (§14.9.4 GPIO DC table, p.1342). With 10 kΩ up: CS1 = 3.3 × 36/46 = **2.58 V** worst case (2.99 V typical at ~70 kΩ). APS6404L Table 9 (p.22): **VIH min = VDD − 0.4 V = 2.9 V** at 3.3 V (2.76 V at 3.16 V). The PSRAM's CE# is therefore in its undefined band from power-up until firmware sets GPIO 47 to XIP_CS1. During that window the bootrom reads flash on the shared SD lines. A PSRAM that decodes the 03h/EBh reads as its own would drive SIO1/SO against the flash. The guide's R13 (10 kΩ) and common boards work in practice, because real CMOS thresholds sit near VDD/2.
- **Impact:** a spec-margin risk of garbled boot reads, most likely on a hot, low-rail unit. It would be hard to diagnose.
- **Fix:** fit **3.3 kΩ** (C25890, already on the BOM, basic): 3.3 × 36/39.3 = 3.02 V ≥ 2.9 V, and 2.90 V at a 3.16 V rail ≥ 2.76 V. It costs ≤ 1 mA while CS1 is asserted, which is nothing. Or, as a firmware-only measure, configure GPIO 47 early in boot. That doesn't help during the bootrom, though.
- **Confidence:** med. The numbers are datasheet limits; whether a real APS6404L misbehaves at 2.6 V is unknown.
- **Owner decision:** approved (2026-09-26)

### R080 [Info] RP2350: core regulator, crystal, flash, BOOTSEL/RUN match the datasheet and "Hardware design with RP2350"
- **Evidence:**
  - Inductor: datasheet §6.3.8.2 (p.455) requires fully shielded, 3.3 µH ±20 %, DCR ≤ 250 mΩ, Isat ≥ 1.5 A, polarity-marked, and names the AOTA-B201610S3R3-101-T; the guide §2.1 uses it too. Abracon datasheet (Rev A, 9/13/2024): 3.3 µH ±20 %, DCR 115 typ / 140 max mΩ, Isat 2.8 typ / 2.4 A (the lower column), Irms 2.3/2.1 A, white-ink polarity dot, "Approved for use with Raspberry Pi's RP235x". All met. The footprint must carry the dot per Figure 23/25 (NOTES already says so).
  - Crystal: guide §4 and §4.1 name the ABM8-272-T3 (CL 10 pF, ESR ≤ 50 Ω) with 2 × 15 pF and a 1 kΩ series resistor at IOVDD = 3.3 V. That's the same circuit here.
  - Flash: W25Q128JVSIQ is the guide's part. Its "IQ" suffix ships with QE = 1 (the W25Q128JV datasheet says QE = 0 is the factory default only for "IM"/"JM"), so quad XIP works out of the box. QSPI_SS pull-up DNF, as the guide does for this flash.
  - BOOTSEL: QSPI_SS → 1 kΩ → button, per the guide. RUN: internal pull-up (Table 1430), so no external one; 1 kΩ in series with the button, per the guide.
  - Decoupling: 8 IOVDD + 3 DVDD + ADC_AVDD + one shared USB_OTP_VDD/QSPI_IOVDD, as in the guide's Appendix B.
- **Impact:** none.
- **Confidence:** high.

### R081 [Low] RP2350: regulator caps; DC-bias derating of CIN, and the datasheet's recommended second DVDD 4.7 µF is missing
- **Evidence:**
  - §6.3.8.2: "CIN should be at least 4.7 µF … ≤ 50 mΩ"; "COUT must be 4.7 µF ±20 %". The plan is 3 × 4.7 µF X5R 10 V 0402 (C23733). The guide's own C9 is also 4.7 µF 0402 X5R (6.3 V), so this matches the reference. Typical 0402 4.7 µF 10 V X5R curves (not in `reference/`; **unverified**) keep ~45–55 % at 3.3 V (CIN ≈ 2.1–2.6 µF effective) and ~80–85 % at 1.1 V (COUT ≈ 3.8–4.0 µF, just inside −20 %).
  - §6.3.8.1, last bullet: "In addition to COUT, for best performance we recommend a second 4.7 µF capacitor on the VOUT net, located on the bottom edge of the package … Don't place this near LX/COUT." Datasheet Figure 19 shows **four** 4.7 µF (CIN, COUT, VREG_AVDD filter, DVDD). The parts list has three.
- **Impact:** regulator transient margin only. Pico 2 ships with the same 0402 parts.
- **Fix:** add a 4th 4.7 µF (C23733) on a DVDD pin away from LX. For the QFN-80 that's pin 32 (bottom edge) or pin 10; the datasheet's "pin 23" is the QFN-60 numbering. If layout allows, use the 0603 16 V C19666 for CIN (less derating).
- **Confidence:** high on the datasheet text, low on the derating numbers.
- **Owner decision:** approved (2026-09-26)

### R082 [Info] Power: TPS73701 feedback values recomputed
- **Evidence (SBVS067W §5.6, Fig. 6-2):** V_OUT = 1.204 × (R1 + R2)/R2. 47 k/27 k → **3.2999 V**; 20 k/15 k → **2.8093 V**. V_FB (DCQ, 25 °C) 1.198/1.204/1.210 V; overall ±3 % legacy / ±1.5 % new silicon, **excluding** resistor tolerance (note 4) and **tested at V_OUT = 1.2 V** (note 3, i.e. with no divider). With 1 % resistors: 3.3 V → 3.16–3.44 V (legacy), 3.21–3.39 V (new); 2.80 V → 2.69–2.93 V (legacy). These match NOTES. C_FF optional, ≤ 0.1 µF (§6.3.1). Dropout: 130 mV typ but **500 mV max at 1 A legacy** / 250 mV new (§5.6); at 0.45 A that's ≤ ~0.23 V, so the 3.3 V rail holds down to ~3.7 V in and the terminator LDO down to ~3.0 V. Current limit ≥ 1.05 A.
- **Confidence:** high.

### R083 [Low] Power: the 2.80 V divider (20 k/15 k, R1‖R2 = 8.6 k) ignores TI's "R1‖R2 ≈ 19 kΩ" rule; FB current adds up to ~±15 mV
- **Evidence:** SBVS067W §7.2.1: "For best accuracy, make the parallel combination of R1 and R2 approximately equal to 19 kΩ … helps compensate for leakages into the error amplifier terminals." I_FB 0.1 typ / **0.6 µA max** (§5.6), and the ±3 % spec was tested without a divider. Uncompensated part ≈ 0.6 µA × (19 k − 8.6 k) × (R1+R2)/R2 ≈ **±15 mV** at the output → 2.80 V rail worst case ≈ 2.68–2.94 V. The 3.3 V divider (R1‖R2 = 17.2 k) is close enough (~±3 mV).
- **Impact:** Eats most of the 20 mV headroom under 2.96 V, and pushes the low end further below the SN74LVTH245A's 2.7 V V_CC minimum that another reviewer already flagged.
- **Fix:** Same ratio at higher impedance: **36 k / 27 k** (4:3, R1‖R2 = 15.4 k; 27 k is already on the board, C25771; check 36 k's JLC tier), or TI's own 44.2 k / 33.2 k (2.807 V, R‖ = 19 k).
- **Confidence:** med (sign and compensation of I_FB are not specified).
- **Owner decision:** approved (2026-09-26)

### R084 [Low] Power: TPS73701 EN pins are not specified; define them
- **Evidence:** SBVS067W pin table: "EN must not be left floating and can be connected to IN". §6.3.3: with EN tied to IN, "for VIN ramp times slower than a few milliseconds, the output can overshoot upon power up", and the gate may stay enhanced after VIN is removed. Our VIN ramps are slow: bench dVdt 3–15 ms; LM66200 soft start ~1.7 ms. TI's own slow-ramp plots (Fig. 7-7/7-8, 50 ms/div, EN presumably tied to IN) show no visible overshoot. Reverse current: none once EN is low; for the adjustable part "reverse current can flow when V_FB is more than 1.0 V above V_IN" (§6.3.4), which only happens briefly at power-down (3.3 V caps back into a collapsing +5V_SYS) and is harmless.
- **Impact:** A few-percent overshoot on the 3.3 V rail would hit the CH334's 3.4 V operating limit (abs max 4.0 V) first.
- **Fix:** Tie each EN to its IN through a divider that crosses 1.7 V only once VIN ≳ 3.8–4.0 V (e.g. 100 k over 75 k: EN = 0.43 × VIN; EN ≤ 2.5 V at 5.93 V), which also gives a clean UVLO. Scope both rails at power-up on bench and USB.
- **Confidence:** med (overshoot magnitude unverified).
- **Owner decision:** approved (2026-09-26)

### R085 [Low] Power: LDO thermal worst case is tighter than NOTES says (new-silicon θJA 76 °C/W, and V_IN up to 5.5–5.93 V)
- **Evidence:** SBVS067W §5.4/5.5: DCQ θ_JA **53.1 °C/W legacy, 76 °C/W new silicon** (JEDEC 2s2p, 3 × 3 in, single device; JLC doesn't let us choose the silicon). Terminator: (5.5 − 2.8) × 0.39 A = 1.05 W (1.22 W at a 5.93 V bench) → ΔT 56–80 °C (up to 93 °C). 3.3 V LDO: (5.5 − 3.3) × 0.45 A (with the corrected RP2350 figure below) = 0.99 W (1.18 W at 5.93 V) → ΔT 53–75 °C (up to 90 °C). NOTES used 5.25 V and implicitly 53 °C/W. At a 40 °C in-case ambient, new silicon, worst-case ceilings: T_J ≈ 115–133 °C, before the two SOT-223s heat each other; TI wants T_J ≤ 125 °C (§7.5.1.2). Typical (0.17 A logic, ~0.15 A average terminator load): ~0.35 W each, ΔT < 30 °C.
- **Impact:** Only the every-maximum-at-once ceiling is at risk, and thermal shutdown (160 °C) protects the part. Worth layout attention, not a redesign.
- **Fix:** Separate the two SOT-223s, give each ≥ ~2–3 in² of pour tied to inner ground with vias under the tab, and vent the case. The bench OVLO fix above also cuts the worst case.
- **Confidence:** high on the numbers; the real θ_JA of our board is unknown.
- **Owner decision:** approved (2026-09-26)

### R086 [Low] Power: terminator LDO at near-zero load: the ±3 % spec needs I_OUT ≥ 10 mA, and there's no pull-down
- **Evidence:** SBVS067W §5.6 accuracy is specified for 10 mA ≤ I_OUT ≤ 1 A. §7.2.2.3: "The TPS737 does not have an active pulldown … output overshoot of several percent if the load current quickly drops to zero"; decay τ = C_OUT × (80 k ‖ (R1+R2) ‖ R_LOAD) (Eq. 5). Bus idle (all lines released): our load is the 35 k divider (80 µA), so with e.g. 10 µF: τ ≈ 10 µF × 24 k ≈ 0.24 s. "Several percent" on 2.81 V is +60–140 mV, which is above 2.96 V for the time it takes the next assertion to pull it back. (Another reviewer already logged the related case of the rail being pumped by other drivers.)
- **Impact:** Brief terminator over-voltage after a bus-release; the "add a small bleed" note in NOTES is the right direction but needs a value.
- **Fix:** A bleed that takes ≥ 1–3 mA (1–2.7 kΩ, ~3–8 mW) keeps τ in the ms range and gets closer to the 10 mA accuracy condition. Scope at bring-up.
- **Confidence:** med.
- **Owner decision:** approved (2026-09-26)

### R087 [Low] Power: CC reference: CJ431 is 2.500 V nominal (not TL431's 2.495 V), comes in 0.5 % and 1 % ranks, and its tempco spec is 17 mV; worst-case margin shrinks from 15 mV to ~6–11 mV
- **Evidence:** cj431.pdf p.2: V_ref 2.475/**2.500**/2.525 V at I_KA = 10 mA; "Classification of V_ref": **0.5 % rank 2.487–2.513 V, 1 % rank 2.475–2.525 V** (the ordering table gives no way to pick the rank, so which one C3113 is is unverified); ΔV_ref over −25…85 °C 4.5 typ / **17 mV max**; I_KA(min) 0.45 typ / **1.0 mA max**; Z_KA ≤ 0.5 Ω. Our I_KA = (3.16 − 2.50)/510 − 2.5/18 k = **1.16 mA** at the low rail (1.7 mA at 3.44 V): above 1.0 mA, thin. Recomputed thresholds (Thevenin 0.6528 V via 13.3 k‖4.7 k = 3.47 k, 1 MΩ to the node): **nominal 0.662 V rising (node at 3.3 V) / 0.651 V falling (node at 0.1 V)**. Worst case with 1 % resistors, rail 3.16–3.44 V, node low 0–0.4 V, onsemi V_IO ±9 mV and I_IB ≤ 400 nA / I_IO ≤ 150 nA over 0–70 °C (LM393/D p.3), bias through 10 k + 5.1 k on the − input, and the full 17 mV tempco taken one-sided:
  - 0.5 % rank: rising 0.630–**0.689 V**, falling **0.620**–0.678 V → +10/+11 mV inside the 0.61/0.70 V window (TUSB321 V_TH_UFP_CC_MED 0.61/0.66/0.70 V).
  - 1 % rank: rising up to **0.692 V**, falling down to **0.617 V** → +6/+8 mV.
  - Both + inputs share the reference node, so up to 800 nA flows into 3.47 k (+2.8 mV); included as +1.4 mV above per input, still inside.
- **Impact:** Still works, with less margin than NOTES states. NOTES' "±0.8 % incl. tempco" and "2.495 V" should be corrected.
- **Fix:** Update the numbers; confirm the C3113 rank on the LCSC page or reel label; optionally raise the bias to ~1.5 mA min (430 Ω) for margin over I_KA(min).
- **Confidence:** high on datasheet values; tempco treatment conservative.
- **Owner decision:** approved (2026-09-26)

### R088 [Low] Power: keep capacitance off the CJ431 cathode
- **Evidence:** TL431-class shunts are conditionally stable: TI's TL431 datasheet stability-boundary figure shows an unstable band of load capacitance at mA-level cathode currents (not in the CJ431 sheet; the curve's exact band is unverified here). NOTES specifies no cap on the 2.5 V node, which is correct.
- **Fix:** Note in the schematic: "no decoupling on CJ431 cathode"; if the 0.65 V tap needs filtering, a cap on the tap (behind 13.3 k) is isolated from the shunt.
- **Confidence:** med.
- **Owner decision:** approved (2026-09-26)

### R089 [Info] Power: CC detection front end checked (LM393 range and levels, Rd, filter, ESD, cable cases)
- **Evidence:**
  - LM393 (onsemi LM393/D, 0–70 °C part): V_ICR 0 to V_CC − 1.5 V (25 °C) / V_CC − 2.0 V (0–70 °C). At V_CC ≈ 4.3 V that's 2.3 V > 2.04 V max CC on a 3 A port; note 10 also guarantees the right output state if one input leaves the range while the other (the 0.65 V reference) stays inside. Input abs max = V_CC (note 1): CC ≤ 2.04 V normally, and 10 k limits any fault current.
  - V_OL ≤ 400 mV at 4 mA (25 °C), ≤ 700 mV over temperature; actual sink ≈ 0.33 mA (10 k) + ~1.3 mA (LED via 1 k) ≈ 1.7 mA → node ≤ 0.4–0.7 V: below OVLO V_OV(F) min 1.076 V and the TCA9555 V_IL (0.99 V). 2N7002 (CJ): R_DS(on) ≤ 7 Ω at V_GS 5 V, gate 4.55 V from 10 k/100 k (3.35 V at the bench UV-fall of 3.69 V, V_th ≤ 2.5 V): OK.
  - Hysteresis from the shared node: when the bench FET or the other comparator pulls the node low, both comparators simply move to the lower (falling) threshold. Correct polarity (CC on −, positive feedback to +).
  - H7VL10B: I_R ≤ 0.2 µA at 7 V, C ≤ 20 pF (h7vl10b.pdf p.2): negligible at 0.65 V. The 10 k/1 µF sits behind the 5.1 k Rd; DC Rd is unchanged and τ = 10 ms ≪ tCCDebounce (100–200 ms, from memory).
  - VCONN never reaches a sink receptacle through a standard cable (the source applies it to the plug's Ra), so CC stays ≤ 2.04 V. Legacy A-to-C 56 k: 5 × 5.1/61.1 = 0.42 V → Default → no USB TERMPWR (as documented). No USB at all: CC = 0 → both comparators off, bench FET enables. 
- **Confidence:** high (Type-C timing from memory).

### R090 [Low] Power: a non-compliant A-to-C cable with a 10 kΩ pull-up reads as "3 A" and enables TERMPWR on a 500 mA USB-A port
- **Evidence:** 5 V × 5.1 k/(10 k + 5.1 k) = 1.69 V → above the 1.5 A threshold. Such cables exist (a known early-USB-C defect; unverified which are still around).
- **Impact:** ~1.4 A drawn from a USB-A port → host over-current shutdown / brown-out.
- **Fix:** USAGE.md: "use a C-to-C cable or the bench input". Firmware can't prevent it (the enable path is hardware by design), but can warn if PWR_SRC = USB and the enumerating host is USB-A (not detectable) — so documentation only.
- **Confidence:** med.
- **Owner decision:** approved (2026-09-26)

### R091 [Info] PSRAM: APS6404L-3SQR-SN limits vs our rail and the RP2350 QMI; the settings firmware needs
- **Evidence (aps6404l.pdf Rev 2.3):**
  - VDD 2.7–3.6 V (Table 9). The 3.16–3.44 V rail is inside.
  - Max clock (Table 10, ordering note): **109 MHz** for wrap-32 bursts at VDD 3.3 V ±10 %; **84 MHz** for linear bursts that cross a 1 KB page. §8.2: a linear burst "can cross page boundary one time only in a burst".
  - **tCEM (CE# low max) = 8 µs** for the standard grade (-SN is Tc −40…85 °C = standard; the 105 °C "X" part is 4 µs). tCPH (CE# high between bursts) ≥ 18 ns. tCSP 2.5 ns, tCHD 3.0 ns, tACLK 2–5.5 ns, tKOH ≥ 1.5 ns.
  - Commands: Quad Mode Enable **35h** (SPI mode only), QPI Fast Quad Read **EBh with 6 wait cycles**, QPI write 38h, reset 66h + 99h, power-up needs ≥ 150 µs with CE# high. Decoupling: 1 µF required plus optional 100 nF (§14.3). The BOM's 100 nF + 1 µF matches.
- **Evidence (RP2350 datasheet §12.14):** QMI chains sequential accesses into one CS-low transfer, broken by M1_TIMING.MAX_SELECT (units of 64 clk_sys) or PAGEBREAK. CS1 on GPIO 47 adds pad delay: 4.1 ns max vs 2.5 ns on QSPI pins, 2.1 ns max skew (Tables 1291/1292).
- **Recommended M1 setup at clk_sys = 150 MHz (a starting point; tune at bring-up):**
  - CLKDIV = 2 → SCK 75 MHz. That's under 84 MHz, so linear bursts may cross pages.
  - **PAGEBREAK = 1024**, because the part allows only one page crossing per burst and long DMA chains would cross many.
  - **MAX_SELECT = 18** (18 × 64 / 150 MHz = 7.68 µs < 8 µs). Recompute if clk_sys changes. That's ~280 bytes per select at 75 MHz.
  - MIN_DESELECT ≥ 3 clk (18 ns).
  - **RXDELAY ≈ 2** (half clk_sys steps). The round trip is ~2.5 (out) + 5.5 (tACLK max) + 1.5 (in) ≈ 9.5 ns, against a 6.7 ns half-period, so RXDELAY = 0 fails.
  - CS setup = half SCK (6.7 ns) − 1.6 ns GPIO47 extra delay ≈ 5 ns ≥ 2.5 ns OK. Use SELECT_SETUP only if SCK goes above ~100 MHz.
  - Init: send QPI-exit F5h first (the PSRAM stays in QPI across a RUN or watchdog reset, since it's not power-cycled), then 66h/99h, then 35h. Set CTRL.WRITABLE_M1.
- **Impact:** none on hardware; this is the firmware recipe.
- **Confidence:** high on datasheet numbers, med on the RXDELAY value (layout-dependent).

### R092 [Med] Firmware: QMI sharing; run the firmware from SRAM, keep SCSI DMA in SRAM, and never touch flash during a bus session
- **Evidence:**
  - **PSRAM bandwidth:** QPI at 75 MHz = 37.5 MB/s raw. With 14 clk overhead (2 cmd + 6 addr + 6 wait) per ≤ 280-byte select, sustained ≈ 34–36 MB/s for long sequential DMA. The target load is SCSI in 5 MB/s + FT1248 out 5 MB/s = 10 MB/s, ~30 % of the QMI. That's fine on paper.
  - **XIP miss cost:** an 8-byte line fill from flash in continuous-read mode ≈ 6 addr + 2 mode + 4 dummy + 16 data = 28 SCK ≈ 0.37 µs at 75 MHz. Add breaking a PSRAM chain (CS1 deselect ≥ 18 ns) and then restarting it (≈ 0.19 µs of command overhead charged to the stream). Code that misses often (ISRs, cold paths) sees 0.5–1 µs per miss, and more when several DMA channels queue at the QMI.
  - §4.4.3 (p.345): "QMI serial transfers force lengthy bus stalls on the DMA … stalling the DMA prevents any other active DMA channels from making progress". A DMA channel reading PSRAM therefore delays **every** other channel, including the PIO RX drains.
  - Flash erase/program disables XIP **and PSRAM** for the whole operation: W25Q128JV tSE (4 KB) 45 ms typical / 400 ms max, and the SDK's `flash_safe_execute` also masks interrupts.
  - Async SCSI and FT1248 are flow-controlled, so a stall only slows them. **Sync SCSI** (offset-based) and the **sniffer** are not: a PIO RX FIFO (8 words joined) holds only ~0.8 µs at 10 MB/s, so a DMA stall behind the QMI loses data.
- **Impact:** R3 throughput and the hard real-time bus-release deadlines (next finding) can't be met with code executing from flash under PSRAM traffic. A flash write mid-session freezes the SCSI engine for up to 0.4 s (2 s for a 64 KB block erase).
- **Fix (firmware):**
  - Build with `PICO_COPY_TO_RAM=1`. Code is probably ~100–150 KB, leaving ~350 KB of SRAM. Flash is then only boot and storage.
  - SCSI and sniffer DMA go into **SRAM** rings only. A second DMA stage (or the CPU) moves blocks SRAM ↔ PSRAM through the **uncached** alias.
  - For PSRAM → FT1248, prefer the XIP stream FIFO (STREAM_ADDR/CTR), which doesn't stall the DMA. Unverified that the stream works on the CS1 window.
  - No flash writes (logs, settings, A/B updates) while a SCSI session is open.
- **Is 520 KB SRAM alone a usable buffer?** Yes, as a fallback. ~256–320 KB of rings holds ~170–210 ms at 1.5 MB/s, or ~60 ms at 5 MB/s. That covers USB scheduling hiccups but not OS-level stalls; the PSRAM (8 MB ≈ 5.6 s at 1.5 MB/s) covers those.
- **Confidence:** med. The bandwidth figures are first-order estimates from datasheet cycle counts, not measured.
- **Owner decision:** approved (2026-09-26)

### R093 [Low] Power: 3.3 V budget: the RP2350 core row (80 mA max) should be ~115 mA; microSD max may be 200 mA
- **Evidence:** RP2350 datasheet §14.9.6 Table 1442: core regulator I_MAX 200 mA; efficiency at 200 mA, V_OUT 1.1 V, VREG_VIN 3.3 V = **59 %** → 0.22 W / 0.59 / 3.3 V ≈ **113 mA** from 3.3 V (more if firmware raises the core voltage for overclocking). SD cards: 100 mA is the default-speed limit, high-speed mode allows more (≈200 mA; from memory, unverified). Rows re-checked and OK: CH334 42 mA typ (1 HS down) / 85 mA (4 HS) (CH334DS1_en §4.2); APS6404L I_CC read/write **7 mA max** (aps6404l.pdf Table 9, so 30 mA is generous); W25Q128JV I_CC3 ≤ 20 mA at 104 MHz, program/erase ≤ 25 mA (§9.4); FT232H I_reg 54 mA typ at VREGIN 5 V (Table 5.2, typ only); TCA9555 ≤ 30 µA active.
- **Impact:** 3.3 V max ≈ 455 mA (not 420), +5V_SYS logic max ≈ 535 mA: the Default/USB 2.0 500 mA case goes from "touches" to "over" if every maximum coincides. Still fine for the 1 A LDO; adds ~0.1 W to the LDO heat.
- **Fix:** Update the table.
- **Confidence:** high for the RP2350 figure; SD figure unverified.
- **Owner decision:** approved (2026-09-26)

### R094 [Info] Power: every 3.3 V part's V_DD max vs the 3.16–3.44 V rail
- **Evidence:** APS6404L-3SQR: V_DD **2.7–3.6 V**, abs max 4.0 V (aps6404l.pdf Table 9 / Table 5). LCSC's "2.7–3.3 V" is wrong; the part is fine. Note V_IH min = V_DD − 0.4 V: OK since the RP2350 QSPI and GPIO 47 are on the same rail. W25Q128JV: 3.0–3.6 V at 133 MHz (abs 4.6 V). RP2350 IOVDD/QSPI_IOVDD 3.3 V nominal, 3.63 V max; **VREG_AVDD 3.135–3.63 V** (§6.3, only 25 mV below our 3.16 V minimum, plus the 33 Ω filter drop, µA-level → OK). FT232H VCCIO 2.97–3.63 V. TCA9555 1.65–5.5 V. 74LVC1G17 ≤ 5.5 V. CH334 external mode **3.2–3.4 V**, abs max 4.0 V (CH334DS1_en §4.1/4.2): the only part the rail can violate, as already accepted (bring-up measurement).
- **Confidence:** high.

### R095 [Low] Power: bench path: TERMPWR limit (up to 1.41 A) + logic (up to ~0.53 A) can exceed the bench eFuse's minimum limit (1.78 A)
- **Evidence:** Bench I_LIM 1.78–2.22 A; TERMPWR I_LIM 1.02–1.41 A (both above). Full TERMPWR overload that keeps V_OUT above the 1.9 V foldback point, plus maximum logic, gives ~1.94 A.
- **Impact:** In that corner the bench eFuse also current-limits (ITIMER open → immediately), +5V_SYS sags and the MCU browns out instead of cleanly reporting TERMPWR_FLT_N. A hard short folds back (§7.3.5.3 note 2) and doesn't hit this.
- **Fix:** Accept, or raise the bench limit to ~2.5 A (R_ILM ≈ 1.33 k, e.g. 1.2 k + 130 Ω; the board's worst is still far below).
- **Confidence:** med.
- **Owner decision:** approved (2026-09-26)

### R096 [Low] Power: at power-up on a Default USB port, TERMPWR can pulse on before 3.3 V rises
- **Evidence:** NOTES "TERMPWR switch" accepts that the enable node reads low until 3.3 V is up. On a Default port, the eFuse then does a current-limited (not dVdt) start at up to 1.41 A into the bus capacitance; no, on first power-up OVLO is low from the start, so it's the dVdt ramp (≥ 3 ms), and 3.3 V (LDO starts at ~3.5 V in) normally rises before +5V_SYS passes the eFuse UVLO (4.20–4.47 V). So the pulse is short or absent.
- **Impact:** Probably nothing; mentioned so bring-up checks it on a 500 mA port (scope TERMPWR at plug-in).
- **Fix:** None needed if the scope shows no pulse; otherwise pull the node up to +5V_SYS through a divider instead of 3.3 V.
- **Confidence:** med.
- **Owner decision:** approved (2026-09-26)

### R097 [Low] Power: capacitors on the power rails are mostly unspecified (for the schematic)
- **Evidence (what the datasheets ask for; nothing in NOTES/parts-list unless noted):**
  - Bench eFuse IN: ≥ 0.1 µF at the pin + ~1 µF rated ≥ 2 × V_IN, i.e. **50 V** (SLVSFC9C §8.3.1, §8.4). OUT: ≥ 1 µF low-ESR close to the pin (§8.3.1).
  - TERMPWR eFuse IN (+5V_SYS): 0.1 µF; OUT (TERMPWR): ≥ 1 µF, plus a Schottky from OUT to GND is TI's suggestion for the negative spike when it interrupts a 6 m cable (§8.3.1; V_OUT pulse min −0.8 V, §6.1). The SMF6.0A forward-conducts but its V_F at amps is ~1–3.5 V.
  - LM66200 VIN1 ~1 µF (keep ≤ ~4.7 µF for the USB 10 µF rule), VIN2 ~1 µF, VOUT ≥ 0.1 µF (§7.3.2, §9).
  - +5V_SYS bulk: none specified; the dVdt analysis assumed ≤ 47 µF, and U1's soft start handles up to ~100 µF.
  - TPS73701 ×2: C_OUT ≥ 1 µF within 10 mm, C_IN 1 µF (SBVS067W §7.3); avoid many paralleled MLCCs with C × ESR < 50 nF·Ω (§7.2.2.1). The 2.80 V rail sees 0–0.39 A steps: give it ~10 µF + a bleed (see above).
  - CH334: V5/VDD33 decoupling per its reference schematic; FT232H VREGIN/VCCD/VCORE caps (another reviewer listed them); LM393 100 nF; TCA9555 100 nF (already in the pinout); PSRAM 100 nF + 1 µF (done); flash 100 nF (done).
- **Fix:** Add a "Power-rail capacitors" table to NOTES/parts-list before drawing.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R098 [Info] Power: wrong-supply cases on the bench node, and cross-domain back-feed paths checked
- **Evidence:**
  - 12 V / 24 V adapter: the eFuse stays in OVLO (OVLO pin 2.51 V / 5.03 V > 1.223 V), OUT stays off, so U1 VIN2, the 2N7002 gate divider (10 k/100 k on OUT: 0 V) and everything downstream see nothing. The only over-stress is the EN pin at 24 V (Med entry above) and the input capacitor's rating. A **fitted** SMF15A (V_BR 16.7 V) would conduct and burn on 24 V, as NOTES says; on reverse polarity a fitted unidirectional TVS forward-conducts.
  - Reverse polarity (≥ −15 V): OUT blocked (§7.3.1); I_IN leakage −3.7 µA at −14 V (§6.5); EN/OVLO clamp current ~25 µA (Low entry above).
  - U1 VIN2 leakage into the bench eFuse OUT when USB powers the board: ≤ ~160 nA (LM66200 Fig. 6-8), bled by the 110 k gate divider → < 20 mV: the bench-present FET can't be falsely turned on.
  - Open-drain signals into the 3.3 V expander (LM66200 ST, both eFuse FLTs, LM393 outputs, 2N7002): all pulled up only to 3.3 V, so no 5 V reaches a 3.3 V input. FLT abs max 6.5 V, ST 6 V.
  - CC reference is on 3.3 V while the LM393 is on 5 V: with 3.3 V absent the reference is 0 V and the node pull-up is off, so the node reads "enabled"; covered by the accepted power-up note.
  - Remaining back-feed paths are TERMPWR_OK → expander (Low entry above), CH334 D+ pull-up with VBUS absent and FT232H VCCIO/VCCD (both logged by other reviewers).
- **Confidence:** high.

### R099 [Low] Power: doc slips found while checking
- **Evidence:** `3-driver/blocks/1-power.md` Description still says "through a **2.85 V** regulator" (decided 2.80 V). NOTES "Ideal diodes" says LM66200 ON thresholds "aren't in the datasheet" (they are: V_ON 0.8/1.0/1.2 V, SLVSG04 §6.5). NOTES "CC detection" says CJ431 = 2.495 V / ±0.5 % incl. ±0.8 % tempco (see the CJ431 entry). NOTES "Resistor values" TERMPWR I_LIM spread 1.06–1.39 A (datasheet row gives 1.02–1.41 A). NOTES "TERMPWR switch and current limit" earlier text "R_ON 28 mΩ": that's 25 °C typ at 12 V/3 A; the max over temperature is 45 mΩ (§6.5).
- **Fix:** Correct when next editing those sections.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R100 [Low] Firmware: PIO0 sketch; `out pins, 9 [8]` won't assemble with `.side_set 1 opt`, and 8 cycles misses the 55 ns setup
- **Evidence:** RP2350 datasheet §11.5.1: side-set uses SIDESET_COUNT MSBs of the 5-bit delay/side-set field, plus one more bit when SIDE_EN (`opt`) is set. `.side_set 1 opt` takes 2 bits, leaving 3 delay bits, so **max delay = [7]**. `[7]` gives 8 cycles = 53 ns at 150 MHz, and SCSI-2 Table 7 needs deskew 45 + cable skew 10 = **55 ns** from data to ACK. Also, data *release* edges (a bit going from 0 to 1) are passive rises through the 110 Ω terminators into the cable and device capacitance, and can take tens of ns to cross 2.0 V (inferred). Asserting ACK is a fast FET edge. So the margin at the far end is smaller than the cycle count suggests.
- **Impact:** assembler error as written; marginal DATA OUT setup once fixed naïvely.
- **Fix:** split the delay (`out pins, 9 [7]` then `nop [7]`, ~107 ns), or use a non-`opt` side-set on data_out (every instruction then sets ACK; 4 delay bits, max [15]). Budget ≥ 100 ns data-to-ACK. That's still < 1 µs per byte at the 1.5–5 MB/s we need. Measure at the connector with the Rigol at bring-up.
- **Confidence:** high on the encoding rule; med on the edge-rate estimate.
- **Owner decision:** approved (2026-09-26)

### R101 [Med] Firmware: data_in/data_out sketches don't detect a phase change, so they'd ACK a STATUS or MESSAGE byte as data
- **Evidence:** both loops just `wait 1 pin 16` (REQ) and handshake. The "+2 for a byte count" limits the count, but a target may end a data phase early: short READ, DISCONNECT (MESSAGE IN), or CHECK CONDITION (STATUS). REQ for the next phase's byte looks the same. SCSI-2 requires the initiator to check the phase on each REQ. The phase lines are stable before REQ, since the target waits ≥ a bus settle delay after changing them. All three phase changes out of DATA IN/OUT set **C/D** (STATUS: C/D = 1; MESSAGE IN/OUT: MSG = 1 and C/D = 1).
- **Impact:** a swallowed status or disconnect message desyncs the protocol engine. A DATA OUT SM would also drive data into a phase that isn't ours.
- **Fix:** set EXECCTRL.JMP_PIN = GPIO 15 (C/D, already in PIO0's window) and add `jmp pin, phase_changed` after each `wait 1 pin 16`, before ACK. The exit path raises an IRQ to the CPU. It costs +1–2 instructions per program. Also: data_in and data_out both side-set ACK and both wait on REQ, so only one may be enabled at a time (`pio_sm_set_enabled`). Last writer wins on a shared pin.
- **Confidence:** high.
- **Owner decision:** approved (2026-09-26)

### R102 [Low] Firmware: data_in samples and asserts ACK in the same instruction; with autopush at threshold 9 the stall lands on that instruction
- **Evidence:** RP2350 §11.5.4.1 pseudocode: `in` shifts, then "if rx count ≥ threshold: if rx fifo full: stall". Side-set is applied at the start of the (stalled) instruction. In the sketch `in pins, 9 side 1` with a 9-bit threshold, a full FIFO asserts ACK while the push is stalled. Per SCSI-2 async, the target may change the DATA BUS as soon as it sees ACK. Whether a stalled `in` re-samples on retry isn't spelled out, so it's **unverified** whether the captured byte could then be the next one. BlueSCSI's host reader avoids this structurally: `in pins, 9 side 0` (ACK) then `in null, 7`, with a 32-bit threshold, so the stall always lands on a later instruction.
- **Fix:** capture before ACK can be seen, e.g. `wait 1 pin 16` → `jmp pin phase_changed` → `in pins, 9` → `push block side 1` (the stall happens with the data already in the ISR). Or copy BlueSCSI's padding/threshold trick. With left-shift and the 9 bits in [8:0], the CPU accumulates XOR parity per block and packs bytes (~4 cycles/byte, ~13 % of a core at 5 MB/s). DMA can't strip parity and check it at the same time.
- **Confidence:** med.

### R103 [Med] Firmware: hard real-time bus-release deadlines need an SRAM-resident, top-priority handler; one PIO trick removes the tightest one
- **Evidence (SCSI-2 rev 10L Table 7, §5.7, §6.1.1):**
  - **Bus clear delay 800 ns:** release *all* signals after (a) BUS FREE is detected (≤ 1200 ns from BSY and SEL both going false), (b) SEL from another device during arbitration, (c) **RST going true**.
  - **Bus set delay 1.8 µs:** assert BSY + ID within 1.8 µs of the BUS FREE detection used for arbitration.
  - **Data release delay 400 ns:** the initiator releases DB within 400 ns of I/O going true.
  - Arbitration delay 2.4 µs (minimum); selection abort 200 µs.
  - Cortex-M33 interrupt entry is ~12 cycles (80 ns at 150 MHz) when the vector table and handler are in SRAM. A single XIP miss is ~0.4–1 µs, and more behind PSRAM DMA (see the QMI finding). An SDK `flash_safe_execute` or any long interrupts-off section blocks for ms.
- **Impact:** with code in flash, the 400/800 ns deadlines can be missed. Our data gates or BSY/ATN could then stay asserted into another device's phase, or through a bus reset. With open-drain drivers that corrupts data but doesn't damage anything.
- **Fix (firmware):**
  - GPIO interrupts on RST (assert), BSY/SEL (both false) and I/O (assert), at the highest NVIC priority. The handler lives in SRAM, disables the PIO0 SMs, and forces all 14 gates off: SIO clear plus `IO_BANK0 GPIOx_CTRL.OEOVER`, or PADS OD, for the PIO pins. That's ~15 register writes ≈ 150–250 ns.
  - Arbitration/selection in a tight polling loop on a **dedicated core** (core 1), interrupts masked only for that window, never touching flash or PSRAM.
  - The 400 ns data-release case is easier to solve in PIO: in data_out, release the data lines right after REQ goes false (`mov pins, null` before dropping ACK). SCSI-2 lets the initiator change or release the bus once REQ is false. Then no data is driven between bytes, and an I/O change never finds our gates on.
  - PIO0 has no spare SM for a hardware RST watchdog (4/4 used), so the ISR is the mechanism.
- **Confidence:** high on the spec numbers; the latency numbers are typical M33 figures, not measured.
- **Owner decision:** approved (2026-09-26)

### R104 [Med] Firmware: the edge-level sniffer produces ~60–80 MB/s during data phases; long captures need Phase 1's protocol-level design
- **Evidence:**
  - PIO0 `sniff` emits a word on every change of the 18 lines, plus a timestamp word from `stamp`: 8 bytes per event. One async byte gives ~5–6 events (data settle, REQ↓, ACK↓, REQ↑, ACK↑; receiver skew can split the data change into two samples).
  - At the 1.5 MB/s scan rate that's 7.5–9 M events/s ≈ **60–72 MB/s**. At 5 MB/s it's ~200 MB/s.
  - Sinks: USB FS ≈ 1 MB/s; FT1248 ≈ 10 MB/s (below); PSRAM ≈ 35 MB/s (above) and only 8 MB (~0.1 s); SRAM rings ~300 KB (~5 ms).
  - The loop is 3 instructions = 20 ns as claimed, but the emit path is 5 more instructions, so ~40 ns blind after each event. That's fine for async; at fast-sync 30 ns pulses (Table 7) edges will be merged or lost.
  - The two-SM scheme (sniff raises IRQ 0; stamp pushes into its own FIFO) can **desync**. If stamp's FIFO is full or it is still busy when the next IRQ comes, one stream drops a word and every later state/time pair is misaligned. The NOTES already mark it unverified.
- **Impact:** R4 "long-capture protocol sniffer" isn't met by the sketch. It works for short edge-level bursts (commands, status, messages, the start of a data phase).
- **Fix:** two modes.
  1. **Protocol mode** for long captures, as `1-bus-capture/NOTES.md` already describes: one record per REQ/ACK handshake (byte + parity + phase bits + coarse time), sampled on REQ (DATA IN) or ACK (DATA OUT), with per-phase counts, the first N bytes and a checksum. About 4 B per handshake, so 6 MB/s at 1.5 MB/s. That fits FT1248 and PSRAM, and FS USB once data phases are summarised.
  2. **Edge mode** into SRAM/PSRAM for short triggered windows.

  Put the time and the state in **one** SM's words (e.g. 18 state bits + a 14-bit delta count in one push) so the streams can't desync.
- **Confidence:** high on the arithmetic; the events-per-byte figure is an estimate.
- **Owner decision:** approved (2026-09-26)

### R105 [Low] Firmware: fast synchronous (10 MB/s) data-in has a 10 ns hold time; at 150 MHz the PIO samples 7–13 ns after REQ
- **Evidence:** SCSI-2 Table 7: fast hold time **10 ns**, fast deskew 20 + fast cable skew 5 ns; non-fast hold is 45 ns. In PIO, REQ and data share the same 2-flop synchroniser, so `wait 1 pin 16` followed by `in pins, 9` samples the data one instruction after the REQ sample that released the wait. That's 6.7–13.3 ns after the physical REQ edge (sample-phase uncertainty + 1 cycle), plus receiver skew. The window closes 10 ns after REQ.
- **Impact:** only if the D4000 negotiates fast sync (unknown; Phase 2 open question; WD33C93A can do 10 MB/s). Async and ≤ 5 MB/s sync have 45 ns hold, which is fine. R1 already makes sync optional.
- **Fix:** in sync mode, sample `mov x, pins` (all 18 bits in one sample, so REQ and data come from the same instant) and pick the first sample with REQ asserted; or raise clk_sys (e.g. 250 MHz → 4 ns steps). Initiators may also refuse fast sync in SDTR, and 5 MB/s sync would still exceed R3.
- **Confidence:** med.

### R106 [Info] Firmware: FT1248 4-bit master fits PIO1 and clears R3 on the MCU side; USB-side rate unverified
- **Evidence (AN_167 v1.1 §3, §5.3, §5.5, §8):**
  - While SS_n is high, the FT232H drives TXE# on MIOSIO0 and RXF# on MISO.
  - Each transaction: SS_n low → **2 command clocks** (4-bit: MIOSIO[3:2] low encodes the width) → **1 turnaround clock** → **2 clocks per byte** (Figs 5.8/5.9) for as long as SS_n stays low. MISO carries ACK/NAK for each byte, valid from the first clock edge of the data phase. On NAK the master should raise SS_n and retry that byte later; a NAKed write byte isn't stored.
  - The master must tristate MIOSIO on the last clock before raising SS_n. CPHA = 1 only (CPOL set in the EEPROM). Commands: 0 write, 1 read, 4 flush. Buffers are 1 KB each way. Unused MIOSIO4–7 "may be left unterminated" (internal pull-ups), so FT232H pins 17–20 need no parts before the 8-bit rework.
  - The FT232H datasheet has no FT1248 AC timing, as NOTES says.
- **Throughput at SCLK = 25 MHz (clk_sys/6):** a burst of N bytes takes ≈ 2N + 5–6 clocks (SS setup, 2 cmd, 1 TA, end TA, idle). At N = 512 that's 12.4 MB/s; at N = 64, ~11.5 MB/s. That's **far above R3's 1.5 MB/s and the 3–5 MB/s target**. The cap will be the FT232H's USB-side drain, which is unmeasured (async FIFO is quoted at 8 MB/s, sync FIFO higher).
- **PIO fit:**
  - Pins: MIOSIO0–3 are `out`/`in`/`set pindirs` pins (32–35); SCLK + SS_n are a 2-bit non-`opt` side-set (41–42), leaving 3 delay bits; MISO (43) is JMP_PIN for the per-byte NAK test.
  - Per byte: `out`/`in` a nibble with SCLK low, then SCLK high, twice, plus `jmp pin` for NAK and a loop test. That's ~5 instructions in 12 clk_sys, which fits at clkdiv 1.
  - Estimate: write path (with NAK retry holding the byte in Y) ~12–14; read path ~10–12; shared command/turnaround ~4. So **~26–30 of 32**. Tight but plausible, since PIO1 carries nothing else. Otherwise split read and write into two SMs sharing the command code.
  - DMA: TX and RX DREQs of PIO1 SM0/1.
- **Confidence:** med (no prior art; instruction counts are estimates).

### R107 [Info] Firmware: PIO, DMA and IRQ resources fit
- **Evidence:**
  - **PIO0** (4 SMs, 32 slots): data_in ~6 (with byte count, C/D check, explicit push), data_out ~7 (with split delay, C/D check, data release), sniff 7, stamp ~5. That's **~25/32, 4/4 SMs**. It's full, so sync-mode programs mean swapping programs at runtime (as NOTES plans), and there's no spare SM.
  - **PIO1:** FT1248 ~26–30/32 (previous finding), 1–2 SMs.
  - **PIO2:** BlueSCSI's RP2350 SDIO is cmd_rsp 10 + rd_data 7 + tx 8 = **25** (`sdio_RP2MCU.pio`). A 1-bit rewrite is similar or smaller, so it fits.
  - **DMA:** 16 channels (RP2350 §12.6). Needs ≈ SCSI RX + TX (2, plus a chained control channel each for rings = 4), sniffer 1–2, FT1248 RX/TX 2, SDIO 2, SRAM↔PSRAM 1–2. That's **≈ 10–12**, OK. There are DREQs for every PIO SM TX/RX.
  - **SD CRC:** the DMA sniffer computes **CRC-16-CCITT** (SNIFF_CTRL.CALC = 0x2/0x3, datasheet §12.6). With 1-bit SDIO there's one CRC16 over the byte stream, so the DMA can do it for free (it can only watch one channel at a time). 4-bit SDIO needs per-line CRCs, which is why BlueSCSI does them on the CPU.
  - Each PIO block has 2 IRQ lines to the NVIC; enough.
- **Confidence:** med (the instruction counts are estimates).

### R108 [Med] Firmware: 1-bit SDIO as a spill target is marginal at default speed and can't write and drain at once
- **Evidence:**
  - 1-bit SD default speed is 25 MHz = 3.125 MB/s raw on D0; High Speed (CMD6, 3.3 V signalling) is 50 MHz = 6.25 MB/s raw, and PIO at 150 MHz manages that at 3 clk_sys per bit. BlueSCSI runs its RP2350 SDIO in HIGHSPEED_OVERCLOCK mode (`sdio_rp2350_config.h`).
  - Real sustained multi-block writes lose a lot to card busy periods (typically 50–70 % of raw; card-dependent, **unverified**), with occasional busy spikes of 100–250 ms that the PSRAM must absorb. So that's ~1.6–2.2 MB/s at 25 MHz and ~3–4 MB/s at 50 MHz.
  - Spill only helps if the SD can take the scan rate while the host is stalled, **and then** supply stored data while new data keeps arriving. The link is half-duplex, so draining needs ≥ 2 × 1.5 MB/s = 3 MB/s.
- **Impact:** at 25 MHz, spill barely keeps pace (≥ 1.5 MB/s) and can't recover. At 50 MHz High Speed it works at 1.5 MB/s, but not at the 3–5 MB/s target. With 8 MB of PSRAM (~5 s) in front, spill only matters for host stalls longer than ~5 s. Whether the scanner simply pauses on a slow host (Phase 2 open question) may make spill unnecessary.
- **Fix:** no hardware change. Plan for High Speed 50 MHz in firmware. Treat spill as "extends the stall buffer", not "sustains throughput". The NOTES rule "if pins free up, go to 4-bit first" stands (4 × bandwidth).
- **Confidence:** med.
- **Owner decision:** approved (2026-09-26)

### R109 [Low] Phase1: "total bus length ≤ 3 m" contradicts Phase 3's reading of SCSI-2 rev 10L
- **Evidence:** `1-bus-capture/NOTES.md` cabling plan: "Total bus length should stay ≤ 3 m. That's the SE limit once sync above 5 MB/s is negotiated." SCSI-2 rev 10L §5.2.1: "The maximum cumulative cable length shall be 6,0 m" for SE, with no fast-mode exception there. Phase 3 NOTES already says the 3 m figure "is not in SCSI-2 rev 10L; it comes from later standards" (SPI's Fast-20 limits of 3 m / 1.5 m). The AHA-2930CU can do Fast-20, but the WD33C93A caps negotiation at ≤ 10 MB/s, so Fast-20 won't happen on this chain.
- **Impact:** none electrically; ≤ 3 m is a conservative target. Just two notes disagree.
- **Fix:** reword Phase 1 to "SCSI-2 allows 6 m SE; keep ≤ 3 m as margin (Fast-20 rules from SPI don't apply because the WD33C93A can't do Fast-20)".
- **Confidence:** high.

### R110 [Low] Phase1: LA flying leads and the Pico 2 tap are stubs; SCSI-2 limits stubs to 0.1 m
- **Evidence:** SCSI-2 §5.2.1: "A stub length of no more than 0,1 m is allowed off the mainline … Stubs should be spaced at least 0,3 m apart". Phase 1 says "keep the leads short" without a number. The Pico 2 sniffer's wiring to the tap is the same kind of stub, plus GPIO capacitance.
- **Impact:** reflections on REQ/ACK can cause double-clocking on the scanner or the G4 during captures, and that would look like a protocol bug.
- **Fix:** state "≤ 10 cm from the IDC tap to the LA/Pico input, including the lead", and prefer the IDC tap connector at the ribbon's end, next to the terminator. The ≤ 2.96 V bus idle is below the RP2350's 3.63 V fault-tolerant limit for unpowered GPIO 0–39 (datasheet Table 1426 "Digital IO (FT)"), so an unpowered Pico 2 doesn't load the bus. The existing "series resistors or buffers" advice is still good practice.
- **Confidence:** high on the spec; med on the practical impact.

### R111 [Question] Phase4/RP2350: which RP2350 stepping will JLC fit, and will macOS let the host tool claim the FT232H?
- **Evidence:**
  - (1) Errata E9/E14/E16 apply only to A2; A3 and A4 fix them (datasheet Appendix C). The design is safe either way, but bring-up notes differ. Check the package marking or `rp2350_chip_version()`.
  - (2) Unverified, from memory: macOS ships a built-in FTDI serial driver that matches VID/PID 0403:6014 (FT232H) and claims the interface, which can stop D2XX or libusb (pyftdi) from opening it. The usual fix is a custom PID in the 93LC56 EEPROM, which the EEPROM is programmed for anyway. Phase 4 already flags D2XX + FT1248 as unverified.
- **Impact:** (1) none; (2) R5 "no custom kernel drivers" on macOS could need an EEPROM PID change or a driver-detach step.
- **Fix:** (2) test with a dev FT232H module on the owner's Mac early. It's cheap, and it de-risks Phase 4 without the board.
- **Confidence:** low on (2).
- **Owner decision:** approved (2026-09-26)
- **Owner comment:** assume A4, account for A2. We can set up a bench test with an FT232H breakout board and a pi pico 2 w.

### R112 [Info] Phase1: LA sample-rate and Pico 2 sniffer numbers are consistent with SCSI-2
- **Evidence:** fast assertion/negation periods are 30 ns (Table 7), matching Phase 1's "~30 ns pulses". 200 MS/s (5 ns) gives 6 samples per pulse, which is enough to decode. The Phase 1 Pico 2 plan (sample DB on REQ for DATA IN, on ACK for DATA OUT; parity self-check; summarise data phases because FS USB is ~1 MB/s) is the protocol-level design recommended above for the board's long-capture mode. Its fast-sync risk is the 10 ns hold-time issue above.
- **Confidence:** high.

### R113 [Low] Firmware: injecting our ID bit into the stalled data_out SM needs care; the SET group doesn't reach DB5–DB7
- **Evidence:** NOTES: "the CPU puts our ID bit on a PIO-owned data pin by injecting one instruction into the idle data-out SM". `set pins` covers at most 5 pins from SET_BASE (§11.5.x), and `set x` takes a 5-bit immediate. With SET_BASE = 18 that reaches DB0–DB4 only, and the default ID 6 is DB6 (GPIO 24). `mov pins, …`/`out pins` drive the whole 9-pin OUT group, which is fine only if the other 8 bits are 0 (released). The SM is stalled on `pull block` at that moment. SMx_INSTR executes immediately (§11.4) and the stalled `pull` resumes afterwards (behaviour while stalled is **unverified** for this exact case).
- **Impact:** none if handled; a wrong injection asserts extra DB bits during arbitration, which SCSI-2 forbids (§5.7 note / Table 6: only our own ID bit).
- **Fix (simplest):** during arbitration and (re)selection, switch the one ID gate pin's FUNCSEL from PIO0 to SIO (`gpio_set_function(24, GPIO_FUNC_SIO)`, output 1), then hand it back to PIO0 before the first information phase. It's one atomic register write each way, and PIO state doesn't matter. Keep the E9 rule (clear IE after every `gpio_set_function`).
- **Confidence:** med.
