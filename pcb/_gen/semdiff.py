"""Semantic diff of two KiCad schematic files: parts, texts, wires, labels, junctions.
Used by build.py to find hand edits made in KiCad before regenerating a sheet."""
import re, sys
from schgen import _extract_block


def items(t):
    out = {"sym": {}, "text": {}, "wire": set(), "label": set(), "junction": set(), "rect": set(), "nc": set()}
    i = 0
    top = t.index("(lib_symbols")
    top = top + len(_extract_block(t, top))
    j = top
    while True:
        k = t.find("\n\t(", j)
        if k < 0: break
        blk = _extract_block(t, k + 2)
        j = k + 2 + len(blk)
        kind = re.match(r'\((\w+)', blk).group(1)
        num = lambda s: tuple(round(float(x), 2) for x in s.split())
        if kind == "symbol":
            ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
            unit = re.search(r'\(unit (\d+)\)', blk).group(1)
            at = num(re.search(r'\(at ([-\d. ]+)\)', blk).group(1))
            props = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', blk))
            val = re.search(r'\(property "Value" "([^"]*)"', blk).group(1)
            dnp = re.search(r'\(dnp (\w+)\)', blk).group(1)
            props = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', blk))
            key = ref + "/" + unit
            if ref.startswith("#"): key = ("pwr", props.get("Value"), at)
            out["sym"][key] = (at, val, dnp, tuple(sorted((k, v) for k, v in props.items() if k not in ("Reference",))))
        elif kind == "text":
            s = re.search(r'\(text "((?:[^"\\]|\\.)*)"', blk).group(1)
            out["text"][s] = num(re.search(r'\(at ([-\d. ]+)\)', blk).group(1))
        elif kind == "wire":
            pts = tuple(sorted(num(x) for x in re.findall(r'\(xy ([-\d. ]+)\)', blk)))
            out["wire"].add(pts)
        elif kind in ("label", "hierarchical_label"):
            n = re.search(r'label "([^"]+)"', blk).group(1)
            out["label"].add((kind, n, num(re.search(r'\(at ([-\d. ]+)\)', blk).group(1))[:2]))
        elif kind == "junction":
            out["junction"].add(num(re.search(r'\(at ([-\d. ]+)\)', blk).group(1)))
        elif kind == "rectangle":
            out["rect"].add(blk.count("("))
        elif kind == "no_connect":
            out["nc"].add(num(re.search(r'\(at ([-\d. ]+)\)', blk).group(1)))
    return out
def fingerprint(path):
    """Hash of a schematic's content (ignores UUIDs and KiCad's formatting)."""
    import hashlib
    it = items(open(path).read())
    norm = {k: sorted(map(repr, v.items() if isinstance(v, dict) else v)) for k, v in it.items()}
    return hashlib.sha256(repr(sorted(norm.items())).encode()).hexdigest()[:16]


def semdiff(path_a, path_b):
    """Differences between path_a (e.g. the file on disk) and path_b (a fresh generation)."""
    out = []
    U = items(open(path_a).read()); Gn = items(open(path_b).read())
    for k in ("sym",):
        for key in sorted(set(U[k]) | set(Gn[k]), key=str):
            a, b = U[k].get(key), Gn[k].get(key)
            if a != b:
                if a and b:
                    diffs = [n for n, x, y in zip(("at", "value", "dnp", "props"), a, b) if x != y]
                    out.append(("SYM changed", key, diffs, a[0], "->gen", b[0]) if "props" not in diffs else ("SYM changed", key, diffs, set(a[3]) ^ set(b[3])))
                else:
                    out.append(("SYM only in", "disk" if a else "gen", key))
    for s in sorted(set(U["text"]) - set(Gn["text"])): out.append(("TEXT only on disk:", repr(s[:120]), U["text"][s]))
    for s in sorted(set(Gn["text"]) - set(U["text"])): out.append(("TEXT only in gen: ", repr(s[:120]), Gn["text"][s]))
    for s in sorted(set(U["text"]) & set(Gn["text"])):
        if U["text"][s] != Gn["text"][s]: out.append(("TEXT moved:", repr(s[:60]), U["text"][s], "->gen", Gn["text"][s]))
    for k in ("wire", "label", "junction", "nc", "rect"):
        a, b = U[k], Gn[k]
        if a - b: out.append((k, "only on disk:", sorted(a - b)[:12], len(a - b)))
        if b - a: out.append((k, "only in gen: ", sorted(b - a)[:12], len(b - a)))
    return out


if __name__ == "__main__":
    for d in semdiff(sys.argv[1], sys.argv[2]):
        print(*d)
