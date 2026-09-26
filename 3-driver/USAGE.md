# Driver board: usage notes

How to set up and use the board. Design reasoning lives in `NOTES.md`.

## Termination switch

The board has a switchable active terminator. Terminate the board only when it is at a
physical end of the SCSI chain. The bus needs exactly two terminators, one at each end.

| DIP 1 | DIP 2 | Terminator |
|---|---|---|
| off | off | off, fixed |
| off | on | off by default; firmware can turn it on |
| on | off | on, fixed |
| on | on | on by default; firmware can turn it off |

- **End of chain (the usual setup):** use DIP 1 on (10 or 11). With DIP 2 off, the
  terminator stays on even when the board is unpowered, as long as TERMPWR is on the bus.
- **Mid-chain:** use off, fixed (00).
- **Caution for 01 (off by default, firmware may turn it on):** if the board is unpowered
  while another device supplies TERMPWR, the terminator can switch on by itself. Mid-chain,
  that gives the bus three terminators, which usually still works but can make transfers
  flaky. It doesn't damage anything. If the board is mid-chain and might be off, use 00.

The firmware-controlled positions (DIP 2) need the I²C GPIO expander, which is fitted as
standard. It is removed only in the FT1248/FIFO rework fallback; after that, DIP 2 does nothing.

## Power

- **USB-C is always connected**: it's the data link. On a port that offers ≥ 1.5 A (USB-C
  current advertisement), the board also supplies TERMPWR from USB.
- **Bench supply for extra current:** connect a 5 V supply to the screw terminal when the USB
  port can't do 1.5 A (e.g. a 500 mA port). While it's present, the bench supply powers the
  whole board, TERMPWR included; USB then carries data only.
  - Set it to **5.0 V** (5.1 V at most) and at least a 2.5 A current limit. The board's
    over-voltage cut-off is 5.14–5.59 V, and above it the bench input shuts off until the
    voltage drops below ~4.9 V.
  - Reversed leads and adapters up to 24 V are survivable, but don't try them on purpose.
  - Switch the bench supply off before switching off or sleeping the computer. With the bench
    on and the host off, the hub's D+ pull-up feeds a small current into the powered-down host
    (a known minor flaw).
- **Cables:** use a USB-C to C cable. A legacy USB-A to C cable reads as "default current", so
  TERMPWR stays off unless the bench supply is connected. A *non-compliant* A-to-C cable (10 kΩ
  pull-up) reads as 3 A and could overload a USB-A port: avoid unknown cables.
- The board draws ~0.2 A while the host has the USB bus suspended (outside the USB suspend
  limit, like most bus-powered hubs).

## First programming (fresh board)

1. **RP2350:** plug in USB-C. With blank flash the RP2350 comes up in its ROM bootloader
   (BOOTSEL) behind the on-board hub. Copy a UF2 onto the `RP2350` drive, or use
   `picotool load -x firmware.uf2`. Later updates: `picotool reboot -f -u`, then load. If USB
   doesn't work, use SWD (Tag-Connect TC2030 + J-Link) or hold BOOTSEL while pressing RUN.
2. **FT232H EEPROM** (93LC56B, blank from the factory; the FT232H can't be bricked by bad
   EEPROM contents, it falls back to defaults on a bad checksum):
   - Easiest: on a Windows PC, run FTDI's FT_PROG once: port A type **FT1248**, FT1248 clock
     polarity / bit order / flow control per the firmware, "Suspend on ACBus7 Low" **off**,
     self-powered, max power ~100 mA. Program, then save the 256-byte image.
   - From macOS: write the saved image with libftdi's `ftdi_eeprom` (`flash_raw = true`,
     `eeprom_type = 0x56`), run as root (Apple's built-in FTDI driver holds the interface).
     `ftdi_eeprom` can't set the FT1248 option bits itself, only the mode.
   - Check on the bench: with SS_n high and flow control on, MISO follows RXF# and MIOSIO0
     follows TXE#.
3. The firmware leaves the FT1248 pins as inputs until it has confirmed FT1248 mode.

## Bring-up checks (first board)

- 3.3 V rail under load (SD write + TERMPWR on): 3.20–3.40 V. If low, fit a resistor on the
  unfitted 0603 pads across the LDO's lower feedback resistor (1 MΩ raises it ≈ 55 mV).
- Terminator rail 2.72–2.94 V; scope it during G4 captures.
- VBUS at plug-in (no ringing above ~5.8 V at the mux input).
- TERMPWR at the connector under full load with your usual cable (≥ 4.25 V), and TERMPWR at
  plug-in on a 500 mA port (should show no pulse).
- Bench input: under-voltage trip ≈ 4.05–4.41 V and over-voltage trip ≈ 5.14–5.59 V (checks
  the EN Zener's leakage).
- '245 output resistance on one line (open vs. ~21 mA load). If > 22 Ω, change that line's
  resistors to 100 Ω.
- REQ ringing at the connector; data-to-ACK setup at the connector (≥ 55 ns; the firmware
  gives ~107 ns).
- Receiver thresholds: sweep one input slowly at the real 3.3 V.
- Driver gate kick with the board off while the G4 drives the bus: fit the 22 pF gate caps
  only if it shows on the bus edge.
