"""SCSI front end: pcb/3-scsi.kicad_sch plus the two repeated channel sheets.

Sources: SCSI-2 rev 10L Table 2 (contact assignments) and 5.4.4 (RESERVED lines); NOTES "Connectors",
"ESD protection", "SCSI drivers", "SCSI receivers" (terminator and terminator enable); parts-list.md §2;
Digital Discovery reference manual Figure 8 (DIN connector) for the logic-analyzer header.
"""
import re
from schgen import Sheet, G, stable_uuid

FILES = ["3-scsi.kicad_sch", "scsi_line_bidir.kicad_sch", "scsi_line_in.kicad_sch"]
FILE_UUIDS = {"3-scsi.kicad_sch": "7aec6415-96cb-4b87-8a65-f8b7e4d6c92f",
              "scsi_line_bidir.kicad_sch": "ece56abf-e761-41e9-bc83-c7f38c5773ca",
              "scsi_line_in.kicad_sch": "d8545710-0d72-46b3-8530-fb3e0c7e43a8"}
ROOT = "2c5b21a9-7d0d-4304-8bd9-0602cba3b7b5"
SCSI_SYM = "858bce67-3a23-4d8c-baef-1b62aed1ef48"      # the "scsi" sheet symbol on the root
SCSI_PATH = f"/{ROOT}/{SCSI_SYM}"

# The 18 lines in SCSI-2 connector order (= RP2350 GPIO 0-17). True = has a driver.
LINES = [("DB0", 1), ("DB1", 1), ("DB2", 1), ("DB3", 1), ("DB4", 1), ("DB5", 1), ("DB6", 1), ("DB7", 1),
         ("DBP", 1), ("ATN", 1), ("BSY", 1), ("ACK", 1), ("RST", 1), ("MSG", 0), ("SEL", 1), ("CD", 0),
         ("REQ", 0), ("IO", 0)]
PAGE = {n: 9 + i for i, (n, _) in enumerate(LINES)}           # channel sheets are pages 9-26
BUS = lambda n: "~{" + n + "}"                                 # active-low bus line label

# SCSI-2 Table 2. Set 1 = IDC50 (low-density ribbon), set 2 = HD50. Keyed by set-1 pin; value (set-2 pin, net).
RES = {23: "SCSI_RESERVED_23", 24: "SCSI_RESERVED_24", 27: "SCSI_RESERVED_27", 28: "SCSI_RESERVED_28"}
IDC_EVEN = {2: "DB0", 4: "DB1", 6: "DB2", 8: "DB3", 10: "DB4", 12: "DB5", 14: "DB6", 16: "DB7", 18: "DBP",
            20: "GND", 22: "GND", 24: RES[24], 26: "TERMPWR", 28: RES[28], 30: "GND", 32: "ATN", 34: "GND",
            36: "BSY", 38: "ACK", 40: "RST", 42: "MSG", 44: "SEL", 46: "CD", 48: "REQ", 50: "IO"}
SIGNALS = {n for n, _ in LINES}


def idc_net(pin):
    if pin % 2:
        return {23: RES[23], 25: "NC", 27: RES[27]}.get(pin, "GND")
    n = IDC_EVEN[pin]
    return BUS(n) if n in SIGNALS else n


def hd_net(pin):
    """HD50 (set 2): pin k (1-25) = IDC 2k-1; pin 25+k = IDC 2k."""
    return idc_net(2 * pin - 1) if pin <= 25 else idc_net(2 * (pin - 25))


# Digital Discovery DIN connector (reference manual Figure 8): pin -> DIN channel; GND on 1,2,11,12,21,22,31,32.
DD_PIN_TO_DIN = {3: 19, 5: 18, 7: 17, 9: 16, 13: 11, 15: 10, 17: 9, 19: 8, 23: 3, 25: 2, 27: 1, 29: 0,
                 4: 23, 6: 22, 8: 21, 10: 20, 14: 15, 16: 14, 18: 13, 20: 12, 24: 7, 26: 6, 28: 5, 30: 4}
