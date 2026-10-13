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
  After that: Pico firmware (pico-sdk, PIO 1-bit master), loopback to the Mac, then 4-bit.
