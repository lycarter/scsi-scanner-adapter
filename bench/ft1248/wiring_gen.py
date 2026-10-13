P = 22
COLS = {c: 120 + i * P for i, c in enumerate("abcde")}
COLS.update({c: 274 + i * P for i, c in enumerate("fghij")})
RAIL_L, RAIL_R = (28, 50), (466, 488)
Y0, ROWS = 70, 36
W, H = 516, Y0 + (ROWS - 1) * P + 36
y = lambda r: Y0 + (r - 1) * P

s = []
a = s.append
a(f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="dt dd">')
a('<title id="dt">Breadboard wiring, Pico 2 W above an FT232H breakout</title>')
a('<desc id="dd">Seven signal lines, each through a 33 ohm resistor, and one ground link. C0 to GP15, C1 to GP14, C2 to GP13, D0 to GP16, D1 to GP17, D2 to GP18, D3 to GP19, and both grounds to the right-hand ground rail. A dashed line shows the second step, which moves the D0 line from GP16 to GP26.</desc>')
a(f'<rect class="bb" x="6" y="30" width="{W-12}" height="{H-36}" rx="10"/>')
a(f'<rect class="chan" x="{COLS["e"]+14}" y="{Y0-14}" width="{COLS["f"]-COLS["e"]-28}" height="{(ROWS-1)*P+28}" rx="4"/>')
# rails
for x, cls in ((RAIL_L[0], "plus"), (RAIL_L[1], "minus"), (RAIL_R[0], "minus"), (RAIL_R[1], "plus")):
    a(f'<line class="rail {cls}" x1="{x}" y1="{Y0-10}" x2="{x}" y2="{y(ROWS)+10}"/>')
    a(f'<text class="railt {cls}" x="{x}" y="{Y0-18}" text-anchor="middle">{"+" if cls=="plus" else "−"}</text>')
    for r in range(1, ROWS + 1):
        if r % 6:
            a(f'<circle class="hole" cx="{x}" cy="{y(r)}" r="2.6"/>')
for c, x in COLS.items():
    a(f'<text class="colt" x="{x}" y="{Y0-18}" text-anchor="middle">{c}</text>')
    for r in range(1, ROWS + 1):
        a(f'<circle class="hole" cx="{x}" cy="{y(r)}" r="2.6"/>')

XL, XR = COLS["c"], COLS["h"]
BX, BW = XL - 14, XR - XL + 28

def board(cls, r0, left, right, hot, name, sub, usb_top):
    n = len(left)
    top, bot = y(r0) - 14, y(r0 + n - 1) + 14
    ux, uw = (XL + XR) / 2 - 24, 48
    if usb_top:
        a(f'<rect class="usb" x="{ux}" y="{top-12}" width="{uw}" height="30" rx="4"/>')
    else:
        a(f'<rect class="usb" x="{ux}" y="{bot-18}" width="{uw}" height="30" rx="4"/>')
    a(f'<rect class="{cls}" x="{BX}" y="{top}" width="{BW}" height="{bot-top}" rx="7"/>')
    for i in range(n):
        yy = y(r0 + i)
        for x, lab, anchor, tx in ((XL, left[i], "start", XL + 10), (XR, right[i], "end", XR - 10)):
            h = lab in hot
            a(f'<rect class="pad{" on" if h else ""}" x="{x-4.5}" y="{yy-4.5}" width="9" height="9" rx="1.5"/>')
            txt = lab + (f' <tspan class="fn">{hot[lab]}</tspan>' if h and hot[lab] and anchor == "start" else "")
            if h and hot[lab] and anchor == "end":
                txt = f'<tspan class="fn">{hot[lab]}</tspan> ' + lab
            a(f'<text class="pin{" on" if h else ""}" x="{tx}" y="{yy+3.6}" text-anchor="{anchor}">{txt}</text>')
    return top, bot

pico_l = "GP0 GP1 GND GP2 GP3 GP4 GP5 GND GP6 GP7 GP8 GP9 GND GP10 GP11 GP12 GP13 GND GP14 GP15".split()
pico_r = "VBUS VSYS GND 3V3_EN 3V3 VREF GP28 AGND GP27 GP26 RUN GP22 GND GP21 GP20 GP19 GP18 GND GP17 GP16".split()
# only the row-18 right GND is used; mark by index after drawing
t, b = board("pico", 1, pico_l, pico_r, {"GP13": "", "GP14": "", "GP15": "", "GP16": "", "GP17": "", "GP18": "", "GP19": "", "GP26": ""}, "", "", True)
a(f'<text class="bname" x="{(XL+XR)/2}" y="{y(8)+4}" text-anchor="middle">Pico 2 W</text>')
a(f'<text class="bsub" x="{(XL+XR)/2}" y="{y(9)+2}" text-anchor="middle">USB end up</text>')
a(f'<rect class="pad on" x="{XR-4.5}" y="{y(18)-4.5}" width="9" height="9" rx="1.5"/>')

FT0 = 24
ft_l = "C0 C1 C2 C3 C4 C5 C6 C7 C8 C9 Gnd".split()
ft_r = "D7 D6 D5 D4 D3 D2 D1 D0 Gnd 5V 3V".split()
board("ft", FT0, ft_l, ft_r, {"C0": "SCLK", "C1": "SS_n", "C2": "MISO", "D0": "MIO0", "D1": "MIO1", "D2": "MIO2", "D3": "MIO3"}, "", "", False)
a(f'<text class="bname" x="{(XL+XR)/2}" y="{y(FT0+4)+4}" text-anchor="middle">FT232H</text>')
a(f'<text class="bsub" x="{(XL+XR)/2}" y="{y(FT0+5)+2}" text-anchor="middle">USB-C end down</text>')
a(f'<rect class="pad on" x="{XR-4.5}" y="{y(FT0+8)-4.5}" width="9" height="9" rx="1.5"/>')

def bow(cls, x, r1, r2, k, resistor=True, dashed=False):
    d = f'M{x},{y(r1)} C{x+k},{y(r1)} {x+k},{y(r2)} {x},{y(r2)}'
    if dashed:
        a(f'<path class="w {cls} dash" d="{d}"/>')
        a(f'<circle class="we {cls}" cx="{x}" cy="{y(r1)}" r="4.2"/>')
        return
    a(f'<path class="wu" d="{d}"/><path class="w {cls}" d="{d}"/>')
    for r in (r1, r2):
        a(f'<circle class="we {cls}" cx="{x}" cy="{y(r)}" r="4.2"/>')
    if resistor:   # body at the apex of the bow, where the path runs vertically
        mx, my = x + 0.75 * k, (y(r1) + y(r2)) / 2
        a(f'<rect class="res" x="{mx-5}" y="{my-11}" width="10" height="22" rx="3"/>')
        for dy in (-6, -2, 2):
            a(f'<line class="band" x1="{mx-5}" y1="{my+dy}" x2="{mx+5}" y2="{my+dy}"/>')

def stub(cls, x1, x2, r):
    a(f'<path class="wu" d="M{x1},{y(r)} H{x2}"/><path class="w {cls}" d="M{x1},{y(r)} H{x2}"/>')
    for x in (x1, x2):
        a(f'<circle class="we {cls}" cx="{x}" cy="{y(r)}" r="4.2"/>')

A, J = COLS["a"], COLS["j"]
bow("miso", A, 17, FT0 + 2, -74)
bow("ss", A, 19, FT0 + 1, -50)
bow("sclk", A, 20, FT0, -28)
stub("gnd", J, RAIL_R[0], 18)
stub("gnd", J, RAIL_R[0], FT0 + 8)
bow("d3", J, 16, FT0 + 4, 84)
bow("d2", J, 17, FT0 + 5, 66)
bow("d1", J, 19, FT0 + 6, 48)
bow("d0", J, 20, FT0 + 7, 30)
bow("d0", J, 10, FT0 + 7, 118, dashed=True)
a(f'<text class="note step" x="{J+62}" y="{y(12)}" text-anchor="middle">step 2</text>')
a(f'<text class="note" x="{RAIL_R[1]+13}" y="{y(28)}" transform="rotate(90 {RAIL_R[1]+13} {y(28)})" text-anchor="middle">ground rail joins the two GND jumpers</text>')
a('</svg>')
svg = "\n".join(s)

html = open("wiring_tpl.html").read().replace("{{SVG}}", svg)
open("wiring.html", "w").write(html)
print(len(html))
