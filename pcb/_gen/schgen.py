"""Small helper for writing a populated KiCad 9 schematic sheet from Python.

Each part pin gets a short stub; the stub end carries a net: a power symbol for global rails
and GND, a hierarchical label for sheet ports, a no-connect flag for "NC", or a local label.
"""
import math, os, re, uuid

KLIB = os.environ.get("KICAD_SYMBOL_DIR", "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols")
PCB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ_LIB = os.path.join(PCB_DIR, "scsi-adapter.kicad_sym")
G = 2.54


def U():
    return str(uuid.uuid4())


def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def f(v):
    v = round(v, 4)
    return f"{v:.4f}".rstrip("0").rstrip(".") if v != 0 else "0"


def _extract(text, name):
    i = text.index(f'\n\t(symbol "{name}"\n') + 1
    d, j = 0, i
    while True:
        c = text[j]
        if c == '"':
            j = text.index('"', j + 1)
            while text[j - 1] == '\\':
                j = text.index('"', j + 1)
        elif c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d == 0:
                return text[i:j + 1]
        j += 1


_libcache = {}


def _extract_block(text, i):
    """Balanced s-expression starting at text[i] == '('."""
    d, j = 0, i
    while True:
        c = text[j]
        if c == '"':
            j = text.index('"', j + 1)
            while text[j - 1] == '\\':
                j = text.index('"', j + 1)
        elif c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d == 0:
                return text[i:j + 1]
        j += 1


def libsym(lib_id):
    """Return (embedded symbol text, pins). Derived symbols (extends) are flattened onto their base.
    pins: number -> (x, y, angle, type, unit); unit 0 = common to all units."""
    lib, name = lib_id.split(":")
    path = PROJ_LIB if lib == "scsi-adapter" else f"{KLIB}/{lib}.kicad_sym"
    if path not in _libcache:
        _libcache[path] = open(path).read()
    body = _extract(_libcache[path], name)
    ext = re.search(r'\(extends "([^"]+)"\)', body)
    if ext:
        base = ext.group(1)
        derived = body
        body = _extract(_libcache[path], base).replace(f'"{base}_', f'"{name}_')
        body = body.replace(f'(symbol "{base}"', f'(symbol "{name}"', 1)
        # the derived symbol's fields override the base's (what KiCad does when it flattens)
        for m in re.finditer(r'\n\t\t\(property "([^"]+)"', derived):
            dprop = _extract_block(derived, m.start() + 3)
            bm = re.search(r'\n\t\t\(property "' + re.escape(m.group(1)) + '"', body)
            if bm:
                bprop = _extract_block(body, bm.start() + 3)
                body = body.replace(bprop, dprop, 1)
            else:
                i = body.index("\n\t\t(symbol ")
                body = body[:i] + "\n\t\t" + dprop + body[i:]
    pins = {}
    unit = 0
    for m in re.finditer(r'\(symbol "[^"]+_(\d+)_\d+"|\(pin (\w+) \w+\s+\(at ([-\d.]+) ([-\d.]+) (\d+)\)[\s\S]*?\(number "([^"]*)"', body):
        if m.group(1) is not None:
            unit = int(m.group(1))
            continue
        pins.setdefault(m.group(6), (float(m.group(3)), float(m.group(4)), int(m.group(5)), m.group(2), unit))
    embedded = body.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)
    return embedded, pins


def rot(x, y, a):
    r = math.radians(a)
    return (x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r))


FONT = '(effects (font (size 1.27 1.27)){extra})'


