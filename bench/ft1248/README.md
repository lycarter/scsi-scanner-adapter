# FT1248 bench test (FT232H breakout + Pico 2 W)

Bench test R111 from `design_docs/3-driver/NOTES.md` (open question 11): prove FT1248 between an
FT232H and an RP2350 on a breadboard, starting with the 1-bit bus. This branch
(`lcarter/ft1248-bench`) is **not meant to be merged**. Findings worth keeping get copied by hand
into `design_docs/3-driver/NOTES.md` and `docs/decisions.md` on `main`.

If you are an LLM picking this up cold: read this file, then `AGENTS.md` at the repo root. The
owner wants small steps, reasoning, and unverified claims marked as such.

## Hardware

- **FT232H breakout:** a clone of Adafruit's USB-C FT232H breakout (product 2264). The owner said
  to assume it is an exact clone; nothing about it has been measured yet.
- **Pico 2 W** (RP2350A). GP23–25 and GP29 belong to the radio.
- Wired on a breadboard on 2026-10-12 as below. Diagram: `wiring.html` (open in a browser).

| Signal | FT232H pad (chip pin) | Pico 2 W | Driven by | Final board GPIO |
|---|---|---|---|---|
| SCLK | C0 (ACBUS0, 21) | GP15, pin 20 | Pico | 37 |
| SS_n | C1 (ACBUS1, 25) | GP14, pin 19 | Pico | 36 |
| MISO | C2 (ACBUS2, 26) | GP13, pin 17 | FT232H | 35 |
| MIOSIO0 | D0 (ADBUS0, 13) | GP16, pin 21 | both, in turn | 38 |
| GND | Gnd | pin 23 | | |
| MIOSIO1–3 (later, 4-bit) | D1, D2, D3 | GP17, GP18, GP19 | | 39–41 |

- Pico GPIO = final-board GPIO − 22, so the PIO program ports by changing base pins only
  (SS_n + SCLK adjacent for the 2-pin side-set, MISO = JMP pin, MIOSIO0–3 consecutive).
- Each board has its own USB cable. No power wire between them, only ground.
- "I2C Mode" switch **off** (Adafruit guide p. 32: it connects D1 to D2). STEMMA socket empty.

## Protocol facts we rely on (FTDI AN_167 v1.1; PDF is in the untracked `reference/datasheets/`)

- FT1248 is selected by the EEPROM. Blank or bad EEPROM = UART mode, where ADBUS0 (D0) is TXD,
  an **output**. So the Pico keeps its four pins as inputs until the idle check passes.
- Bus width is chosen per transaction: the lines that are low on the first clock select it.
  D1–D7 unconnected (internal pull-ups) = 1-bit (§4).
- 1-bit transaction (§5.1): SS_n low → FT232H releases MIOSIO0 → 7 command clocks → 1 turnaround
  clock → 8 clocks per byte while SS_n stays low. MISO = ACK/NAK per byte. After a write the
  master releases MIOSIO0 on the last clock before raising SS_n.
- Commands (§6): 0x0 write, 0x1 read, 0x4 flush. CPHA = 1 only; CPOL is an EEPROM bit (§8).
- While SS_n is high and flow control is on, MISO shows RXF# and MIOSIO0 shows TXE# (§3).
- SCLK ≤ 30 MHz. No AC timing is published.

## Mac setup

The Adafruit guide (*CircuitPython Libraries on any Computer with FT232H*, pp. 19–20, 25) says:
`brew install libusb`, `pip3 install pyftdi`, then `Ftdi().open_from_url('ftdi:///?')` lists the
device. We don't need Blinka. The guide does not cover the EEPROM.

```sh
cd bench/ft1248
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # libusb 1.0.27 is already in brew
```

## EEPROM (`ft232h_eeprom.py`)

`USAGE.md` on main says to use FT_PROG on Windows. pyftdi can do it from the Mac instead: it sets
the port type but not the three FT1248 option bits, so the script pokes byte 0x01 itself and lets
pyftdi recompute the checksum. Every write first saves the old image under `backups/`.

