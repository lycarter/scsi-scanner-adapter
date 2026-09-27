# Generated schematic sheets

Some sheets are written by Python scripts here rather than drawn by hand, and each script is checked
against KiCad's own netlist. Sheets generated so far: `1-power`, `2-termpwr`, `3-scsi` (with the channel sheets
`scsi_line_bidir` and `scsi_line_in`), `4-rp2350`.

```
python3 pcb/_gen/build.py            # regenerate, then ERC + netlist check
python3 pcb/_gen/build.py --check    # write nothing; report whether each sheet still matches its script
python3 pcb/_gen/build.py --force    # overwrite hand edits (they are lost)
```

## How it fits together

- `sheet_N_name.py`: one per sheet. `build(path)` places the parts, wires and notes, and returns the
  *intended* connections as `{(ref, pin): net}`.
- `schgen.py`: the drawing helpers (parts, stubs, power symbols, labels, boxes, notes).
- `netcheck.py`: exports KiCad's netlist and checks that every intended group of pins is exactly one
  net, with nothing extra. This is the real test: a stub that misses a pin, or a wire that touches
  the wrong one, shows up here.
- `semdiff.py`: compares two schematic files by content (parts, texts, wires, labels), ignoring
  UUIDs and KiCad's formatting.

## Editing a generated sheet

Either edit the script and run `build.py`, or edit in KiCad. If you edit in KiCad, `build.py` notices (the sheet
no longer matches the fingerprint in `fingerprints.json` from the last build), refuses to overwrite
it, and lists what differs. Copy those changes into the script (a note's exact
position doesn't matter; near the same spot is fine), then run it again. Running `--check` after an
edit tells you whether the file on disk still matches its script.

Needs KiCad 9's `kicad-cli` (`KICAD_CLI` overrides the default macOS path) and the KiCad symbol
libraries (`KICAD_SYMBOL_DIR`).
