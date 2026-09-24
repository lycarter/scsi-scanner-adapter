"""Tiny ASCII block-diagram library with self-checks.

A page source declares named boxes and the links between them; build.py renders the
art into the page's .md along with a plain-text connection list. To understand a
diagram, read the source or that list; never parse the art.

Conventions in the art: '+' is a corner or a junction (a real connection). A wire that
crosses another without connecting shows as an unbroken '|' (the horizontal one is
drawn behind it).

Checks (they raise DiagramError, so a bad layout never reaches the page):
- boxes may not overlap, and box text must fit;
- text and labels may only be written onto empty cells;
- wires may only cross empty cells (or a frame edge), or cross a perpendicular wire when cross=True;
- a link's first/last point must sit just outside the border of the box it names;
- a '*NET' endpoint must land on an existing wire of that net (drawn as a '+' junction),
  unless that net has no wire yet.
"""


class DiagramError(Exception):
    pass


class Diagram:
    def __init__(self):
        self.cells = {}          # (x, y) -> char
        self.kind = {}           # (x, y) -> 'box' | 'text' | 'h' | 'v' | 'corner' | 'end'
        self.net_of = {}         # (x, y) -> net name, for wire cells
        self.boxes = {}          # id -> (x, y, w, h, lines)
        self.names = {}          # id -> display name for the connection list
        self.links = []          # (a, b, label, arrow)
        self.notes = []

    # ---- low level -------------------------------------------------------
    def _set(self, x, y, ch, kind, net=None):
        self.cells[(x, y)] = ch
        self.kind[(x, y)] = kind
        if net is not None:
            self.net_of[(x, y)] = net

    def _free(self, x, y):
        return (x, y) not in self.cells

    def _text(self, x, y, s, what):
        for i, ch in enumerate(s):
            if ch == ' ':
                continue
            if not self._free(x + i, y):
                raise DiagramError(f"{what} {s!r} at ({x},{y}) overwrites "
                                   f"{self.kind[(x + i, y)]} at ({x + i},{y})")
            self._set(x + i, y, ch, 'text')

    # ---- public API --------------------------------------------------------
    def box(self, id, x, y, w, h, *lines, name=None):
        """A box with its top-left corner at (x, y). Text is left-aligned, one space in.

        name: what the connection list calls it (default: its first non-blank line).
        """
        if id in self.boxes:
            raise DiagramError(f"duplicate box id {id!r}")
        for j in range(y, y + h):
            for i in range(x, x + w):
                if not self._free(i, j):
                    raise DiagramError(f"box {id!r} overlaps {self.kind[(i, j)]} at ({i},{j})")
        if len(lines) > h - 2:
            raise DiagramError(f"box {id!r}: {len(lines)} lines don't fit in height {h}")
        for i in range(x, x + w):
            self._set(i, y, '-', 'box'); self._set(i, y + h - 1, '-', 'box')
        for j in range(y, y + h):
            self._set(x, j, '|', 'box'); self._set(x + w - 1, j, '|', 'box')
        for (i, j) in [(x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)]:
            self._set(i, j, '+', 'box')
        for k, line in enumerate(lines):
            if len(line) > w - 4:
                raise DiagramError(f"box {id!r}: {line!r} is wider than {w - 4}")
            for i, ch in enumerate(line):
                self._set(x + 2 + i, y + 1 + k, ch, 'box')
        self.boxes[id] = (x, y, w, h, lines)
        self.names[id] = name or next((l.strip() for l in lines if l.strip()), id)

    def frame(self, x, y, w, h, title=''):
        """An outline (e.g. the board edge) that other boxes sit inside; wires may cross it."""
        for i in range(x, x + w):
            self._set(i, y, '=', 'frame'); self._set(i, y + h - 1, '=', 'frame')
        for j in range(y, y + h):
            self._set(x, j, '|', 'frame'); self._set(x + w - 1, j, '|', 'frame')
        for (i, j) in [(x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)]:
            self._set(i, j, '+', 'frame')
        if title:
            t = f' {title} '
            for i, ch in enumerate(t):
                self._set(x + (w - len(t)) // 2 + i, y, ch, 'frame')

    def note(self, x, y, *lines):
        """Free text, e.g. a label that belongs to no single link."""
        for k, line in enumerate(lines):
            self._text(x, y + k, line, 'note')
        self.notes.append(' '.join(lines))

    def link(self, a, b, pts, label=None, at=None, arrow='>', cross=False, net=None):
        """A wire from a to b along the polyline pts (orthogonal segments only).

        a, b: a box id, '*NET' (a tap on / start of a named wire), '@Name' (something off the
        page, e.g. '@Host computer'; not checked) or None (a free end).
        arrow: '>' (a to b), '<' (b to a), '<>' (both ways) or None (plain connection).
        net: name this wire so later links can tap it as '*NET' (inferred from a '*' end).
        label: text placed at `at` (x, y); '\\n' makes more lines, stacked below. To place each
        line separately (e.g. above and below the wire), pass at=[(x1, y1), (x2, y2), ...].
        """
        net = net or next((e[1:] for e in (a, b) if isinstance(e, str) and e.startswith('*')), None)
        self._check_end(a, pts[0], 'start')
        self._check_end(b, pts[-1], 'end')
        cells = []
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if x1 != x2 and y1 != y2:
                raise DiagramError(f"link {a}->{b}: segment ({x1},{y1})-({x2},{y2}) isn't straight")
            if (x1, y1) == (x2, y2):   # one-cell link between two touching boxes
                o = 'v' if self.kind.get((x1, y1 - 1)) == 'box' else 'h'
            else:
                o = 'h' if y1 == y2 else 'v'
            n = max(abs(x2 - x1), abs(y2 - y1))
            dx, dy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
            for s in range(n + (1 if (x2, y2) == pts[-1] else 0)):
                cells.append((x1 + dx * s, y1 + dy * s, o))
        corners = set(pts[1:-1])
        for (x, y, o) in cells:
            p = (x, y)
            is_end = p in (pts[0], pts[-1])
            if is_end and not self._free(x, y):
                # tap onto an existing wire of the same net
                if net and self.net_of.get(p) == net:
                    self._set(x, y, '+', 'corner', net)
                    continue
                raise DiagramError(f"link {a}->{b}: endpoint {p} lands on {self.kind[p]}")
            if self.kind.get(p) == 'frame':   # wires pass through the board edge
                self._set(x, y, '-' if o == 'h' else '|', o, net)
                continue
            if not self._free(x, y):
                k = self.kind[p]
                if cross and k in ('h', 'v') and k != o:
                    self._set(x, y, '|', 'x')
                    continue
                if net and self.net_of.get(p) == net and k in ('h', 'v', 'corner'):
                    self._set(x, y, '+', 'corner', net)
                    continue
                raise DiagramError(f"link {a}->{b}: wire at {p} hits {k}"
                                   + ("" if k not in ('h', 'v') else " (pass cross=True to cross it)"))
            if p in corners:
                self._set(x, y, '+', 'corner', net)
            else:
                self._set(x, y, '-' if o == 'h' else '|', o, net)
        if len(pts) == 1 or pts[0] == pts[-1]:
            # one-cell link: the arrow points from box a's side toward box b's side
            ax, ay = self._centre(a); bx, by = self._centre(b)
            pts = [pts[0], pts[0]]
            prev_fwd = (pts[0][0] - (bx > ax) + (bx < ax), pts[0][1] - (by > ay) + (by < ay)) \
                if (ax, ay) != (bx, by) else pts[0]
            fwd = [prev_fwd, pts[0]]
            back = [(2 * pts[0][0] - prev_fwd[0], 2 * pts[0][1] - prev_fwd[1]), pts[0]]
        else:
            fwd, back = [pts[-2], pts[-1]], [pts[1], pts[0]]
        # on a tap, put the arrowhead one cell back so the '+' junction stays visible
        for want, (frm, to) in (('>', fwd), ('<', back)):
            if arrow not in (want, '<>'):
                continue
            if self.kind.get(to) == 'corner':
                step = ((frm[0] > to[0]) - (frm[0] < to[0]), (frm[1] > to[1]) - (frm[1] < to[1]))
                to = (to[0] + step[0], to[1] + step[1])
                if self.kind.get(to) == 'corner':
                    continue
            self._arrow(frm, to)
        if label:
            if at is None:
                raise DiagramError(f"link {a}->{b}: label {label!r} needs at=(x, y)")
            lines = label.split('\n')
            spots = at if isinstance(at, list) else [(at[0], at[1] + k) for k in range(len(lines))]
            if len(spots) != len(lines):
                raise DiagramError(f"link {a}->{b}: {len(lines)} label lines but {len(spots)} positions")
            for (lx, ly), line in zip(spots, lines):
                self._text(lx, ly, line, 'label')
        self.links.append((a, b, label, arrow))

    # ---- helpers -------------------------------------------------------------
    def _arrow(self, frm, to):
        (x1, y1), (x2, y2) = frm, to
        ch = '>' if x2 > x1 else '<' if x2 < x1 else 'v' if y2 > y1 else '^'
        self._set(x2, y2, ch, 'end')

    def _check_end(self, e, p, which):
        if e is None or e[0] in '*@':
            return
        if e not in self.boxes:
            raise DiagramError(f"unknown box {e!r}")
        x, y, w, h, _ = self.boxes[e]
        px, py = p
        beside = (px in (x - 1, x + w) and y < py < y + h - 1) or \
                 (py in (y - 1, y + h) and x < px < x + w - 1)
        if not beside:
            raise DiagramError(f"link {which} {p} doesn't touch box {e!r} "
                               f"(x {x}..{x + w - 1}, y {y}..{y + h - 1})")

    def _centre(self, e):
        if e in self.boxes:
            x, y, w, h, _ = self.boxes[e]
            return (x + w / 2, y + h / 2)
        return (0, 0)

    def _name(self, e):
        if e is None:
            return '(free end)'
        if e.startswith('*'):
            return f'{e[1:]} (net)'
        if e.startswith('@'):
            return e[1:]
        return self.names[e]

    # ---- output --------------------------------------------------------------
    def render(self):
        W = max(x for x, _ in self.cells) + 1
        H = max(y for _, y in self.cells) + 1
        g = [[' '] * W for _ in range(H)]
        for (x, y), ch in self.cells.items():
            if x < 0 or y < 0:
                raise DiagramError(f"cell at negative coordinate ({x},{y})")
            g[y][x] = ch
        return '\n'.join(''.join(r).rstrip() for r in g)

    def connections(self):
        sym = {'>': '→', '<': '←', '<>': '↔', None: '—'}
        out = []
        for a, b, label, arrow in self.links:
            s = f"{self._name(a)} {sym[arrow]} {self._name(b)}"
            if label:
                s += ": " + ' '.join(label.split())
            out.append(s)
        return out