```sh
.venv/bin/python ft232h_eeprom.py list
.venv/bin/python ft232h_eeprom.py info                # read-only, saves a backup
.venv/bin/python ft232h_eeprom.py set-ft1248          # dry run, prints the byte changes
.venv/bin/python ft232h_eeprom.py set-ft1248 --write  # then unplug and replug the FT232H
.venv/bin/python ft232h_eeprom.py set-uart --write    # undo
```

Chosen options: clock idles low, MSB first, flow control on. Reasons: idle-low with CPHA = 1 is
the plain "SPI mode 1" shape and matches the planned side-set; flow control on gives the idle
status lines, which are our no-firmware check.

The clone's EEPROM turned out to be **blank** (all 0xFF, enumerating as "Single RS232-HS" with no
serial), so there was nothing to edit in place. `probe` showed a writable 256-byte part, and
`set-ft1248 --init-serial BENCH1` built a whole image (layout in `fresh_image()`).
`backups/BENCH1-ft1248.bin` is the image now in the chip. To go back to blank, write 0xFF
everywhere with `restore` (make a 256-byte 0xFF file).

Unverified:
- That bit 0x04 of byte 0x01 *set* means flow control *on* (libftdi/pyftdi name the bit; D2XX's
  header comment says "enable"). The idle check settles it.
- The byte layout in `fresh_image()` is libftdi's, from memory. The chip accepted it (checksum
  valid, new serial enumerates), but drive strength and ACBUS function bytes are untested.

Verified on macOS 26.6 (2026-10-12): pyftdi/libusb reads and writes the EEPROM **without sudo**
while Apple's AppleUSBFTDI driver is attached and `/dev/cu.usbserial-*` exists. A USB reset from
pyftdi (`FtdiEeprom.reset_device()`) reloads the EEPROM; no replug needed.

## Idle check (after programming, no Pico firmware)

Pico unplugged or in BOOTSEL (all GPIO high-impedance). Scope on C2 (MISO) and D0 (MIOSIO0).
Expected: MISO high until the Mac sends a byte (`printf x > /dev/cu.usbserial-*`), then low;
MIOSIO0 low (room in the write buffer). If D0 idles high and pulses when the Mac sends, the chip
is still a UART.

## Status log

- 2026-10-12: branch created; pin map chosen; breadboard wired by the owner; `ft232h_eeprom.py`
  written and its edit + checksum path tested offline against pyftdi (no hardware attached yet).
  **Next:** plug in the FT232H alone, run `info`, review the dry run, write, do the idle check.
- 2026-10-12: FT232H plugged in alone. EEPROM blank; probed as 256-byte; programmed for FT1248
  (clock idle low, MSB first, flow-control bit set, serial BENCH1). It now enumerates as
  `0403:6014 'FT232H bench' BENCH1` and macOS makes `/dev/cu.usbserial-BENCH1`.
  Host-side pin read (`Ftdi.read_pins()`, no bit-mode change) gives ADBUS = `11111110`: D0 low,
  D1–D7 pulled high. D0 low is what TXE# with flow control on should look like (UART TXD would
  idle high), so FT1248 mode and the flow-control polarity look right. Caveat: pyftdi's open()
  resets the bit mode first. **Still to do on the scope:** MISO (C2) high, then low after
  `printf x > /dev/cu.usbserial-BENCH1`.
- 2026-10-12: **scope idle check passed** (owner, Pico unplugged): C2/MISO high and D0 low at
  idle; after `printf x > /dev/cu.usbserial-BENCH1`, C2 goes low and stays low. So FT1248 mode
  is active, EEPROM bit 0x04 set = flow control on, and Apple's serial node delivers bytes into
  the FT1248 read buffer. Status lines are active-low like RXF#/TXE#.
  **Open:** C2 high read **3.7 V** on the scope. Expected ~3.3 V. Check the breakout's 3V pad
  with a multimeter before trusting it: the RP2350's limit for an *unpowered* GPIO is 3.63 V
  (RP2350 datasheet "Digital IO (FT)" table, cited in the design review R110).
- 2026-10-12: multimeter: 3V pad = 3.3 V, so the 3.7 V was a scope error (closed). Idle digital
  pins read ~2.8 V (weak internal pull-ups).
