"""Choose the RP2350B GPIO 32-46 order that minimises weighted track crossings.

Reasoning and result: ../NOTES.md, "GPIO 32-46 order". Run from anywhere:
    python3 design_docs/3-driver/tools/ft1248_pinsolve.py [--plot out.png]
Needs numpy (and matplotlib for --plot). Reads pad positions from pcb/scsi-adapter.kicad_pcb, so
rerun it when the FT232H, microSD, LA header or expander move.

Model: each net is the shortest path (visibility graph around the RP2350B and FT232H bodies) from
just outside its RP2350B pad to each destination pad. Two paths crossing cost min(weight): the
cheaper net takes the via pair. Shared corner chains are resolved by the order of their arms.
The FT232H is modelled (not read from the board) at a few candidate placements, pins 13-24 facing
the RP2350B; the answer should not depend on which.
"""
import json, math, heapq, itertools, os, re, sys
import numpy as np

PCB = os.path.join(os.path.dirname(__file__), "../../../pcb/scsi-adapter.kicad_pcb")


def read_pads(path=PCB):
    t = open(path).read()
    out = {}
    for f in re.split(r'\n\t\(footprint ', t)[1:]:
        ref = re.search(r'\(property "Reference" "([^"]+)"', f).group(1)
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', f)
        X, Y, th = float(at.group(1)), float(at.group(2)), math.radians(float(at.group(3) or 0))
        pads = {}
        for m in re.finditer(r'\(pad "([^"]*)" \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+)[^)]*\)', f):
            x, y = float(m.group(2)), float(m.group(3))
            pads.setdefault(m.group(1), (X + x * math.cos(th) + y * math.sin(th), Y - x * math.sin(th) + y * math.cos(th)))
        out[ref] = {"at": (X, Y, math.degrees(th)), "pads": pads}
    return out


P = read_pads()
RPC = tuple(P["U401"]["at"][:2])


GPIO_PIN = {32: 40, 33: 42, 34: 43, 35: 44, 36: 45, 37: 46, 38: 47, 39: 48, 40: 49,
            41: 52, 42: 53, 43: 54, 44: 55, 45: 56, 46: 57, 47: 58}


def rot(X, Y, th, x, y):
    t = math.radians(th)
    return (X + x * math.cos(t) + y * math.sin(t), Y - x * math.sin(t) + y * math.cos(t))


