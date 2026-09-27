"""Regenerate the generated schematic sheets and verify them.

    python3 pcb/_gen/build.py            # regenerate every sheet, then ERC + netlist check
    python3 pcb/_gen/build.py --check    # don't write anything; check the files on disk
    python3 pcb/_gen/build.py --force    # overwrite even if a sheet was edited by hand in KiCad

build.py records a content fingerprint of every sheet it writes (fingerprints.json). If a sheet on
disk no longer matches its fingerprint, someone edited it in KiCad: build.py lists the differences and
writes nothing. Fold the edits into the sheet script (texts can go anywhere nearby), then run again.
"""
import importlib, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from netcheck import netcheck
from semdiff import semdiff, fingerprint

SHEETS = ["sheet_1_power", "sheet_2_termpwr"]
CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
ROOT_SCH = os.path.join(PCB, "scsi-adapter.kicad_sch")
FINGERPRINTS = os.path.join(HERE, "fingerprints.json")   # content hash of each sheet as last written


def kicad(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"kicad-cli {' '.join(args)} failed:\n{r.stdout}{r.stderr}")


def main():
    check_only, force = "--check" in sys.argv, "--force" in sys.argv
    tmp = tempfile.mkdtemp()
    last = json.load(open(FINGERPRINTS)) if os.path.exists(FINGERPRINTS) else {}
    intended, pending, edited = {}, [], False
    for name in SHEETS:                       # generate and compare everything before writing anything
        mod = importlib.import_module(name)
        fresh = os.path.join(tmp, mod.FILE)
        intended[mod.FILE] = mod.build(fresh)
        on_disk = os.path.join(PCB, mod.FILE)
        exists = os.path.exists(on_disk)
        # hand-edited = the file on disk no longer matches what build.py last wrote
        hand_edited = exists and mod.FILE in last and fingerprint(on_disk) != last[mod.FILE]
        changed = exists and fingerprint(on_disk) != fingerprint(fresh)
        if check_only:
            state = "hand-edited since last build" if hand_edited else "matches last build"
            print(f"{mod.FILE}: {state}; {'script output differs' if changed else 'script output identical'}")
        elif hand_edited and not force:
            print(f"{mod.FILE} was edited in KiCad since the last build. Differences from the new script output")
            print("(your edits, plus any script changes). Fold the edits into " + name + ".py, or use --force:")
            for d in semdiff(on_disk, fresh):
                print("   ", *d)
            edited = True
        pending.append((fresh, on_disk, mod.FILE))
    if edited:
        sys.exit("Nothing written.")
    if not check_only:
        for fresh, on_disk, file in pending:
            os.replace(fresh, on_disk)
            last[file] = fingerprint(on_disk)
            print(f"{file}: written")
        json.dump(last, open(FINGERPRINTS, "w"), indent=1, sort_keys=True)
    erc = os.path.join(tmp, "erc.rpt")
    kicad("sch", "erc", "--severity-all", "-o", erc, ROOT_SCH)
    rpt = open(erc).read()
    for name in SHEETS:
        mod = importlib.import_module(name)
        sheet = mod.FILE.split("-", 1)[1].rsplit(".", 1)[0]
        sect = rpt.split(f"***** Sheet /{sheet}/")[1].split("***** Sheet")[0] if f"/{sheet}/" in rpt else ""
        items = [l for l in sect.splitlines() if l.startswith("[")]
        print(f"ERC {mod.FILE}: {len(items)} item(s)")
        for l in items:
            print("   ", l)
    net = os.path.join(tmp, "net.net")
    kicad("sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, ROOT_SCH)
    bad = 0
    for file, want in intended.items():
        problems = netcheck(net, want)
        bad += len(problems)
        print(f"netlist {file}: {len({r for r, _ in want})} parts, {len(problems)} problem(s)")
        for p in problems:
            print("   ", p)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