- 2026-10-12: Pico 2 W flashed with MicroPython v1.29.0 (`firmware/`, git-ignored; from
  micropython.org/download/RPI_PICO2_W). `ft1248_bitbang.py` is a ~5 kHz bit-banged 1-bit
  master. **1-bit FT1248 works in both directions:** `mac_loopback.py` sent all 256 byte values
  plus a string (277 bytes) Mac → `/dev/cu.usbserial-BENCH1` → FT232H → Pico → FT232H → Mac and
  got them back intact.
  Findings:
  - Command bits on the wire are CMD3, 0, 0, CMD2, 0, CMD1, CMD0, then one turnaround clock
    (AN_167 Fig. 5.2/5.3). Read = 0x1, write = 0x0, flush = 0x4 all accepted.
  - CPOL 0 / CPHA 1 as programmed: drive on the rising edge, sample on the falling edge.
  - **ACK/NAK differs from AN_167's text:** MISO is low (ACK) only during the *first* clock of
    each byte, then high for the other seven. A NAK is MISO high on that first clock. The PIO
    program must sample MISO once per byte, on the first clock (`dbg_trace.py` prints the raw
    per-clock trace). Not yet looked at: whether this differs in 4-bit mode (2 clocks per byte).
  - A read past the end clocks out zeros with NAK; nothing breaks.
  - macOS shows two nodes for the one chip, `/dev/cu.usbserial-BENCH1` and
    `/dev/cu.usbserial-3`. Not investigated.
  Not measured: throughput, anything above ~5 kHz, the flush command's effect on latency.
