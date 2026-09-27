# Third-party material in the PCB

## Raspberry Pi RP2350B Minimal design (R4-S1)

Source: `RP-010329-CA-1-RP2350B Minimal KiCAD.zip`, linked from *Hardware design with RP2350* §1
(see `docs/sources.md`). Derived from it:

- The placement and support routing of the RP2350B block in `scsi-adapter.kicad_pcb` (U401 and its regulator,
  decoupling, crystal, QSPI flash, USB series resistors, and the local copper pours), rotated 135° and adapted to
  our 4-layer stackup and parts.
- The land patterns of `scsi-adapter.pretty/C_0402_1005Metric_Wide` and
  `scsi-adapter.pretty/L_Abracon_AOTA-B201610_2.0x1.6mm_Polarized`.

Copyright (c) 2026 Raspberry Pi Ltd

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
