"""Check a KiCad netlist against a sheet's intended connections: every intended group of pins must be
one net, with no extra pins of those parts on it and no stray connections."""
import re, collections


def netcheck(netlist_path, intended):
    """intended: {(ref, pin): net}. Returns a list of problem strings (empty = pass)."""
    t = open(netlist_path).read()
    t = t[t.index("(nets"):]
    kn = {}
    for block in re.split(r'\n\s*\(net \(code', t)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', block).group(1)
        for r, p in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', block):
            kn[(r, p)] = name
    refs = {r for r, _ in intended}
    groups = collections.defaultdict(set)
    for k, n in intended.items():
        groups[n].add(k)
    problems = []
    for n, g in sorted(groups.items()):
        names = {kn.get(x, "MISSING") for x in g}
        if len(names) != 1:
            problems.append(f"split: {n} -> {sorted(names)}")
            continue
        kname = names.pop()
        extra = {x for x, v in kn.items() if v == kname and x[0] in refs and x not in g}
        if extra:
            problems.append(f"merged: {n} ({kname}) also has {sorted(extra)}")
    for k, v in kn.items():
        if k[0] in refs and k not in intended and not v.startswith("unconnected"):
            problems.append(f"stray: {k} on {v}")
    return problems
