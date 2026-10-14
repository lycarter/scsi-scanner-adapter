#!/usr/bin/env python3
"""Build the JLCPCB order files for the driver board: Gerber/drill zip, BOM and CPL.

    python3 tools/jlc_export.py            # stops if DRC or the cross-checks fail
    python3 tools/jlc_export.py --draft    # exports anyway, for looking at the output

The board file is never written. The project is copied to a temp folder, the zones are
refilled there (kicad-cli can't refill, and a stale fill both fails DRC and plots wrong
copper), and everything is exported from that copy.

What JLC assembles is decided by the schematic's `Fit` field: only `Fit` = JLC parts that are
not DNP go into the BOM and CPL. Hand-fit parts (`Fit` = Hand) are left out even though
KiCad doesn't mark them DNP.

JLC's library draws some parts turned or shifted relative to KiCad's footprint. The corrections
seen in JLC's placement preview are in JLC_ROTATION and JLC_OFFSET, keyed by C-number, because a
correction belongs to one JLC part on one KiCad footprint. Every part on the board was checked
in the preview on 2026-10-14; a part added later has not been, so check it there and add it.
"""
import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KICAD = Path("/Applications/KiCad/KiCad.app/Contents")
KICAD_CLI = KICAD / "MacOS/kicad-cli"
KICAD_PYTHON = KICAD / "Frameworks/Python.framework/Versions/Current/bin/python3"

PROJECT = "scsi-adapter"
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"

# Degrees added to KiCad's rotation (counter-clockwise seen from the top), per JLC part.
# From JLC's placement preview, 2026-10-14 (owner).
JLC_ROTATION = {
    "C8545": 180,       # 2N7002, SOT-23 (Q201)
    "C15310": 180,      # FDV301N, SOT-23 (Q901...)
    "C426705": 180,     # 74LVC1G17GW, SOT-353 (U901...)
    "C190271": 180,     # 93LC56BT, SOT-23-6 (U702)
    "C42411119": 180,   # Abracon AOTA-B201610 inductor (L401)
    "C56848": 270,      # TPS73701DCQR, SOT-223-6 (U103, U104)
    "C2652121": 270,    # SN74LVTH245APWR, TSSOP-20 (U301-U303)
    "C465732": 270,     # TCA9555PWR, TSSOP-24 (U501)
    "C97521": 270,      # W25Q128JVSIQ, SOIC-8 5.3 mm (U402)
    "C5333729": 270,    # APS6404L, SOIC-8 3.9 mm (U403)
    "C5373042": 270,    # CH334P, QFN-16 (U601)
    "C3662799": 180,    # TPS259470ARPWR, VQFN-HR-10 (U201 seen; U101 is the same part)
    "C7955": 270,       # LM393DR2G, SOIC-8 (U202)
    "C3235557": 270,    # TPS2116DRLR, SOT-583 (U102)
    "C3113": 180,       # CJ431, SOT-23 (U203)
}

# Where JLC's part origin sits in the KiCad footprint's own coordinates (mm, y down), per JLC part.
# The position file gives the footprint origin; JLC centres its part on its own origin.
JLC_OFFSET = {
    # TF PUSH microSD socket (J501): our origin is on the locating pegs, JLC's is the centre of
    # the pads, 5.5 mm toward the contact row. Confirmed in the preview.
    "C393941": (0.0, -5.5),
}

REFILL = """
import sys, pcbnew
board = pcbnew.LoadBoard(sys.argv[1])
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(sys.argv[1], board)
"""


def run(*cmd):
    result = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"FAILED: {' '.join(str(c) for c in cmd)}\n{result.stdout}{result.stderr}")
    return result.stdout


def natural(ref):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ref)]


def drc_problems(board, work):
    report = work / "drc.json"
    run(KICAD_CLI, "pcb", "drc", "--severity-error", "--format", "json", "-o", report, board)
    data = json.loads(report.read_text())
    problems = []
    for v in data.get("violations", []) + data.get("unconnected_items", []):
        items = "; ".join(f"{i['description']} @ ({i['pos']['x']}, {i['pos']['y']})" for i in v["items"])
        problems.append(f"DRC {v['type']}: {v['description']} [{items}]")
    return problems


