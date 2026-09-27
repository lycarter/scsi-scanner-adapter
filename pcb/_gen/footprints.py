"""Project footprints, written to pcb/scsi-adapter.pretty/.

Each footprint is built from its datasheet's land pattern, with the numbers written out here so they
can be checked against the drawing. Run: python3 pcb/_gen/footprints.py
"""
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "scsi-adapter.pretty")


def uid(name, *k):
    """Stable UUIDs, so regenerating a footprint doesn't churn the file."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "scsi-adapter-fp/" + name + "/" + "/".join(map(str, k))))


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if v else "0"


class Footprint:
    def __init__(self, name, descr, tags, attr="smd"):
        self.name, self.descr, self.tags, self.attr = name, descr, tags, attr
        self.items = []
        self.n = 0

    def _u(self):
        self.n += 1
        return uid(self.name, self.n)

    def prop(self, key, value, x, y, layer, hide=False):
        h = "\n\t\t(hide yes)" if hide else ""
        self.items.append(f'\t(property "{key}" "{value}"\n\t\t(at {f(x)} {f(y)} 0)\n\t\t(unlocked yes)\n'
                          f'\t\t(layer "{layer}"){h}\n\t\t(uuid "{self._u()}")\n'
                          f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)')

    def line(self, layer, x0, y0, x1, y1, w):
        self.items.append(f'\t(fp_line\n\t\t(start {f(x0)} {f(y0)})\n\t\t(end {f(x1)} {f(y1)})\n'
                          f'\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type default)\n\t\t)\n'
                          f'\t\t(layer "{layer}")\n\t\t(uuid "{self._u()}")\n\t)')

    def rect(self, layer, x0, y0, x1, y1, w):
        self.items.append(f'\t(fp_rect\n\t\t(start {f(x0)} {f(y0)})\n\t\t(end {f(x1)} {f(y1)})\n'
                          f'\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type default)\n\t\t)\n\t\t(fill no)\n'
                          f'\t\t(layer "{layer}")\n\t\t(uuid "{self._u()}")\n\t)')

    def poly(self, layer, pts, w, fill=True):
        p = " ".join(f"(xy {f(x)} {f(y)})" for x, y in pts)
        self.items.append(f'\t(fp_poly\n\t\t(pts {p})\n\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type solid)\n\t\t)\n'
                          f'\t\t(fill {"yes" if fill else "no"})\n\t\t(layer "{layer}")\n\t\t(uuid "{self._u()}")\n\t)')

    def text(self, layer, s, x, y, size=0.5):
        self.items.append(f'\t(fp_text user "{s}"\n\t\t(at {f(x)} {f(y)} 0)\n\t\t(unlocked yes)\n'
                          f'\t\t(layer "{layer}")\n\t\t(uuid "{self._u()}")\n\t\t(effects\n\t\t\t(font\n'
                          f'\t\t\t\t(size {size} {size})\n\t\t\t\t(thickness {size * 0.15:.3f})\n\t\t\t)\n\t\t)\n\t)')

    def smd(self, num, cx, cy, w, h, radius=0.0, layers=("F.Cu", "F.Mask", "F.Paste")):
        """Rectangular SMD pad, centre (cx, cy), size w x h, corner radius in mm."""
        ly = " ".join(f'"{l}"' for l in layers)
        shape = "roundrect" if radius else "rect"
        rr = f"\n\t\t(roundrect_rratio {radius / min(w, h):.4f})" if radius else ""
        self.items.append(f'\t(pad "{num}" smd {shape}\n\t\t(at {f(cx)} {f(cy)})\n\t\t(size {f(w)} {f(h)})\n'
                          f'\t\t(layers {ly}){rr}\n\t\t(uuid "{self._u()}")\n\t)')

    def tht(self, num, cx, cy, size, drill, shape="circle"):
        """Round through-hole pad; pin 1 gets shape='roundrect' (KiCad's pin-1 convention)."""
        rr = "\n\t\t(roundrect_rratio 0.25)" if shape == "roundrect" else ""
        self.items.append(f'\t(pad "{num}" thru_hole {shape}\n\t\t(at {f(cx)} {f(cy)})\n\t\t(size {f(size)} {f(size)})\n'
                          f'\t\t(drill {f(drill)})\n\t\t(layers "*.Cu" "*.Mask"){rr}\n\t\t(uuid "{self._u()}")\n\t)')

    def circle(self, layer, cx, cy, r, w):
        self.items.append(f'\t(fp_circle\n\t\t(center {f(cx)} {f(cy)})\n\t\t(end {f(cx + r)} {f(cy)})\n'
                          f'\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type default)\n\t\t)\n\t\t(fill no)\n'
                          f'\t\t(layer "{layer}")\n\t\t(uuid "{self._u()}")\n\t)')

    def npth_or_mp(self, cx, cy, size, drill, num=""):
        """Plated mounting hole (board lock / bracket); num="SH" ties it to a shield pin."""
        self.items.append(f'\t(pad "{num}" thru_hole circle\n\t\t(at {f(cx)} {f(cy)})\n\t\t(size {f(size)} {f(size)})\n'
                          f'\t\t(drill {f(drill)})\n\t\t(layers "*.Cu" "*.Mask")\n\t\t(uuid "{self._u()}")\n\t)')

    def npth(self, cx, cy, drill):
        """Non-plated hole (locating peg)."""
        self.items.append(f'\t(pad "" np_thru_hole circle\n\t\t(at {f(cx)} {f(cy)})\n\t\t(size {f(drill)} {f(drill)})\n'
                          f'\t\t(drill {f(drill)})\n\t\t(layers "*.Cu" "*.Mask")\n\t\t(uuid "{self._u()}")\n\t)')

    def custom(self, num, ax, ay, pts, layers=("F.Cu", "F.Mask")):
        """Custom-shape pad: a small rect anchor at (ax, ay) plus a filled polygon (absolute coords)."""
        ly = " ".join(f'"{l}"' for l in layers)
        p = " ".join(f"(xy {f(x - ax)} {f(y - ay)})" for x, y in pts)
        self.items.append(f'\t(pad "{num}" smd custom\n\t\t(at {f(ax)} {f(ay)})\n\t\t(size 0.2 0.2)\n'
                          f'\t\t(layers {ly})\n\t\t(options\n\t\t\t(clearance outline)\n\t\t\t(anchor rect)\n\t\t)\n'
                          f'\t\t(primitives\n\t\t\t(gr_poly\n\t\t\t\t(pts {p})\n\t\t\t\t(width 0)\n'
                          f'\t\t\t\t(fill yes)\n\t\t\t)\n\t\t)\n\t\t(uuid "{self._u()}")\n\t)')

    def model(self, path, offset=(0, 0, 0), rotate=(0, 0, 0)):
        o = " ".join(f(v) for v in offset)
        r = " ".join(f(v) for v in rotate)
        self.items.append(f'\t(model "{path}"\n\t\t(offset\n\t\t\t(xyz {o})\n\t\t)\n\t\t(scale\n'
                          f'\t\t\t(xyz 1 1 1)\n\t\t)\n\t\t(rotate\n\t\t\t(xyz {r})\n\t\t)\n\t)')

    def write(self):
        os.makedirs(LIB, exist_ok=True)
        head = (f'(footprint "{self.name}"\n\t(version 20241229)\n\t(generator "scsi_adapter_gen")\n'
                f'\t(generator_version "9.0")\n\t(layer "F.Cu")\n\t(descr "{self.descr}")\n\t(tags "{self.tags}")\n')
        body = "\n".join(self.items)
        path = os.path.join(LIB, self.name + ".kicad_mod")
        with open(path, "w") as fh:
            fh.write(head + body + f"\n\t(attr {self.attr})\n\t(embedded_fonts no)\n)\n")
        return path


def l_pad(sx, sy):
    """RPW0010A corner pad (1, 4, 7, 10) as an L, mirrored into the quadrant (sx, sy).
    Horizontal part x 0.60..1.20, y 0.55..0.85; tab x 0.60..0.85, y 0.85..1.20 (datasheet p.73)."""
    q = [(0.60, 0.55), (1.20, 0.55), (1.20, 0.85), (0.85, 0.85), (0.85, 1.20), (0.60, 1.20)]
    return [(sx * x, sy * y) for x, y in q]


def l_paste(sx, sy):
    """Stencil aperture for a corner pad (93 %): the same L with the tab trimmed to 0.225 wide (p.74)."""
    q = [(0.60, 0.55), (1.20, 0.55), (1.20, 0.85), (0.825, 0.85), (0.825, 1.20), (0.60, 1.20)]
    return [(sx * x, sy * y) for x, y in q]


def rpw0010a():
    """TI RPW0010A VQFN-HR-10, 2 x 2 mm (TPS25947, U101/U201).
    Source: TPS25947 datasheet SLVSFC9C, package pages 72-74 (4225183/A 08/2019). Pad edges were read
    from the drawing's vector outlines and match its dimensions (8X 0.6 long pads centred on 1.8,
    0.25 middle pads at +-0.225, 0.3 corner pads at 0.475 pitch, 2X 0.3 x 2.4 bars at +-0.25).
    Pads are NSMD, as TI recommends. Paste follows TI's 0.1 mm stencil: bars 5/6 split in two (82 %),
    corner pads 93 %, the rest 100 %."""
    fp = Footprint("Texas_RPW0010A_VQFN-HR-10_2x2mm_P0.45mm",
                   "TI RPW0010A VQFN-HR (HotRod) 10 pin, 2x2 mm, land pattern and stencil per TI 4225183/A "
                   "(TPS25947 datasheet SLVSFC9C p.72-74)",
                   "VQFN-HR HotRod RPW0010A TPS25947")
    fp.prop("Reference", "REF**", 0, -2.3, "F.SilkS")
    fp.prop("Value", fp.name, 0, 2.3, "F.Fab")
    fp.prop("Datasheet", "https://www.ti.com/lit/ds/symlink/tps25947.pdf", 0, 0, "F.Fab", hide=True)
    fp.prop("Description", "", 0, 0, "F.Fab", hide=True)
    # Pin 1 top-left, 1-4 down the left, 5/6 the bars (left, right), 7-10 up the right.
    # Side pads 2, 3, 8, 9: 0.6 x 0.25 centred on x = +-0.9, y = -+0.225; R0.05 corners.
    for num, sx, sy in (("2", -1, -1), ("3", -1, 1), ("8", 1, 1), ("9", 1, -1)):
        fp.smd(num, sx * 0.9, sy * 0.225, 0.6, 0.25, 0.05)
    # Corner L pads: copper and mask here, paste as separate apertures below.
    for num, sx, sy in (("1", -1, -1), ("4", -1, 1), ("7", 1, 1), ("10", 1, -1)):
        fp.custom(num, sx * 0.9, sy * 0.7, l_pad(sx, sy))
    # Bars 5 (IN side) and 6: 0.3 x 2.4 at x = -+0.25.
    for num, sx in (("5", -1), ("6", 1)):
        fp.smd(num, sx * 0.25, 0, 0.3, 2.4, 0.05, layers=("F.Cu", "F.Mask"))
    # Paste apertures (unnumbered, F.Paste only).
    for sx, sy in ((-1, -1), (-1, 1), (1, 1), (1, -1)):
        fp.custom("", sx * 0.9, sy * 0.7, l_paste(sx, sy), layers=("F.Paste",))
    for sx in (-1, 1):
        for sy in (-1, 1):   # each bar: two 0.28 x 1.06 apertures, y 0.10..1.16
            fp.smd("", sx * 0.25, sy * 0.63, 0.28, 1.06, 0.05, layers=("F.Paste",))
    # Fab: 2 x 2 body with a pin-1 chamfer.
    fp.poly("F.Fab", [(-0.5, -1), (1, -1), (1, 1), (-1, 1), (-1, -0.5)], 0.1, fill=False)
    fp.text("F.Fab", "${REFERENCE}", 0, 0, 0.5)
    # Silk: the pads reach +-1.2 on every side, so only a pin-1 arrow, 0.16 mm clear of pad 1 (JLC: 0.15).
    fp.poly("F.SilkS", [(-1.42, -0.70), (-1.72, -0.52), (-1.72, -0.88)], 0.12)
    # Courtyard: pads + 0.25.
    fp.rect("F.CrtYd", -1.45, -1.45, 1.45, 1.45, 0.05)
    # No RPW model in KiCad 9; RPU0010A has the same 2 x 2 x 1 body (pads drawn differently).
    fp.model("${KICAD9_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/Texas_RPU0010A_VQFN-HR-10_2x2mm_P0.5mm.step")
    return fp.write()


def wj500v_2p():
    """Kangnex WJ500V-5.08-2P screw terminal (J101, LCSC C8465).
    Source: Kangnex drawing WJ500V-5.08-XXP-1Y-00A rev A (2024-03-10). Pitch 5.08; PCB hole 1.50; pins
    0.9 x 0.8 (1.2 across the diagonal, so KiCad's 1.3 mm Phoenix MKDS drill is too tight). Body: 10.00 deep,
    the pin row 4.50 from the back and 5.50 from the wire-entry face (third-angle side view); N x 5.08 wide,
    2.54 left of pin 1 and 3.14 right of the last pin, which includes a 0.6 interlocking tab. 14.07 tall.
    Wire entry faces +y, as in KiCad's terminal blocks."""
    fp = Footprint("TerminalBlock_Kangnex_WJ500V-5.08-2P_1x02_P5.08mm_Horizontal",
                   "Kangnex WJ500V-5.08-2P screw terminal, 2 pins, pitch 5.08mm, drill 1.5mm "
                   "(Kangnex drawing WJ500V-5.08-XXP-1Y-00A rev A)",
                   "screw terminal block Kangnex WJ500V 5.08mm")
    fp.attr = "through_hole"
    x0, x1, xt, yb, yf = -2.54, 7.62, 8.22, -4.5, 5.5     # body left/right, tab end, back, wire-entry face
    fp.prop("Reference", "REF**", 2.54, yb - 1.6, "F.SilkS")
    fp.prop("Value", fp.name, 2.54, yf + 1.8, "F.Fab")
    fp.prop("Datasheet", "https://www.lcsc.com/datasheet/C8465.pdf", 0, 0, "F.Fab", hide=True)
    fp.prop("Description", "", 0, 0, "F.Fab", hide=True)
    # Pads: 1.5 drill, 3.0 pad (0.75 annular ring: the screw torque loads these joints).
    fp.tht("1", 0, 0, 3.0, 1.5, "roundrect")
    fp.tht("2", 5.08, 0, 3.0, 1.5)
    # Fab: body, interlock tab, screw heads, wire-entry line.
    fp.poly("F.Fab", [(x0, yb), (x1, yb), (x1, yf), (x0 + 0.5, yf), (x0, yf - 0.5)], 0.1, fill=False)
    fp.rect("F.Fab", x1, yb + 1.0, xt, yb + 3.0, 0.1)
    for cx in (0, 5.08):
        fp.circle("F.Fab", cx, 0, 1.5, 0.1)
    fp.line("F.Fab", x0, yf - 1.5, x1, yf - 1.5, 0.1)
    fp.text("F.Fab", "${REFERENCE}", 2.54, -2.8, 1.0)
    # Silk: body outline 0.11 outside, wire-entry line, pin-1 arrow on the wire-entry face.
    o = 0.11
    fp.poly("F.SilkS", [(x0 - o, yb - o), (xt + o, yb - o), (xt + o, yf + o), (x0 - o, yf + o)], 0.12, fill=False)
    fp.line("F.SilkS", x0 - o, yf - 1.5, x1 + o, yf - 1.5, 0.12)
    fp.poly("F.SilkS", [(0, yf + o + 0.05), (0.45, yf + o + 0.65), (-0.45, yf + o + 0.65)], 0.12)
    # Courtyard: body + 0.5 (connector convention).
    fp.rect("F.CrtYd", x0 - 0.5, yb - 0.5, xt + 0.5, yf + 1.0, 0.05)
    # Nearest stock model: Phoenix MKDS 1,5/2-5,08 (body within about 1 mm). Re-check when the enclosure is drawn.
    fp.model("${KICAD9_3DMODEL_DIR}/TerminalBlock_Phoenix.3dshapes/"
             "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.step")
    return fp.write()


def te_amplimite_050_50pos_ra():
    """TE AMPLIMITE .050 Series III right-angle receptacle, 50 positions (J302 HD50): 5787082-5 (latch
    blocks + board locks). Same body and PCB pattern as 5787394-5 (no board locks) and 1761028-3 (rails),
    per catalog 82068 p.7 (E/F/G/K identical).
    Sources:
    - Application spec 114-40029 rev J, Fig. 12 (right-angle, 26/50 pos): contact holes 0.74-0.99 plated,
      4 rows 1.90 apart, 1.27 between positions, board-lock holes 2.77 +-0.05 at E = 46.48 on the row-B
      line, first position 8.00 from the left board lock, PCB edge 5.61 max in front of the board-lock line.
    - TE customer view model C-5787082-5 rev A (STEP): tail rows at 1.905 pitch, 13/12/13/12 tails at
      2.54 pitch with alternate rows offset 1.27, tails 0.305 x 0.406; board locks in line with row B; the
      shell's front flange hangs 0.81 below the board top, back to 5.89 in front of row B, so the edge
      must sit between 5.61 and 5.89 in front of row B; we use 5.61.
    Numbering (114-40029, from the component side, mating face up): position 1 is the rear row's first
    tail; 1-25 alternate rear row D (odd) / row C (even), 26-50 alternate row B (26, 28, ...) / front row A.
    Origin at pin 1; the mating face points to -y."""
    fp = Footprint("TE_AMPLIMITE-050_5787082-5_50pos_P1.27mm_Horizontal",
                   "TE AMPLIMITE .050 Series III right-angle receptacle, 50 pos (SCSI-2 HD50), 5787082-5 / 5787394-5 / "
                   "1761028-3; TE 114-40029 rev J Fig. 12 and customer view model C-5787082-5 rev A",
                   "TE AMPLIMITE 050 HD50 SCSI half-pitch receptacle right angle 5787082")
    fp.attr = "through_hole"
    P, R = 1.27, 1.905
    yD, yC, yB, yA = 0.0, -R, -2 * R, -3 * R
    for n in range(1, 51):
        if n <= 25:
            k = n - 1
            y = yD if k % 2 == 0 else yC
        else:
            k = n - 26
            y = yB if k % 2 == 0 else yA
        # 0.85 finished hole: middle of TE's 0.74-0.99 range, easy to seat 50 tails by hand.
        fp.tht(str(n), k * P, y, 1.3, 0.85, "roundrect" if n == 1 else "circle")
    cx = 12 * P                                       # connector centre line, x = 15.24
    for sx in (-1, 1):                                # board locks = shell, 2.77 plated, on the row-B line
        fp.npth_or_mp(cx + sx * 23.24, yB, 3.8, 2.77, "SH")
    edge = yB - 5.61                                  # PCB edge (max distance from TE)
    front = yB - (0.1016 + 11.684)                    # shell front face (model z = +0.10)
    rear = yB + (16.764 - 11.684)                     # bracket rear (model z = -16.76)
    half = 26.226                                     # G / 2
    fp.prop("Reference", "REF**", cx, rear + 1.6, "F.SilkS")
    fp.prop("Value", fp.name, cx, front - 1.4, "F.Fab")
    fp.prop("Datasheet", "https://www.te.com/usa-en/product-5787082-5.html", 0, 0, "F.Fab", hide=True)
    fp.prop("Description", "", 0, 0, "F.Fab", hide=True)
    # Fab: whole body (it overhangs the board edge), edge line, pin 1 marker.
    fp.rect("F.Fab", cx - half, front, cx + half, rear, 0.1)
    fp.line("F.Fab", cx - half, edge, cx + half, edge, 0.1)
    fp.text("F.Fab", "PCB edge", cx, edge + 0.9, 0.8)
    fp.text("F.Fab", "${REFERENCE}", cx, rear - 2.8, 1.0)
    fp.line("Dwgs.User", cx - half - 2, edge, cx + half + 2, edge, 0.1)
    fp.text("Dwgs.User", "Board edge here (TE: <= 5.61 from board-lock line)", cx, edge - 0.8, 0.6)
    # Silk: the on-board part of the body, open at the board edge; pin-1 arrow behind pad 1.
    o = 0.11
    fp.line("F.SilkS", cx - half - o, edge, cx - half - o, rear + o, 0.12)
    fp.line("F.SilkS", cx - half - o, rear + o, cx + half + o, rear + o, 0.12)
    fp.line("F.SilkS", cx + half + o, rear + o, cx + half + o, edge, 0.12)
    fp.poly("F.SilkS", [(0, rear + o + 0.2), (-0.45, rear + o + 0.8), (0.45, rear + o + 0.8)], 0.12)
    # Courtyard: whole body + 0.5, including the overhang past the board edge.
    fp.rect("F.CrtYd", cx - half - 0.5, front - 0.5, cx + half + 0.5, rear + 1.0, 0.05)
    # TE's STEP: +y up, +z toward the mating face, origin on the centre line at the front, seating plane
    # (bracket feet) at y = -4.343. Rotated so +z points along KiCad's 3D +y (the -y side of the footprint).
    fp.model("${KIPRJMOD}/scsi-adapter.3dshapes/TE_5787082-5.step",
             offset=(cx, -(yB - 11.684), 4.343), rotate=(-90, 0, 180))
    return fp.write()


def tf_push_shouhan():
    """SHOU HAN "TF PUSH" push-push microSD socket with card detect (J501, LCSC C393941).
    Source: SHOU HAN drawing TF PUSH rev A (2020-07-07), "Recommended P.C.B hole layout, component side
    view", tolerance +-0.05. Origin: the "connector center" line (x) and the peg-hole line (y).
    - Contacts Cd, 8 ... 1 (left to right): 0.70 x 1.60 at 1.10 pitch; Cd is 0.60 right of the left shell
      pads' inner edge, which is 2.20 left of the left peg; pad span y -11.80 .. -10.20 (10.20 from the pegs).
    - Pegs: 2 x NPTH 1.00 (pegs 0.80), 8.00 apart, the left one 4.95 left of the connector centre.
    - Shell pads: rear pair 1.50 tall, y -10.75 .. -9.25 (left 1.20 wide, right 1.60 wide, 3.00 right of the
      right peg); front pair 1.20 x 2.20, y -1.50 .. +0.70; left pads x -8.35 .. -7.15, front-right 12.10 right
      of the left peg. Checks: 9.95 (rear shell bottom to front shell bottom), 9.25, 10.20 all agree.
    - Body (top view): 14.75 x 14.50, centred on the connector centre, rear face 10.50 behind the pegs; the
      card slot is the +y face. Height 1.80-2.00.
    Pins: 1 DAT2, 2 CD/DAT3, 3 CMD, 4 VDD, 5 CLK, 6 VSS, 7 DAT0, 8 DAT1 (drawing table); Cd = 9 (DET) and
    the shell = 10 (SHIELD), as in KiCad's Micro_SD_Card_Det1. The Cd contact switches against the shell
    (the only other metal); polarity (closed with or without a card) isn't on the drawing."""
    fp = Footprint("microSD_SHOUHAN_TF-PUSH_PushPush_CardDetect",
                   "SHOU HAN TF PUSH push-push microSD socket with card detect (LCSC C393941); "
                   "SHOU HAN drawing TF PUSH rev A recommended PCB layout",
                   "micro SD TF card socket push-push card detect SHOUHAN C393941")
    xl_peg, xr_peg = -4.95, 3.05
    names = ["9", "8", "7", "6", "5", "4", "3", "2", "1"]        # Cd, 8 ... 1, left to right
    x_cd = xl_peg - 2.20 + 0.60
    for i, num in enumerate(names):
        fp.smd(num, x_cd + i * 1.10, -11.00, 0.70, 1.60)
    fp.smd("10", -7.75, -10.00, 1.20, 1.50)                     # rear-left shell
    fp.smd("10", xr_peg + 3.00 + 0.80, -10.00, 1.60, 1.50)      # rear-right shell (x 6.05 .. 7.65)
    fp.smd("10", -7.75, -0.40, 1.20, 2.20)                      # front-left shell
    fp.smd("10", xl_peg + 12.10 + 0.60, -0.40, 1.20, 2.20)      # front-right shell (x 7.15 .. 8.35)
    for x in (xl_peg, xr_peg):
        fp.npth(x, 0, 1.00)
    bx, by0, by1 = 7.375, -10.50, 4.00
    fp.prop("Reference", "REF**", 0, -13.2, "F.SilkS")
    fp.prop("Value", fp.name, 0, 7.4, "F.Fab")
    fp.prop("Datasheet", "https://www.lcsc.com/datasheet/C393941.pdf", 0, 0, "F.Fab", hide=True)
    fp.prop("Description", "", 0, 0, "F.Fab", hide=True)
    fp.rect("F.Fab", -bx, by0, bx, by1, 0.1)
    fp.text("F.Fab", "card slot", 0, by1 - 0.8, 0.8)
    fp.text("F.Fab", "${REFERENCE}", 0, -5, 1.0)
    # Silk: body sides between the shell pads (0.2 clear of copper), and the slot edge; pin-1 dot.
    o = 0.11
    fp.line("F.SilkS", -bx - o, -9.25 + 0.3, -bx - o, -1.50 - 0.3, 0.12)
    fp.line("F.SilkS", bx + o, -9.25 + 0.3, bx + o, -1.50 - 0.3, 0.12)
    fp.line("F.SilkS", -bx - o, 0.70 + 0.3, -bx - o, by1 + o, 0.12)
    fp.line("F.SilkS", bx + o, 0.70 + 0.3, bx + o, by1 + o, 0.12)
    fp.line("F.SilkS", -bx - o, by1 + o, bx + o, by1 + o, 0.12)
    fp.circle("F.SilkS", x_cd + 8 * 1.10 + 0.9, -12.3, 0.15, 0.3)   # next to pad 1
    fp.rect("F.CrtYd", -8.6, -12.05, 8.6, by1 + 0.5, 0.05)
    fp.line("Dwgs.User", -bx, by1, bx, by1, 0.1)
    fp.text("Dwgs.User", "Slot: put at the board edge; the card sticks out past it", 0, by1 + 1.2, 0.6)
    return fp.write()


def aota_b201610():
    """Abracon AOTA-B201610S3R3-101-T, 3.3 uH 2016 molded power inductor with a polarity dot (L401).
    Source: Abracon datasheet rev A (2024-09-13) p.4: body 2.00 x 1.60 x 1.00, recommended land pattern
    2 x 1.00 x 1.60 pads with a 1.00 gap (centres +-1.00).
    Orientation: RP2350 datasheet 6.3.8.2 says to mark polarity and place it as in Figure 23; there the
    dot is on the pad that goes to COUT/VOUT, and the other pad goes to VREG_LX. The Hardware design
    guide's KiCad layout (Fig. 4) has pad 1 = +1V1 with the dot, pad 2 = VREG_LX. We follow that:
    **pad 1 = the dot end = DVDD_1V1**. The silk dot marks pad 1 so JLC's placement check can match it
    to the part's white dot."""
    fp = Footprint("L_Abracon_AOTA-B201610_2.0x1.6mm_Polarized",
                   "Abracon AOTA-B201610S3R3-101-T polarity-marked 2016 power inductor; pad 1 = dot end "
                   "(RP2350: pad 1 to DVDD, pad 2 to VREG_LX, datasheet Fig. 23); Abracon land pattern",
                   "inductor 2016 0806 Abracon AOTA polarity RP2350")
    fp.smd("1", -1.0, 0, 1.0, 1.6)
    fp.smd("2", 1.0, 0, 1.0, 1.6)
    fp.prop("Reference", "REF**", 0.6, -2.3, "F.SilkS")
    fp.prop("Value", fp.name, 0, 1.9, "F.Fab")
    fp.prop("Datasheet", "https://abracon.com/Magnetics/power/AOTA-B201610S3R3-101-T.pdf", 0, 0, "F.Fab", hide=True)
    fp.prop("Description", "", 0, 0, "F.Fab", hide=True)
    fp.rect("F.Fab", -1.0, -0.8, 1.0, 0.8, 0.1)
    fp.circle("F.Fab", -0.55, -0.35, 0.2, 0.1)                 # the part's white dot, at the pad-1 end
    fp.text("F.Fab", "${REFERENCE}", 0.3, 0, 0.4)
    fp.line("F.SilkS", -0.35, -0.91, 0.35, -0.91, 0.12)
    fp.line("F.SilkS", -0.35, 0.91, 0.35, 0.91, 0.12)
    fp.circle("F.SilkS", -1.0, -1.25, 0.1, 0.2)                # polarity dot beside pad 1
    fp.rect("F.CrtYd", -1.75, -1.55, 1.75, 1.05, 0.05)
    fp.model("${KICAD9_3DMODEL_DIR}/Inductor_SMD.3dshapes/L_Murata_DFE201610P.step")
    return fp.write()


def dip_shouhan_2p():
    """SHOU HAN 2.54-2P TPGT, 2-position SMD slide DIP switch (SW301, LCSC C6331180).
    Source: SHOU HAN drawing DSP-DSICXXLS-AP (DSIC series). PCB layout: pads 1.1 x 2.2 at 2.54 pitch,
    rows 6.6 apart inner edge to inner edge and 11 outer (centres 8.8 apart). Body A x 6.15 with A = 5.08
    for 2 poles; 3.4 tall to the actuator; lead span 9.4.
    Numbering as KiCad's SW_DIP_x02: switch 1 = pads 1-4, switch 2 = pads 2-3; pads 1, 2 on the numbered
    edge (+y), 4, 3 on the "ON" edge (-y). Sliding an actuator toward "ON" (-y) closes that switch."""
    fp = Footprint("SW_DIP_SPSTx02_Slide_SHOUHAN_2.54-2P-TPGT_W8.8mm_P2.54mm",
                   "SHOU HAN 2.54-2P TPGT 2-position SMD slide DIP switch (LCSC C6331180), "
                   "drawing DSP-DSICXXLS-AP PCB layout",
                   "DIP switch SPST slide SMD 2 position SHOUHAN C6331180")
    for num, x, y in (("1", -1.27, 4.4), ("2", 1.27, 4.4), ("3", 1.27, -4.4), ("4", -1.27, -4.4)):
        fp.smd(num, x, y, 1.1, 2.2)
    bx, by = 2.54, 3.075
    fp.prop("Reference", "REF**", 0, -6.6, "F.SilkS")
    fp.prop("Value", fp.name, 0, 6.8, "F.Fab")
    fp.prop("Datasheet", "https://www.lcsc.com/datasheet/C6331180.pdf", 0, 0, "F.Fab", hide=True)
    fp.prop("Description", "", 0, 0, "F.Fab", hide=True)
    fp.rect("F.Fab", -bx, -by, bx, by, 0.1)
    for x in (-1.27, 1.27):                                       # actuator slots
        fp.rect("F.Fab", x - 0.4, -1.5, x + 0.4, 1.5, 0.1)
    fp.text("F.Fab", "ON", 0, -2.3, 0.6)
    # Silk: body sides, "ON" above the body on the left, switch numbers on the body.
    o = 0.11
    for sx in (-1, 1):
        fp.line("F.SilkS", sx * (bx + o), -by - o, sx * (bx + o), by + o, 0.12)
    fp.text("F.SilkS", "ON", -3.9, -4.4, 1.0)
    fp.text("F.SilkS", "1", -1.27, 1.9, 1.0)
    fp.text("F.SilkS", "2", 1.27, 1.9, 1.0)
    fp.rect("F.CrtYd", -4.9, -5.75, 3.05, 5.75, 0.05)
    return fp.write()


if __name__ == "__main__":
    for build in (rpw0010a, wj500v_2p, te_amplimite_050_50pos_ra, tf_push_shouhan, aota_b201610, dip_shouhan_2p):
        print("wrote", os.path.relpath(build(), os.getcwd()))