def square(X, Y, th, h):
    return [rot(X, Y, th, sx * h, sy * h) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def rp_escape(g):
    x, y = P["U401"]["pads"][str(GPIO_PIN[g])]
    dx, dy = x - RPC[0], y - RPC[1]
    # push outward along the face normal (the dominant local axis of the 45-degree package)
    lx, ly = rot(0, 0, -135, dx, dy)                    # into package frame
    n = (1.0 if lx > 0 else -1.0, 0.0) if abs(lx) > abs(ly) else (0.0, 1.0 if ly > 0 else -1.0)
    ex, ey = rot(0, 0, 135, n[0] * 0.45, n[1] * 0.45)
    return (x + ex, y + ey)


def ft_pads(X, Y, th):
    pads = {}
    for i in range(12):
        off = -2.75 + 0.5 * i
        pads[1 + i] = ((-4.16, off), (-1, 0))
        pads[13 + i] = ((off, 4.16), (0, 1))
        pads[25 + i] = ((4.16, -off), (1, 0))
        pads[37 + i] = ((-off, -4.16), (0, -1))
    out = {}
    for k, ((x, y), (nx, ny)) in pads.items():
        out[k] = rot(X, Y, th, x + 0.5 * nx, y + 0.5 * ny)
    return out


def seg_inter(a, b, c, d):
    """Proper intersection of open segments ab, cd."""
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    d1, d2, d3, d4 = o(c, d, a), o(c, d, b), o(a, b, c), o(a, b, d)
    return (d1 * d2 < -1e-12) and (d3 * d4 < -1e-12)


def seg_hits_poly(a, b, poly):
    """Does segment ab pass through the interior of convex polygon poly (CW or CCW)?"""
    # sample-based is fine at this scale: check midpoints and proper edge crossings
    n = len(poly)
    for i in range(n):
        if seg_inter(a, b, poly[i], poly[(i + 1) % n]):
            return True
    for t in (0.25, 0.5, 0.75):
        p = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        if inside(p, poly):
            return True
    return False


def inside(p, poly):
    s = None
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        c = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        if abs(c) < 1e-9:
            return False
        if s is None:
            s = c > 0
        elif s != (c > 0):
            return False
    return True


class World:
    def __init__(self, ft_xy, ft_th, extra_obst=()):
        self.ft = ft_pads(ft_xy[0], ft_xy[1], ft_th)
        self.obst = [square(RPC[0], RPC[1], 135, 5.3), square(ft_xy[0], ft_xy[1], ft_th, 4.55)] + list(extra_obst)
        self.corners = [c for o in [square(RPC[0], RPC[1], 135, 5.5), square(ft_xy[0], ft_xy[1], ft_th, 4.8)]
                        for c in o]
        self.cache = {}

    def path(self, a, b):
        a, b = tuple(a[:2]), tuple(b[:2])
        key = (a, b)
        if key in self.cache:
            return self.cache[key]
        nodes = [a, b] + self.corners
        ok = lambda p, q: not any(seg_hits_poly(p, q, o) for o in self.obst)
        dist = {0: 0.0}
        prev = {}
        pq = [(0.0, 0)]
        done = set()
        while pq:
            d, i = heapq.heappop(pq)
            if i in done:
                continue
            done.add(i)
            if i == 1:
                break
            for j in range(len(nodes)):
                if j in done or j == i:
                    continue
                if not ok(nodes[i], nodes[j]):
                    continue
                nd = d + math.dist(nodes[i], nodes[j])
                if nd < dist.get(j, 1e18):
                    dist[j] = nd
                    prev[j] = i
                    heapq.heappush(pq, (nd, j))
        seq = [1]
        while seq[-1] != 0:
            seq.append(prev[seq[-1]])
        pl = [nodes[i] for i in reversed(seq)]
        self.cache[key] = (pl, dist[1])
        return self.cache[key]


def ang(v):
    return math.atan2(v[1], v[0])


def crosses(P1, P2):
    n = 0
    # proper intersections
    for i in range(len(P1) - 1):
        for j in range(len(P2) - 1):
            if seg_inter(P1[i], P1[i + 1], P2[j], P2[j + 1]):
                n += 1
    # shared vertices (interior corners only)
    idx2 = {v: j for j, v in enumerate(P2)}
    i = 1
    while i < len(P1) - 1:
        v = P1[i]
        if v not in idx2 or idx2[v] in (0, len(P2) - 1):
            i += 1
            continue
        j = idx2[v]
        # extend the shared chain forward
        step = 0
        if i + 1 < len(P1) and j + 1 < len(P2) and P1[i + 1] == P2[j + 1]:
            step = 1
        elif i + 1 < len(P1) and j - 1 >= 0 and P1[i + 1] == P2[j - 1]:
            step = -1
        k = 0
        if step:
            while (i + k + 1 < len(P1) - 1 and 0 < j + step * (k + 1) < len(P2) - 1
                   and P1[i + k + 1] == P2[j + step * (k + 1)]):
                k += 1
        a0, a1 = i, i + k
        b0, b1 = j, j + step * k
        p_in, p_out = P1[a0 - 1], P1[a1 + 1]
        q_in, q_out = (P2[b0 - 1], P2[b1 + 1]) if step >= 0 else (P2[b0 + 1], P2[b1 - 1])
        if k == 0:
            c = P1[a0]
            arms = sorted([(ang((p[0] - c[0], p[1] - c[1])), t) for p, t in
                           ((p_in, 'p'), (p_out, 'p'), (q_in, 'q'), (q_out, 'q'))])
            s = ''.join(t for _, t in arms)
            if s in ('pqpq', 'qpqp'):
                n += 1
        else:
            s0, s1 = P1[a0], P1[a1]
            d1 = ang((P1[a0 + 1][0] - s0[0], P1[a0 + 1][1] - s0[1]))
            d2 = ang((P1[a1 - 1][0] - s1[0], P1[a1 - 1][1] - s1[1]))
            rel = lambda p, c, d: (ang((p[0] - c[0], p[1] - c[1])) - d) % (2 * math.pi)
            side0 = rel(p_in, s0, d1) < rel(q_in, s0, d1)
            side1 = rel(p_out, s1, d2) < rel(q_out, s1, d2)
            if side0 == side1:
                n += 1
        i = a1 + 1
    return n


# ---------------- signals ----------------
def dests(W):
    ft = W.ft
    J, U5, L3, U4 = P["J501"]["pads"], P["U501"]["pads"], P["J303"]["pads"], P["U403"]["pads"]
    sd = lambda k: (J[k][0], J[k][1] + 1.2)
    return {
        "M0": ft[13], "M1": ft[14], "M2": ft[15], "M3": ft[16], "D4": ft[17], "D5": ft[18], "D6": ft[19],
        "D7": ft[20], "SCLK": ft[21], "SSN": ft[25], "MISO": ft[26], "WR": ft[27],
        "SDA": (U5["23"][0] - 1.2, U5["23"][1]), "SCL": (U5["22"][0] - 1.2, U5["22"][1]),
        "SDCLK": sd("5"), "SDCMD": sd("3"), "SDD0": sd("7"),
        "LA0": (L3["5"][0], L3["5"][1] + 1.5), "LA1": (L3["3"][0], L3["3"][1] + 1.5),
        "TP": (205.0, 62.0), "PSRAM": U4["1"],
    }


W8 = {"M0": 3, "M1": 3, "M2": 3, "M3": 3, "SCLK": 3, "SSN": 3, "MISO": 3, "SDA": 1, "SCL": 1, "SDCLK": 2,
      "SDCMD": 2, "SDD0": 2, "LA0": 1, "LA1": 1, "TP": 0.25, "PSRAM": 2,
      "D4": 1, "D5": 1, "D6": 1, "D7": 1, "WR": 1}          # D4-7/WR = the DNP rework copper
REWORK = ["SDA", "SCL", "SDCLK", "SDCMD", "SDD0"]
GPIOS = list(range(32, 47))


class Evaluator:
    def __init__(self, worlds):
        self.worlds = worlds
        self.D = [dests(W) for W in worlds]
        self.pl = {}
        self.xc = {}

    def poly(self, wi, dest, g):
        k = (wi, dest, g)
        if k not in self.pl:
            self.pl[k] = self.worlds[wi].path(rp_escape(g), self.D[wi][dest])
        return self.pl[k]

    def pair(self, d1, g1, d2, g2):
        if g1 == g2:
            return 0.0
        k = (d1, g1, d2, g2)
        if k in self.xc:
            return self.xc[k]
        c = 0
        for wi in range(len(self.worlds)):
            c += crosses(self.poly(wi, d1, g1)[0], self.poly(wi, d2, g2)[0])
        v = c * min(W8[d1], W8[d2]) / len(self.worlds)
        self.xc[k] = self.xc[(d2, g2, d1, g1)] = v
        return v

    def length(self, d, g):
        return sum(self.poly(wi, d, g)[1] for wi in range(len(self.worlds))) / len(self.worlds)


def wires_of(assign, role):
    """assign: signal -> gpio. role: rework signal -> extra FT dest ('D4'.. or 'WR')."""
    w = [(s, g) for s, g in assign.items()]
    w += [(role[s], assign[s]) for s in role]
    return w


def i2c_ok(a):
    sda, scl = a["SDA"], a["SCL"]
    return (sda % 4 == 0 and scl % 4 == 1) or (sda % 4 == 2 and scl % 4 == 3)


LEN_W = 0.004


def soft(a):
    p = 0.0
    if abs(a["SCLK"] - a["SSN"]) != 1:
        p += 1.0          # 2-pin side-set for FT1248 SCLK + SS_n
    return p


def total(E, a, role):
    w = wires_of(a, role) + [("PSRAM", 47)]
    c = sum(E.pair(*w[i], *w[j]) for i in range(len(w)) for j in range(i + 1, len(w)))
    L = sum(E.length(d, g) * W8[d] for d, g in w)
    return c + LEN_W * L + soft(a), c


def solve(E, orients=("fwd", "rev"), fixed_n=None, verbose=True):
    best = []
    free_sigs = ["SCLK", "SSN", "MISO", "LA0", "LA1", "TP"]
    for orient in orients:
        for n in range(32, 40):
            if fixed_n and n != fixed_n:
                continue
            block = list(range(n, n + 8))
            if orient == "fwd":
                mio = {f"M{k}": n + k for k in range(4)}
                dslots = {f"D{4 + k}": n + 4 + k for k in range(4)}
            else:
                mio = {f"M{k}": n + 7 - k for k in range(4)}
                dslots = {f"D{4 + k}": n + 3 - k for k in range(4)}
            rest = [g for g in GPIOS if g not in block]
            for perm in itertools.permutations(REWORK, 4):
                left = [s for s in REWORK if s not in perm][0]
                role = {perm[k]: f"D{4 + k}" for k in range(4)}
                role[left] = "WR"
                base = dict(mio)
                for k in range(4):
                    base[perm[k]] = dslots[f"D{4 + k}"]
                sigs = free_sigs + [left]
                # fixed wires
                fw = [(s, g) for s, g in base.items()] + [(role[s], base[s]) for s in perm] + [("PSRAM", 47)]
                fc = sum(E.pair(*fw[i], *fw[j]) for i in range(len(fw)) for j in range(i + 1, len(fw)))
                fL = sum(E.length(d, g) * W8[d] for d, g in fw)
                # wires per free signal
                fsw = {s: [s] + (["WR"] if s == left else []) for s in sigs}
                m = len(sigs)
                lin = np.zeros((m, len(rest)))
                for i, s in enumerate(sigs):
                    for j, g in enumerate(rest):
                        v = 0.0
                        for d in fsw[s]:
                            v += sum(E.pair(d, g, d2, g2) for d2, g2 in fw) + LEN_W * E.length(d, g) * W8[d]
                        if s == "TP" and g < 40:
                            v += 1e6
                        lin[i, j] = v
                quad = {}
                for i in range(m):
                    for k in range(i + 1, m):
                        M = np.zeros((len(rest), len(rest)))
                        for j, g in enumerate(rest):
                            for l, g2 in enumerate(rest):
                                if j == l:
                                    continue
                                M[j, l] = sum(E.pair(d, g, d2, g2) for d in fsw[sigs[i]] for d2 in fsw[sigs[k]])
                        quad[(i, k)] = M
                perms = np.array(list(itertools.permutations(range(len(rest)))))
                cost = np.full(len(perms), fc + LEN_W * fL)
                for i in range(m):
                    cost += lin[i, perms[:, i]]
                for (i, k), M in quad.items():
                    cost += M[perms[:, i], perms[:, k]]
                # soft + I2C feasibility, only on the best few
                order = np.argsort(cost)[:400]
                for oi in order:
                    a = dict(base)
                    for i, s in enumerate(sigs):
                        a[s] = rest[perms[oi, i]]
                    if not i2c_ok(a):
                        continue
                    t = cost[oi] + soft(a)
                    best.append((t, orient, n, a, role))
                    break
    best.sort(key=lambda b: b[0])
    return best


def show(E, b):
    t, orient, n, a, role = b
    tot, c = total(E, a, role)
    print(f"cost {tot:.2f}  crossings(weighted) {c:.2f}  orient={orient} base={n}")
    inv = {g: s for s, g in a.items()}
    for g in range(32, 48):
        s = inv.get(g, "PSRAM" if g == 47 else "?")
        print(f"  GPIO{g:2d} pin{GPIO_PIN[g]:2d}  {s:6s} {('-> FT ' + role[s]) if s in role else ''}")




def breakdown(E, a, role):
    from collections import Counter
    w = wires_of(a, role) + [("PSRAM", 47)]
    cnt = Counter()
    for i in range(len(w)):
        for j in range(i + 1, len(w)):
            v = E.pair(*w[i], *w[j])
            if v:
                cnt[f"{w[i][0]}@{w[i][1]} x {w[j][0]}@{w[j][1]}"] += v
    return cnt


def plot(E, a, role, fn, wi=0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    W = E.worlds[wi]
    fig, ax = plt.subplots(figsize=(14, 9))
    for o in W.obst:
        xs, ys = zip(*(o + [o[0]]))
        ax.plot(xs, ys, "k-")
    col = {"M": "tab:blue", "D": "tab:cyan", "W": "tab:cyan", "S": "tab:green", "L": "tab:purple",
           "T": "tab:red", "P": "tab:orange"}
    for d, g in wires_of(a, role) + [("PSRAM", 47)]:
        pl = E.poly(wi, d, g)[0]
        xs, ys = zip(*pl)
        c = col.get(d[0], "k")
        if d in ("SSN", "SCLK", "SDA", "SCL"):
            c = {"SSN": "navy", "SCLK": "navy", "SDA": "olive", "SCL": "olive"}[d]
        ax.plot(xs, ys, color=c, lw=1, ls="--" if d[0] in "DW" and len(d) <= 2 else "-")
        ax.text(pl[0][0], pl[0][1], f"{g}", fontsize=6)
        ax.text(pl[-1][0], pl[-1][1], d, fontsize=6)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    fig.savefig(fn, dpi=110)


CURRENT = {"LA1": 32, "LA0": 33, "SDD0": 34, "MISO": 35, "SSN": 36, "SCLK": 37, "M0": 38, "M1": 39, "M2": 40,
           "M3": 41, "SDA": 42, "SCL": 43, "SDCLK": 44, "SDCMD": 45, "TP": 46}
CURRENT_ROLE = {"SDA": "D4", "SCL": "D5", "SDCLK": "D6", "SDCMD": "D7", "SDD0": "WR"}

if __name__ == "__main__":
    # candidate FT232H placements: (centre, KiCad rotation); 90 = pins 13-24 facing east
    worlds = [World((117, 62), 90), World((122, 72), 90), World((120, 55), 45)]
    E = Evaluator(worlds)
    print("as drawn (schematic):")
    show(E, (0, "fwd", 38, CURRENT, CURRENT_ROLE))
    orients = ("fwd", "rev") if "--rev" in sys.argv else ("fwd",)   # rev = MIOSIO k on n+7-k
    B = solve(E, orients=orients)
    print("best:")
    show(E, B[0])
    if "--plot" in sys.argv:
        plot(E, B[0][3], B[0][4], sys.argv[sys.argv.index("--plot") + 1])