def export_gerbers(board, out, work):
    gerbers = work / "gerbers"
    gerbers.mkdir()
    run(KICAD_CLI, "pcb", "export", "gerbers", "-o", gerbers, "--layers", LAYERS,
        "--no-x2", "--no-netlist", "--subtract-soldermask", board)
    run(KICAD_CLI, "pcb", "export", "drill", "-o", str(gerbers) + "/", "--format", "excellon",
        "--excellon-units", "mm", "--excellon-zeros-format", "decimal",
        "--excellon-oval-format", "alternate", "--excellon-separate-th", board)
    files = sorted(p for p in gerbers.iterdir() if p.suffix != ".gbrjob")
    with zipfile.ZipFile(out / f"{PROJECT}-gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.name)
    return [p.name for p in files]


def schematic_parts(schematic, work):
    bom = work / "bom.csv"
    run(KICAD_CLI, "sch", "export", "bom", "-o", bom, "--fields",
        "Reference,Value,Footprint,LCSC,Fit,${DNP}", "--labels", "Reference,Value,Footprint,LCSC,Fit,DNP",
        "--group-by", "", "--ref-range-delimiter", "", schematic)
    with bom.open(newline="") as f:
        return list(csv.DictReader(f))


def board_positions(board, work):
    pos = work / "pos.csv"
    run(KICAD_CLI, "pcb", "export", "pos", "-o", pos, "--format", "csv", "--units", "mm",
        "--side", "both", board)
    with pos.open(newline="") as f:
        return {row["Ref"]: row for row in csv.DictReader(f)}


def write_bom_and_cpl(parts, positions, out):
    problems = []
    fitted = [p for p in parts if p["Fit"] == "JLC" and not p["DNP"]]
    for p in parts:
        if p["Fit"] == "JLC" and p["DNP"]:
            problems.append(f"{p['Reference']}: Fit = JLC but marked DNP")
        if p["Fit"] not in ("JLC", "Hand", "DNP", "None"):
            problems.append(f"{p['Reference']}: unknown Fit value {p['Fit']!r}")

    groups = defaultdict(list)
    for p in fitted:
        ref = p["Reference"]
        if not re.fullmatch(r"C\d+", p["LCSC"]):
            problems.append(f"{ref}: Fit = JLC but LCSC is {p['LCSC']!r}")
        if ref not in positions:
            problems.append(f"{ref}: in the schematic BOM but has no position on the board")
        groups[p["LCSC"]].append(p)

    # One line per C-number: JLC picks the part by that alone. The comment and footprint come
    # from the lowest reference (the schematic spells some values two ways, e.g. "100nF" and
    # "100nF 50V", and C402/C403 use a wider 0402 land pattern for the same capacitor).
    with (out / f"{PROJECT}-bom.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for group in groups.values():
            group.sort(key=lambda p: natural(p["Reference"]))
        for lcsc, group in sorted(groups.items(), key=lambda g: natural(g[1][0]["Reference"])):
            w.writerow([group[0]["Value"], ",".join(p["Reference"] for p in group),
                        group[0]["Footprint"].split(":")[-1], lcsc])

    with (out / f"{PROJECT}-cpl.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for p in sorted((p for p in fitted if p["Reference"] in positions), key=lambda p: natural(p["Reference"])):
            row = positions[p["Reference"]]
            if row["Side"] != "top" and (p["LCSC"] in JLC_ROTATION or p["LCSC"] in JLC_OFFSET):
                problems.append(f"{p['Reference']}: JLC corrections are only worked out for the top side")
            angle = math.radians(float(row["Rot"]))
            dx, dy = JLC_OFFSET.get(p["LCSC"], (0.0, 0.0))
            # footprint frame (y down, rotated counter-clockwise) -> position file frame (y up)
            x = float(row["PosX"]) + dx * math.cos(angle) + dy * math.sin(angle)
            y = float(row["PosY"]) + dx * math.sin(angle) - dy * math.cos(angle)
            rotation = (float(row["Rot"]) + JLC_ROTATION.get(p["LCSC"], 0)) % 360
            w.writerow([p["Reference"], f"{x:.4f}mm", f"{y:.4f}mm",
                        "Top" if row["Side"] == "top" else "Bottom", f"{rotation:g}"])
    return fitted, groups, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pcb-dir", type=Path, default=REPO / "pcb")
    ap.add_argument("--out", type=Path, default=REPO / "pcb" / "fab")
    ap.add_argument("--draft", action="store_true", help="export even if checks fail")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        copy = work / "project"
        shutil.copytree(args.pcb_dir, copy, ignore=shutil.ignore_patterns(
            "*-backups", "*.lck", "fab", "_gen", "fp-info-cache"))
        board = copy / f"{PROJECT}.kicad_pcb"
        # pcbnew's Python occasionally dies here (seen once in five runs, KiCad 9.0.9), so retry.
        for attempt in range(3):
            shutil.copy(args.pcb_dir / board.name, board)
            if subprocess.run([str(KICAD_PYTHON), "-c", REFILL, str(board)], capture_output=True).returncode == 0:
                break
        else:
            sys.exit("FAILED: zone refill (pcbnew Python) failed three times")

        problems = drc_problems(board, work)
        parts = schematic_parts(copy / f"{PROJECT}.kicad_sch", work)
        positions = board_positions(board, work)

        if args.out.exists():
            shutil.rmtree(args.out)
        args.out.mkdir(parents=True)
        gerber_files = export_gerbers(board, args.out, work)
        fitted, groups, bom_problems = write_bom_and_cpl(parts, positions, args.out)
        problems += bom_problems

    print(f"Gerber zip: {len(gerber_files)} files: {', '.join(gerber_files)}")
    print(f"BOM: {len(groups)} lines, {len(fitted)} placements "
          f"({sum(1 for p in parts if p['Fit'] == 'Hand')} hand-fit and "
          f"{sum(1 for p in parts if p['DNP'])} DNP parts left out)")
    for p in problems:
        print("PROBLEM:", p)
    if problems and not args.draft:
        shutil.rmtree(args.out)
        sys.exit(f"{len(problems)} problem(s): nothing exported. Fix them, or use --draft to look at the output.")
    print(f"{'DRAFT (do not order) ' if problems else ''}written to {args.out}")


if __name__ == "__main__":
    main()
