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

The firmware-controlled positions (DIP 2) apply only if the board has the optional GPIO
expander fitted. Without it, DIP 2 does nothing.