class Sheet:
    def __init__(self, uuid_, paper, title, inst_path, project="scsi-adapter"):
        self.uuid, self.paper, self.title, self.path, self.project = uuid_, paper, title, inst_path, project
        self.libs = {}
        self.items = []
        self.intended = {}          # (ref, pin) -> net
        self.pwr_n = 0
        self.rails = set()
        self.hier = {}              # name -> shape

    # ---------- primitives ----------
    def text(self, s, x, y, size=1.27, bold=False):
        b = " (bold yes)" if bold else ""
        self.items.append(f'\t(text {q(s)} (exclude_from_sim no) (at {f(x)} {f(y)} 0) '
                          f'(effects (font (size {size} {size}){b}) (justify left top)) (uuid {q(U())}))\n')

    def wire(self, x1, y1, x2, y2):
        self.items.append(f'\t(wire (pts (xy {f(x1)} {f(y1)}) (xy {f(x2)} {f(y2)})) '
                          f'(stroke (width 0) (type default)) (uuid {q(U())}))\n')

    def rect(self, x1, y1, x2, y2):
        self.items.append(f'\t(rectangle (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) '
                          f'(stroke (width 0.254) (type dash)) (fill (type none)) (uuid {q(U())}))\n')

    def junction(self, x, y):
        self.items.append(f'\t(junction (at {f(x)} {f(y)}) (diameter 0) (color 0 0 0 0) (uuid {q(U())}))\n')

    def note(self, s, x, y):
        self.items.append(f'\t(text {q(s)} (exclude_from_sim no) (at {f(x)} {f(y)} 0) '
                          f'(effects (font (size 1.016 1.016) (italic yes)) (justify left top)) (uuid {q(U())}))\n')

    def _lib(self, lib_id):
        if lib_id not in self.libs:
            self.libs[lib_id] = libsym(lib_id)
        return self.libs[lib_id]

    def _symbol(self, lib_id, ref, value, x, y, a, props, fields_at, dnp=False, hide_ref=False,
                in_bom=True, on_board=True, unit=1):
        emb, pins = self._lib(lib_id)
        (rx, ry, rj), (vx, vy, vj) = fields_at
        hr = " (hide yes)" if hide_ref else ""
        fa = a if a in (90, 270) else 0
        s = [f'\t(symbol (lib_id {q(lib_id)}) (at {f(x)} {f(y)} {a}) (unit {unit}) (exclude_from_sim no) '
             f'(in_bom {"yes" if in_bom else "no"}) (on_board {"yes" if on_board else "no"}) '
             f'(dnp {"yes" if dnp else "no"}) (uuid {q(U())})\n',
             f'\t\t(property "Reference" {q(ref)} (at {f(rx)} {f(ry)} {fa}) '
             f'{FONT.format(extra=(f" (justify {rj})" if rj else "") + hr)})\n',
             f'\t\t(property "Value" {q(value)} (at {f(vx)} {f(vy)} {fa}) '
             f'{FONT.format(extra=f" (justify {vj})" if vj else "")})\n']
        for k, v in props.items():
            s.append(f'\t\t(property {q(k)} {q(v)} (at {f(x)} {f(y)} 0) {FONT.format(extra=" (hide yes)")})\n')
        for num, pv in pins.items():
            if pv[4] in (0, unit):
                s.append(f'\t\t(pin {q(num)} (uuid {q(U())}))\n')
        s.append(f'\t\t(instances (project {q(self.project)} (path {q(self.path)} '
                 f'(reference {q(ref)}) (unit {unit}))))\n\t)\n')
        self.items.append("".join(s))
        return pins

    def pin_pos(self, pins, num, x, y, a):
        px, py, pa = pins[num][:3]
        dx, dy = rot(px, py, a)
        out = (pa + a + 180) % 360           # direction away from the body
        return x + dx, y - dy, out

    # ---------- net attachment ----------
    def attach(self, net, x, y, d, stub=G):
        """Attach net at a pin end (x, y) whose outward direction is d (0 right, 90 up, ...)."""
        if net == "NC":
            self.items.append(f'\t(no_connect (at {f(x)} {f(y)}) (uuid {q(U())}))\n')
            return
        if net is None:
            return
        ux, uy = rot(1, 0, d)
        ex, ey = x + ux * stub, y - uy * stub
        self.wire(x, y, ex, ey)
        if (net == "GND" or net in self.rails) and d in (0, 180):
            nd = 270 if net == "GND" else 90
            ny = ey + (G if nd == 270 else -G)
            self.wire(ex, ey, ex, ny)
            ex, ey, d = ex, ny, nd
        self.net_at(net, ex, ey, d)

    def net_at(self, net, x, y, d):
        if net == "GND" or net in self.rails:
            self.power(net, x, y, d)
        elif net in self.hier:
            ang, j = {0: (0, "left"), 180: (180, "right"), 90: (0, "left"), 270: (0, "left")}[d]
            self.items.append(f'\t(hierarchical_label {q(net)} (shape {self.hier[net]}) (at {f(x)} {f(y)} {ang}) '
                              f'{FONT.format(extra=f" (justify {j})")} (uuid {q(U())}))\n')
        else:
            ang, j = (180, "right bottom") if d == 180 else (0, "left bottom")
            self.items.append(f'\t(label {q(net)} (at {f(x)} {f(y)} {ang}) '
                              f'{FONT.format(extra=f" (justify {j})")} (uuid {q(U())}))\n')

    def power(self, net, x, y, d):
        lib_id = "power:GND" if net == "GND" else "power:+5V"
        a = (d - 270) % 360 if net == "GND" else (d - 90) % 360
        self.pwr_n += 1
        ref = f"#PWR{self.refbase + self.pwr_n:03d}"
        # value text sits beyond the symbol body
        ux, uy = rot(1, 0, d)
        tx, ty = x + ux * (5.08 if net == "GND" else 3.81), y - uy * (5.08 if net == "GND" else 3.81)
        self._symbol(lib_id, ref, net, x, y, a, {"Footprint": "", "Datasheet": "", "Description": ""},
                     ((x, y, "left"), (tx, ty, "left" if d == 0 else "right" if d == 180 else "")),
                     hide_ref=True, in_bom=False, on_board=False)

    # ---------- parts ----------
    def part(self, lib_id, ref, value, x, y, nets, a=0, props=None, dnp=False, fields=None, stub=G, unit=1):
        props = dict(props or {})
        emb, pins = self._lib(lib_id)
        if fields is None:            # default: to the right of the body
            fields = ((x + 2.54, y - 1.27, "left"), (x + 2.54, y + 1.27, "left"))
        elif fields == "left":
            fields = ((x - 2.54, y - 1.27, "right"), (x - 2.54, y + 1.27, "right"))
        self._symbol(lib_id, ref, value, x, y, a, props, fields, dnp=dnp, unit=unit)
        pins = {k: v for k, v in pins.items() if v[4] in (0, unit)}
        for num, net in nets.items():
            assert num in pins, (ref, num)
            px, py, d = self.pin_pos(pins, num, x, y, a)
            self.attach(net, px, py, d, stub)
            if net not in (None, "NC"):
                self.intended[(ref, num)] = net
        missing = set(pins) - set(nets)
        assert not missing, (ref, missing)
        return pins

    def pwr_flag(self, ref, net, x, y):
        emb, pins = self._lib("power:PWR_FLAG")
        self._symbol("power:PWR_FLAG", ref, "PWR_FLAG", x, y, 0, {"Footprint": "", "Datasheet": "", "Description": ""},
                     ((x, y - 5.08, "left"), (x, y - 5.08, "")), hide_ref=True, in_bom=False, on_board=False)
        self.attach(net, x, y, 270)

    # ---------- output ----------
    def write(self, path, date="2026-09-26"):
        out = [f'(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n\t(generator_version "9.0")\n'
               f'\t(uuid {q(self.uuid)})\n\t(paper {q(self.paper)})\n\t(title_block\n\t\t(title {q(self.title)})\n'
               f'\t\t(date {q(date)})\n\t\t(rev "0.1")\n\t)\n\t(lib_symbols\n']
        for emb, _ in self.libs.values():
            out.append("\t" + emb.replace("\n", "\n\t") + "\n")
        out.append("\t)\n")
        out.extend(self.items)
        out.append('\t(embedded_fonts no)\n)\n')
        open(path, "w").write("".join(out))