- 2026-10-12: **PIO 1-bit master at real clock rates** (`pio_ft1248.py` on the Pico, still
  MicroPython; DMA feeds the FIFOs so Python is out of the data path; `speed_test.py` on the Mac
  sends/receives a known pattern through `/dev/cu.usbserial-BENCH1` and counts wrong bytes).
  clk_sys 150 MHz; SCLK = sm clock / (H + L). Breadboard, ~10 cm jumpers.

  | SCLK | H, L | Pico → Mac (write) | Mac → Pico (read) | Read with input-sync bypass |
  |---|---|---|---|---|
  | 0.1–18.75 MHz | 4, 4 | clean | clean | |
  | 25 MHz | 3, 3 | clean, 2.77 MB/s (2 × 2 MB) | clean, 3.0 MB/s (3 × 128 KB) | clean |
  | 30 MHz (FTDI's max) | 3, 2 and 2, 3 | clean, 3.25 MB/s (2 × 2 MB) | **~97 % of bytes wrong** | clean, 3.5 MB/s (3 × 128 KB) |
  | 37.5 MHz (out of spec) | 2, 2 | corrupt | corrupt | clean once (64 KB) |

  "Clean" = zero wrong bytes in the amount shown; that is not a bit-error-rate measurement.
  Findings:
  - **Reads need INPUT_SYNC_BYPASS at 30 MHz and not at 25 MHz.** The program samples MIOSIO0
    on the next rising edge; the 2-flop synchroniser makes that ~13 ns earlier, which is too
    early at a 33 ns period. So FT232H clock-to-data plus wiring is somewhere between ~13 and
    ~20 ns (inferred from pass/fail, not measured). NOTES on main already plans the bypass.
  - Sampling on the next rising edge and testing MISO at the end of the first clock of a byte
    both work; see the program comments. NAK → raise SS_n → wait for the status line → resend
    the same byte was exercised constantly on writes (the 1 KB buffer fills) with no loss.
  - Rates are the link's own ceiling (8 bits × (H + L) cycles + a few per byte), so in 1-bit
    mode USB was never the limit. 1-bit at 25 MHz already beats R3's 1.5 MB/s.
  - A failed read run leaves bytes in the FT232H, which makes every later run look corrupt.
    `rx_test` now drains first. (This fooled me once.)
  - The read and write programs are 21 + 28 instructions, so they are loaded one at a time
    here. The final 4-bit pair must fit PIO1's 32 slots together or swap like this.
  Not measured: sustained Mac → Pico rate beyond a 128 KB burst (the Pico's RAM limits the
  verified size, and pyserial's write+flush takes 0.8 s for 128 KB, which I don't understand
  yet); the USB-side ceiling, which only 4-bit mode can reach; the flush command.
- 2026-10-12: **100 MB sustained, Pico → Mac, 1-bit, SCLK 30 MHz: perfect.**
  `sustained_test.py 100` (output saved in `results-100MB-1bit-30MHz.txt`): 104,857,600
  pseudorandom bytes in **32.25 s = 3.251 MB/s (26.0 Mbit/s)**. The Mac's copy is bytewise
  identical to a stream it regenerated independently, and CRC-32 of the received bytes equals
  the Pico's running CRC of the generated bytes (f7c7ecfa).
  Data = MurmurHash3 finaliser of a word counter (`fill_random`, viper), generated and CRC'd one
  32 KB chunk ahead while DMA sends the previous chunk. Generating + CRC took 94 % of the wall
  time, so the Pico's CPU was close to becoming the limit; a faster link (4-bit) will need a
  cheaper generator or checksum to stay link-limited.
  Reminder: the final board's FT1248 link is **4-bit**; 1-bit on the board is the microSD. This
  whole log so far is FT1248 at 1-bit width, because that is what the owner first asked for.
- 2026-10-12: `wiring.html` updated for 4-bit (D1→GP17, D2→GP18, D3→GP19); it is generated by
  `wiring_gen.py` from `wiring_tpl.html`. Measured on the Pico: `fill_random` 5.7 MB/s,
  `binascii.crc32` 8.8 MB/s. Both are below the ~11–12 MB/s a 4-bit link could reach at 30 MHz
  (my estimate: 2 clocks per byte, 5 cycles per clock, plus per-byte overhead), so the 1-bit
  test design would measure the CPU.
  **Proposed 4-bit sustained test (not built, awaiting the owner's OK):**
  1. Before the clock starts, fill two 128 KB buffers with `fill_random` (takes ~50 ms, untimed).
  2. During the run the CPU does nothing per byte: DMA plays buffer A, then B, then A… into the
     PIO FIFO. While one buffer is on the wire, Python overwrites the first 4 bytes of the other
     with the pass number, so the stream never repeats exactly and a dropped or repeated block
     shows up in the bytewise compare.
  3. The rolling checksum comes from the RP2350's **DMA sniffer**, which computes CRC-32 in
     hardware over the bytes the DMA channel actually moved. Unverified: that MicroPython's
     `rp2.DMA` exposes the sniff bit and that the sniffer's bit-reversed CRC-32 mode matches
     zlib; check both on 1 MB before trusting it.
  4. Mac: record everything, then (untimed) rebuild the stream with numpy, compare bytewise,
     compare CRC-32.
  5. Sweep SCLK (5, 10, 18.75, 25, 30 MHz) with 20 MB each before the 100 MB run. Where MB/s
     stops rising with SCLK, the limit has moved from the link to USB or the Mac.
  6. Reverse direction: Mac sends, the Pico's RX DMA discards the data but sniffs its CRC, with
     the first 128 KB kept for a bytewise check.
  Open risk: the Mac-side reader (pyserial through Apple's driver) may itself top out; if the
  sweep plateaus, repeat one point reading through pyftdi/libusb to tell the two apart.
- 2026-10-12: **4-bit FT1248 works; 100 MB perfect in both directions at SCLK 30 MHz.**
  Owner added D1–D3. Files: `dbg_trace4.py` (bit-bang trace), `pio4_ft1248.py` (PIO + tests, on
  the Pico), `sustained4_test.py` (Mac, Apple serial node), `libusb_rx_test.py` /
  `libusb_tx_test.py` (Mac, libusb), results in `results-100MB-4bit-30MHz*.txt`.

  **EEPROM is now LSB-first** (`set-ft1248 --lsb-first`, byte 0x01 = 0x06). Reason, measured with
  `dbg_trace4.py`: MSB-first puts B7 on MIOSIO0 (high nibble first, each nibble bit-reversed
  against GPIO order). LSB-first gives MIOSIO[i] = bit i, low nibble first, which is exactly
  PIO's `in pins, 4` / `out pins, 4` with right shifts. The command encoding is the same in both
  settings. **Recommend LSB-first for the real board** (changes `USAGE.md`'s FT_PROG step).
  The 1-bit programs (`pio_ft1248.py`, `ft1248_bitbang.py`) assume MSB-first and now see
  bit-reversed bytes.

  4-bit wire format, confirmed: clock 1 = CMD3, 0, 0, CMD2 on MIOSIO0..3; clock 2 = 0, CMD1,
  CMD0, x; clock 3 = turnaround; then 2 clocks per byte. ACK = MISO low on the first clock of a
  byte only, as in 1-bit; NAK'd reads/writes retried by raising SS_n, no loss.

  100 MB runs, SCLK 30 MHz (H 3, L 2), input-sync bypass on, every byte verified + CRC-32:

  | Direction | Mac path | Time | Rate |
  |---|---|---|---|
  | Pico → Mac | Apple `/dev/cu.usbserial-BENCH1` | 18.40 s | 5.70 MB/s |
  | Pico → Mac | libusb (pyusb bulk read) | 9.32 s | **11.25 MB/s** |
  | Mac → Pico | Apple serial node | 11.27 s | 9.31 MB/s |
  | Mac → Pico | libusb (pyusb bulk write) | 12.74 s | 8.23 MB/s |

  20 MB sweeps (all verified clean), MB/s:

  | SCLK | Pico → Mac, Apple | Pico → Mac, libusb | Mac → Pico, Apple |
  |---|---|---|---|
  | 5 MHz | 2.50 | | 2.45 |
  | 10 MHz | 4.99 | | 4.48 |
  | 18.75 MHz | 5.5–5.8 | 7.86 | 7.59 |
  | 25 MHz | 5.50 | 9.47 | |
  | 30 MHz | 5.6–5.8 | 11.11 | 9.16 |

  How the test avoids the CPU: Pico → Mac replays two pre-generated 128 KB pseudorandom blocks
  by DMA, each pass stamped with its number; the RP2350 **DMA sniffer** computes CRC-32 in
  hardware (matches zlib with CALC = 1, OUT_REV, OUT_INV, seed 0xFFFFFFFF; SNIFF_CTRL at DMA
  base + 0x454). Mac → Pico sends one stamped 64 KB block repeatedly; the Pico memcmp's each
  block while the next arrives. Python's gap between DMA passes is ~65 µs.

  Findings:
  - **Apple's serial driver caps device → host at about 5.8 MB/s.** The same hardware delivers
    11.25 MB/s through libusb. libusb bulk I/O works without sudo while Apple's driver is
    attached, as long as the tty is not open. This bears on phase 4's macOS data-path choice.
  - Pico → Mac via libusb still rises with SCLK at 30 MHz, so the link (plus NAK retries), not
    USB, is the limit there. The write program costs 11 cycles per byte at H 3, L 2 (ceiling
    13.6 MB/s); the read program 10 (15 MB/s). Mac → Pico at 8–9 MB/s is below its link
    ceiling, so that direction is host/USB/FT232H limited; not investigated further.
  - **PIO trap:** an `in` with autopush that stalls on a full RX FIFO applies its side-set
    immediately but samples when the stall ends. Combined with a clock edge it corrupted one
    byte per stall. Fixed with plain `in` + separate blocking `push` (comment in the source).
  - Read and write programs are 20 + 28 instructions: they do not fit PIO1's 32 slots together.
    The real firmware must swap them or shrink them.
  - Harness bugs that looked like link problems, for the record: stale bytes left in the
    FT232H after a failed run; pyserial copying the whole remaining buffer on each partial
    write (made a 100 MB write crawl and capped Mac → Pico at ~3 MB/s). One early 20 MB
    Mac → Pico run had a CRC mismatch under an older test that only checked the first block
    bytewise; never reproduced once every block was checked. Treat as unexplained.
  - Once, after a writer was killed mid-transfer, small writes to the serial node stopped
    reaching the FT232H until a USB reset (`FtdiEeprom.reset_device()`).
  Still open: series resistors are not fitted on the breadboard; SS_n setup/hold margins and
  H/L splits other than (3, 2) at 30 MHz untested in 4-bit; no bit-error-rate figure, only
  "0 errors in N bytes"; flush command latency; Windows.
  **Next (owner to choose):** fold the durable findings into `design_docs/3-driver/NOTES.md`,
  `docs/decisions.md` and `USAGE.md` on main; or continue to pico-sdk firmware.