DIN_NET = {i: n + "_LOGIC_ANALYZER" for i, (n, _) in enumerate(LINES)}   # DIN0-17 = the 18 lines in GPIO order
DIN_NET[18], DIN_NET[19] = "LOGIC_ANALYZER_MARKER0", "LOGIC_ANALYZER_MARKER1"             # DIN20-23 unused


def la_net(pin):
    if pin in (1, 2, 11, 12, 21, 22, 31, 32):
        return "GND"
    return DIN_NET.get(DD_PIN_TO_DIN[pin], "NC")


R0402, C0402 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric"


def props(fp, lcsc, dnp=False, note="", fit="JLC", ds=""):
    return {"Footprint": fp, "Datasheet": ds, "Description": note, "LCSC": lcsc, "Fit": "DNP" if dnp else fit}


def heading(s, t, x, y, body=""):
    s.text(t, x, y, 2.0, bold=True)
    if body:
        s.text(body, x, y + 4.5, 1.27)


def connector(s, lib, ref, value, x, y, netfn, prps, dnp=False, fields=None):
    """Place a connector; ground runs on one side share a short bus with a single GND symbol,
    single GNDs and rails get an inline power symbol, everything else a label or no-connect."""
    emb, pins = s._lib(lib)
    s._symbol(lib, ref, value, x, y, 0, prps, fields or ((x, y - 35.56, "left"), (x, y - 33.02, "left")), dnp=dnp)
    sides = {}
    for num in pins:
        px, py, d = s.pin_pos(pins, num, x, y, 0)
        sides.setdefault(d, []).append((py, px, num, netfn(int(num))))
    for d, rows in sides.items():
        rows.sort()
        sgn = -1 if d == 180 else 1
        i = 0
        while i < len(rows):
            j = i
            while j + 1 < len(rows) and rows[i][3] == "GND" and rows[j + 1][3] == "GND" \
                    and abs(rows[j + 1][0] - rows[j][0] - G) < 0.01:
                j += 1
            py, px, num, net = rows[i]
            if net not in ("NC",):
                s.intended[(ref, num)] = net
            if j > i:                                      # a run of GNDs: stubs onto a short vertical bus
                bx = px + sgn * G
                for k in range(i, j + 1):
                    s.wire(rows[k][1], rows[k][0], bx, rows[k][0])
                    s.intended[(ref, rows[k][2])] = "GND"
                for k in range(i, j):                      # segment by segment: stubs must meet wire ends
                    s.wire(bx, rows[k][0], bx, rows[k + 1][0])
                mid = rows[(i + j) // 2][0]
                for k in range(i + 1, j):
                    s.junction(bx, rows[k][0])
                s.wire(bx, mid, bx + sgn * G, mid)
                s.power("GND", bx + sgn * G, mid, d)
                i = j + 1
                continue
            s.attach(net, px, py, d, inline=True)
            i += 1


def build_channel(path, bidir):
    """One channel sheet file, used by several sheet symbols (one instance per line)."""
    lines = [(n, PAGE[n]) for n, b in LINES if bool(b) == bidir]
    inst = []
    for n, page in lines:
        def refmap(r, page=page):
            m = re.match(r"(#?[A-Z]+)(\d+)$", r)
            return f"{m.group(1)}{page * 100 + int(m.group(2))}"
        inst.append((f"{SCSI_PATH}/{stable_uuid('scsi/' + n)}", refmap))
    fname = "scsi_line_bidir.kicad_sch" if bidir else "scsi_line_in.kicad_sch"
    s = Sheet(FILE_UUIDS[fname], "A4", "SCSI scanner adapter", inst, seed=fname)
    s.refbase = 0
    s.rails = {"+3V3"}
    s.hier = {"LINE": "bidirectional", "GATE": "input", "RX": "output", "LOGIC_ANALYZER": "output"}
    if bidir:
        heading(s, "SCSI line with driver", 20.32, 20.32,
                "x14: DB0-7, DBP, ATN, BSY, ACK, RST, SEL (pages 9-21 except MSG). References: page x 100 + n.\n"
                "Driver: GATE high = line asserted (Q1 pulls it to ~0.2 V). Receiver: RX low = line asserted\n"
                "(the RP2350 pad inverts it). Place this cluster on its own bus trace next to the connector.")
    else:
        heading(s, "SCSI line, receive only", 20.32, 20.32,
                "x4: MSG, C/D, REQ, I/O. The initiator never drives these (SCSI-2 Table 6: target-only).\n"
                "RX low = line asserted (the RP2350 pad inverts it). References: page x 100 + n.")
    BY = 76.2                                              # the LINE bus
    s.net_at("LINE", 43.18, BY, 180)
    xs = [43.18]
    if bidir:
        QX, QY = 101.6, 91.44
        s.part("Transistor_FET:Q_NMOS_GSD", "Q1", "FDV301N", QX, QY, {"1": None, "3": None, "2": "GND"},
               props=props("Package_TO_SOT_SMD:SOT-23", "C15310", note="Open-drain SCSI driver",
                           ds="https://www.onsemi.com/pdf/datasheet/fdv301n-d.pdf"),
               fields=((QX + 5.08, QY - 1.27, "left"), (QX + 5.08, QY + 1.27, "left")))
        s.wire(QX + 2.54, QY - 5.08, QX + 2.54, BY)
        s.junction(QX + 2.54, BY)
        xs.append(QX + 2.54)
        # gate: GATE -> R1 100R -> gate node (R2 4.7k and C1 22 pF DNP to GND) -> Q1 gate
        s.part("Device:R", "R1", "100R", 78.74, QY, {"1": "GATE", "2": None}, a=90,
               props=props(R0402, "C25076", note="Gate series R (edge rate; 0R or larger to tune)"),
               fields=((78.74, QY - 5.08, ""), (78.74, QY - 2.54, "")))
        s.wire(82.55, QY, 86.36, QY)
        s.wire(86.36, QY, 91.44, QY)
        s.wire(91.44, QY, QX - 5.08, QY)
        for jx in (86.36, 91.44):
            s.junction(jx, QY)
            s.wire(jx, QY, jx, QY + 3.81)
        s.part("Device:C", "C1", "22pF C0G", 86.36, QY + 7.62, {"1": None, "2": "GND"},
               props=props(C0402, "C1555", True, "Gate cap, DNP"), dnp=True, fields="left")
        s.part("Device:R", "R2", "4.7k", 91.44, QY + 7.62, {"1": None, "2": "GND"},
               props=props(R0402, "C25900", note="Gate pull-down (<= 8.2k for RP2350-E9)"),
               fields=((93.98, QY + 6.35, "left"), (93.98, QY + 8.89, "left")))
        for k in (("R1", "2"), ("C1", "1"), ("R2", "1"), ("Q1", "1")):
            s.intended[k] = "~gate"
        s.intended[("Q1", "3")] = "LINE"
        s.note("C1 DNP: fit only if a rising bus edge,\ncoupled through the FET's gate-drain\n"
               "capacitance, makes a visible dip or step\n(board off, G4 driving the bus).", 60.96, 111.76)
    # receiver
    UX, UY = 165.1, 93.98
    s.part("74xGxx:74LVC1G17", "U1", "74LVC1G17GW", UX, UY, {"2": None, "4": None, "5": "+3V3", "3": "GND",
                                                              "1": "NC"},
           props=props("Package_TO_SOT_SMD:SOT-353_SC-70-5", "C426705",
                       note="Nexperia only: its thresholds are what SCSI-2 needs", ds=""),
           fields=((UX + 2.54, UY - 11.43, "left"), (UX + 2.54, UY + 11.43, "left")))
    AX = UX - 12.7
    s.wire(AX - 5.08, BY, AX - 5.08, UY)
    s.wire(AX - 5.08, UY, AX, UY)
    xs.append(AX - 5.08)
    for a, b in zip(xs, xs[1:]):
        s.wire(a, BY, b, BY)
    s.intended[("U1", "2")] = "LINE"
    YX = UX + 10.16
    s.wire(YX, UY, YX + 10.16, UY)
    s.wire(YX + 10.16, UY, YX + 20.32, UY)
    s.junction(YX + 10.16, UY)
    s.net_at("RX", YX + 20.32, UY, 0)
    s.wire(YX + 10.16, UY, YX + 10.16, UY + 6.35)
    s.part("Device:R", "R3", "100R", YX + 10.16, UY + 10.16, {"1": None, "2": "LOGIC_ANALYZER"},
           props=props(R0402, "C25076", note="Logic-analyzer tap series R: limits a short at the header to 33 mA"),
           fields=((YX + 12.7, UY + 8.89, "left"), (YX + 12.7, UY + 11.43, "left")))
    s.intended[("U1", "4")] = s.intended[("R3", "1")] = "RX"
    s.part("Device:C", "C2", "100nF 50V", 144.78, 111.76, {"1": "+3V3", "2": "GND"},
           props=props(C0402, "C307331", note="U1 decoupling"), fields="left")
    s.note("R3 feeds the logic-analyzer header; the RP2350 input\ntakes RX straight from U1.", 185.42, 116.84)
    s.write(path)
    return s, lines


def build(paths):
    intended = {}
    # ---------------- channel sheets ----------------
    for bidir, fname in ((True, "scsi_line_bidir.kicad_sch"), (False, "scsi_line_in.kicad_sch")):
        cs, lines = build_channel(paths[fname], bidir)
        for (n, page), (_, refmap) in zip(lines, cs.instances):
            port = {"LINE": BUS(n), "GATE": n + "_GATE", "RX": n + "_RX", "LOGIC_ANALYZER": n + "_LOGIC_ANALYZER"}
            for (ref, pin), net in cs.intended.items():
                net = port.get(net, net if net in ("GND", "+3V3") else f"{n}/{net}")
                intended[(refmap(ref), pin)] = net

    # ---------------- parent sheet ----------------
    s = Sheet(FILE_UUIDS["3-scsi.kicad_sch"], "A2", "SCSI scanner adapter", SCSI_PATH, seed="3-scsi.kicad_sch")
    s.refbase = 300
    s.rails = {"VTERMINATOR", "TERMPWR"}
    s.hier = {n + "_GATE": "input" for n, b in LINES if b}
    s.hier.update({n + "_RX": "output" for n, _ in LINES})
    s.hier.update({"LOGIC_ANALYZER_MARKER0": "input", "LOGIC_ANALYZER_MARKER1": "input",
                   "TERMINATOR_EN_INVERTED_FIRMWARE": "bidirectional"})

    # ================= Connectors =================
    s.rect(12.7, 12.7, 254.0, 167.64)
    heading(s, "Connectors", 20.32, 20.32,
            "SCSI: the same bus on both, wired by signal name from SCSI-2 Table 2 (IDC50 = contact set 1, HD50 = set 2).")
    s.text("J301 SCSI IDC50 (fitted)", 30.48, 36.83, 1.27)
    connector(s, "Connector_Generic:Conn_02x25_Odd_Even", "J301", "IDC50 box header", 45.72, 76.2, idc_net,
              props("Connector_IDC:IDC-Header_2x25_P2.54mm_Vertical", "C30006", fit="Hand",
                    note="BOOMELE 2x25 keyed box header"),
              fields=((40.64, 43.18, "left"), (40.64, 110.49, "left")))
    s.text("J302 SCSI HD50 (DNP)", 104.14, 36.83, 1.27)
    connector(s, "Connector_Generic:Conn_02x25_Top_Bottom", "J302", "HD50 female R/A", 116.84, 76.2, hd_net,
              props("", "", True, fit="DNP", note="Half-pitch 50-pin female, right angle. Part and footprint to do."),
              dnp=True, fields=((111.76, 43.18, "left"), (111.76, 110.49, "left")))
    s.note("Pin 25 (HD50 13) is OPEN: a reversed ribbon puts TERMPWR on a\ndead pin, not on ground. "
           "IDC50 even pins 20, 22, 30, 34 are GROUND.", 20.32, 114.3)
    for i, (pin, net) in enumerate(sorted(RES.items())):
        x = 33.02 + i * 30.48
        s.part("Device:R", f"R{337 + i}", "0R", x, 135.89, {"1": net, "2": "GND"},
               props=props(R0402, "C17168", note="RESERVED line to ground (SCSI-2 5.4.4); remove if mid-chain"),
               fields="left")
    s.note("SCSI-2 5.4.4: RESERVED lines 'shall be connected to ground' in end devices, 'should be open'\n"
           "otherwise. We are an end device: all four fitted. Remove R337-R340 if the board ever sits mid-chain.",
           20.32, 151.13)
    s.text("J303 logic-analyzer header (Digital Discovery DIN)", 177.8, 36.83, 1.27)
    connector(s, "Connector_Generic:Conn_02x16_Odd_Even", "J303", "2x16 box header", 200.66, 66.04, la_net,
              props("Connector_IDC:IDC-Header_2x16_P2.54mm_Vertical", "C2685073", fit="Hand",
                    note="Liansheng BH-00169 2x16 keyed box header"),
              fields=((195.58, 43.18, "left"), (195.58, 89.66, "left")))
    s.note("Pin-for-pin copy of the Digital Discovery's 2x16 DIN\nconnector (reference manual Fig. 8): a straight\n"
           "32-way 0.1\" IDC ribbon links pin n to pin n.\nDIN0-17 = the 18 bus lines in GPIO order (DB0..IO),\n"
           "DIN18/19 = the two markers, DIN20-23 unused.\nGND on 1, 2, 11, 12, 21, 22, 31, 32.\n"
           "Each tap has 100R at its receiver (channel sheets).", 177.8, 97.79)

    # ================= Active terminator =================
    s.rect(12.7, 172.72, 254.0, 292.1)
    heading(s, "Active terminator", 20.32, 180.34,
            "VTERMINATOR (2.83 V) -> SN74LVTH245A, A tied high -> TERMINATOR_OUT_<line> -> 2 x 220R per line (next to each line,\n"
            "right) -> bus. /OE high or unpowered: outputs high-Z. 6 lines per package, in connector order.")
    groups = [[n for n, _ in LINES][k * 6:(k + 1) * 6] for k in range(3)]
    TERM = props("Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm", "C2652121", note="Terminator driver",
                 ds="https://www.ti.com/lit/ds/symlink/sn74lvth245a.pdf")
    for k, grp in enumerate(groups):
        IX, IY = 63.5 + k * 76.2, 233.68
        ref = f"U{301 + k}"
        nets = {str(p): None for p in range(2, 10)}          # A1-A8, wired to the rail below
        nets.update({"1": None, "19": "TERMINATOR_EN_INVERTED", "20": "VTERMINATOR", "10": "GND",
                     "12": "NC", "11": "NC"})
        for b, n in enumerate(grp):                          # B1 = pin 18 ... B6 = pin 13
            nets[str(18 - b)] = "TERMINATOR_OUT_" + n
        s.part("scsi-adapter:SN74LVTH245A", ref, "SN74LVTH245APWR", IX, IY, nets, props=TERM,
               fields=((IX + 2.54, IY - 22.86, "left"), (IX + 2.54, IY + 22.86, "left")), stub=G)
        bx = IX - 15.24
        ys = [IY - 12.7 + 2.54 * a for a in range(8)] + [IY + 10.16]
        for yy in ys:
            s.wire(IX - 12.7, yy, bx, yy)
        for ya, yb in zip([ys[0] - 2.54] + ys[:-1], ys):   # segment by segment: stubs must meet wire ends
            s.wire(bx, ya, bx, yb)
        for yy in ys[:-1]:
            s.junction(bx, yy)
        s.power("VTERMINATOR", bx, ys[0] - 2.54, 90)
        for p in list(range(2, 10)) + [1]:
            s.intended[(ref, str(p))] = "VTERMINATOR"
        s.part("Device:C", f"C{301 + k}", "100nF 50V", IX + 25.4, IY + 15.24, {"1": "VTERMINATOR", "2": "GND"},
               props=props(C0402, "C307331", note=f"{ref} decoupling"),
               fields=((IX + 27.94, IY + 13.97, "left"), (IX + 27.94, IY + 16.51, "left")))
    s.note("A1-A8 and DIR tie straight to the rail: DIR high = A->B, and bus-hold inputs mustn't get pull resistors.\n"
           "B7/B8 unused.", 20.32, 281.94)

    # ================= Terminator enable =================
    s.rect(12.7, 297.18, 254.0, 406.4)
    heading(s, "Terminator enable DIP switch", 20.32, 304.8,
            "Switch state survives power-off and needs no firmware; DIP 2 lets firmware (expander P12) override it.")
    SX, SY = 66.04, 345.44
    NX = SX - 12.7                                    # the /OE node column
    s.part("Device:R", "R341", "10k", NX, SY - 12.7, {"1": "VTERMINATOR", "2": None},
           props=props(R0402, "C25744", note="/OE pull-up: off by default"), fields="left")
    s.part("Switch:SW_DIP_x02", "SW301", "DIP 2-pos", SX, SY, {"1": None, "2": None, "4": None, "3": None},
           props=props("", "C6331180", note="SHOU HAN 2-position SMD DIP. Footprint to do."),
           fields=((SX - 5.08, SY - 6.35, "left"), (SX - 5.08, SY + 5.08, "left")))
    s.wire(NX, SY - 8.89, NX, SY - 2.54)
    s.wire(NX, SY - 2.54, SX - 7.62, SY - 2.54)
    s.wire(SX - 7.62, SY, NX, SY)
    s.wire(NX, SY, NX, SY - 2.54)
    s.junction(NX, SY - 2.54)
    s.junction(NX, SY)
    s.wire(NX, SY, NX, SY + 2.54)
    s.net_at("TERMINATOR_EN_INVERTED", NX, SY + 2.54, 180)
    for k in (("R341", "2"), ("SW301", "1"), ("SW301", "2")):
        s.intended[k] = "TERMINATOR_EN_INVERTED"
    s.wire(SX + 7.62, SY - 2.54, SX + 12.7, SY - 2.54)
    s.part("Device:R", "R342", "1k", SX + 12.7, SY + 1.27, {"1": None, "2": "GND"},
           props=props(R0402, "C11702", note="DIP 1 pull-down (lets a push-pull expander pin override it)"),
           fields=((SX + 15.24, SY, "left"), (SX + 15.24, SY + 2.54, "left")))
    s.intended[("SW301", "4")] = s.intended[("R342", "1")] = "~dip1"
    s.wire(SX + 7.62, SY, SX + 7.62, SY + 12.7)
    s.net_at("TERMINATOR_EN_INVERTED_FIRMWARE", SX + 7.62, SY + 12.7, 180)
    s.intended[("SW301", "3")] = "TERMINATOR_EN_INVERTED_FIRMWARE"
    s.note("TERMINATOR_EN_INVERTED drives /OE on U301-U303: low = terminated. R341 pulls it up to\n"
           "2.83 V (off). DIP 1 closes it to GND through R342: ~0.26 V = on. DIP 2 connects it to\n"
           "the expander pin (push-pull, so it can override R342). The expander powers up with its\n"
           "pins as inputs, so the switch default holds; firmware reads the pin to learn it.\n"
           "Mid-chain and possibly unpowered: use off/off.", 20.32, 372.11)
    # truth table (native KiCad table, grey header)
    TT = [["DIP 1", "DIP 2", "Termination"],
          ["off", "off", "off, fixed"],
          ["off", "on", "off by default; firmware may turn it on"],
          ["on", "off", "on, fixed"],
          ["on", "on", "on by default; firmware may turn it off"]]
    s.table(116.84, 322.58, TT, [12.7, 12.7, 55.88], header_fill=(220, 220, 220), center_cols=(0, 1))

    # ================= Per-line driver and receiver =================
    s.rect(259.08, 12.7, 584.2, 327.66)
    heading(s, "Per-line driver and receiver", 266.7, 20.32,
            "Per line: terminator pair (2 x 220R = 110R), ESD diode to GND, then the channel sheet (driver + receiver).\n"
            "Keep each cluster on its own bus trace by the connector. GATE (from the RP2350) and RX (to it) are sheet pins.")
    s.note("R301-R336: 220R 1 % 0402 (C25091), <= 35 mW each at 2.94 V into an asserted line.\n"
           "D301-D318: H5VUD5BB (C20615820), bidirectional, 0.3 pF, 5 V working. ESD protection: they clamp static\n"
           "discharges from the cable or a finger on the connector to GND before they reach the FET or the receiver.\n"
           "0.3 pF keeps each line inside SCSI-2's 25 pF budget; bidirectional, so normal bus swings never make them conduct.",
           266.7, 33.02)
    bidir = [n for n, b in LINES if b]
    recv = [n for n, b in LINES if not b]
    PITCH = 25.4
    slots = [(264.16, 55.88 + i * PITCH, n) for i, n in enumerate(bidir[:9])]
    slots += [(429.26, 55.88 + i * PITCH, n) for i, n in enumerate(bidir[9:])]
    ry0 = 55.88 + 5 * PITCH + 27.94
    slots += [(429.26, ry0 + i * PITCH, n) for i, n in enumerate(recv)]
    s.rect(424.18, ry0 - 22.86, 579.12, ry0 + 3 * PITCH + 27.94)
    heading(s, "Receive-only lines", 429.26, ry0 - 17.78,
            "MSG, C/D, REQ, I/O: only the target drives them (SCSI-2 Table 6), so no driver.")
    idx = {n: i for i, (n, _) in enumerate(LINES)}
    for cx, ry, n in slots:
        i = idx[n]
        b = n in bidir
        sx = cx + 58.42                                  # channel sheet symbol
        ly = ry + G                                      # LINE row
        nx = sx - 12.7                                   # the bus-line node
        px = sx - 24.13                                  # centre of the resistor pair
        ra, rb = f"R{301 + 2 * i}", f"R{302 + 2 * i}"
        for rr, yy, fy in ((ra, ly, ly - 2.54), (rb, ly + 3.81, ly + 6.35)):
            s.part("Device:R", rr, "220R", px, yy, {"1": None, "2": None}, a=90,
                   props=props(R0402, "C25091", note=f"Terminator for {n} (2 x 220R = 110R)"),
                   fields=((px, fy, ""), (px, fy, "")), hide_value=True)
            s.intended[(rr, "1")] = "TERMINATOR_OUT_" + n
            s.intended[(rr, "2")] = BUS(n)
        s.wire(px - 3.81, ly, px - 3.81, ly + 3.81)
        s.wire(px + 3.81, ly, px + 3.81, ly + 3.81)
        s.wire(px - 3.81, ly, px - 6.35, ly)
        s.net_at("TERMINATOR_OUT_" + n, px - 6.35, ly, 180)
        s.wire(px + 3.81, ly, nx, ly)                    # pair -> node -> channel LINE pin
        s.wire(nx, ly, sx, ly)
        s.wire(nx, ly, nx, ly - G)                       # bus label above the node
        s.net_at(BUS(n), nx, ly - G, 0)
        s.wire(nx, ly, nx, ly + G)                       # ESD below the node
        s.junction(nx, ly)
        s.part("Device:D_TVS", f"D{301 + i}", "H5VUD5BB", nx, ly + G + 3.81, {"1": None, "2": "GND"}, a=270,
               props=props("Diode_SMD:D_SOD-523", "C20615820", note=f"ESD for {n}"),
               fields=((nx + 2.54, ly + G + 3.81, "right"), (nx + 2.54, ly + G + 3.81, "right")), hide_value=True)
        s.intended[(f"D{301 + i}", "1")] = BUS(n)
        right = ([("GATE", "input", n + "_GATE")] if b else [None]) + \
            [None, ("RX", "output", n + "_RX"), None, ("LOGIC_ANALYZER", "output", n + "_LOGIC_ANALYZER")]
        s.sheet_symbol(n, "scsi_line_bidir.kicad_sch" if b else "scsi_line_in.kicad_sch", sx, ry, 30.48,
                       [("LINE", "bidirectional", None)], right, PAGE[n], stable_uuid("scsi/" + n))
    s.write(paths["3-scsi.kicad_sch"])
    intended.update(s.intended)
    return intended
