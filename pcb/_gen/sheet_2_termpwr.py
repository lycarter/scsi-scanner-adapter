"""Populate pcb/2-termpwr.kicad_sch. Sources: NOTES "CC detection", "TERMPWR switch and current limit",
"eFuse startup", "Resistor and small-part values"; parts-list.md §1."""
from schgen import Sheet, G

FILE = "2-termpwr.kicad_sch"
FILE_UUID = "f41f4cff-43a5-4b18-a5cb-1a059c9ac4a2"      # the sheet file's own uuid; keep it stable

ROOT = "2c5b21a9-7d0d-4304-8bd9-0602cba3b7b5"
SHEET_SYM = "d6807777-092c-4171-8862-e4c45e752643"      # the "termpwr" sheet symbol on the root
def build(out_path):
    """Write the sheet to out_path; return the intended {(ref, pin): net} map."""
    s = Sheet(FILE_UUID, "A3", "SCSI scanner adapter", f"/{ROOT}/{SHEET_SYM}")
    s.refbase = 200
    s.rails = {"+5V_SYS", "+3V3", "TERMPWR"}
    EN_NODE = "TERMPWR_EN_INVERTED"
    s.hier = {"BENCH_5V": "input", "CC1": "input", "CC2": "input", EN_NODE: "output",
              "TERMPWR_EFUSE_FAULT_INVERTED": "output"}

    R0402 = "Resistor_SMD:R_0402_1005Metric"
    C0402 = "Capacitor_SMD:C_0402_1005Metric"


    def props(fp, lcsc, dnp=False, note="", fit="JLC", ds=""):
        return {"Footprint": fp, "Datasheet": ds, "Description": note, "LCSC": lcsc, "Fit": "DNP" if dnp else fit}


    def Rp(val, lcsc, note="", fp=R0402, dnp=False):
        return dict(lib="Device:R", val=val, props=props(fp, lcsc, dnp, note), a=0, top="1", bot="2", dnp=dnp)


    def Cp(val, lcsc, note="", fp=C0402, dnp=False):
        return dict(lib="Device:C", val=val, props=props(fp, lcsc, dnp, note), a=0, top="1", bot="2", dnp=dnp)


    def LEDp(val, lcsc, fp, note=""):
        return dict(lib="Device:LED", val=val, props=props(fp, lcsc, note=note), a=90, top="2", bot="1", dnp=False)


    def place(ref, e, x, y, top, bot):
        fields = "left" if e["a"] == 0 else ((x + 2.54, y - 1.27, "right"), (x + 2.54, y + 1.27, "right"))
        s.part(e["lib"], ref, e["val"], x, y, {e["top"]: top, e["bot"]: bot}, a=e["a"], props=e["props"],
               dnp=e["dnp"], fields=fields)


    STEP = 12.7


    def chain(x, y0, elems, top, bottom, taps=None):
        """Vertical series chain of two-pin parts. elems: [(ref, spec)]. taps = {i: net or ("wire", x_end)}:
        the joint below part i gets a labelled stub, or a wire to x_end (to meet another part's pin)."""
        taps = taps or {}
        for i, (ref, e) in enumerate(elems):
            y = y0 + i * STEP
            place(ref, e, x, y, top if i == 0 else None, bottom if i == len(elems) - 1 else None)
            if i == len(elems) - 1:
                break
            nref, ne = elems[i + 1]
            ya, yb = y + 3.81, y + STEP - 3.81
            tap = taps.get(i)
            net = tap if isinstance(tap, str) else f"~{ref}-{nref}"
            if tap is None:
                s.wire(x, ya, x, yb)
            else:
                ty = y + STEP / 2
                s.wire(x, ya, x, ty)
                s.wire(x, ty, x, yb)
                s.junction(x, ty)
                if isinstance(tap, str):
                    s.wire(x, ty, x + G, ty)
                    s.net_at(tap, x + G, ty, 0)
                else:
                    s.wire(x, ty, tap[1], ty)
            s.intended[(ref, e["bot"])] = net
            s.intended[(nref, ne["top"])] = net
        return {i: y0 + i * STEP + STEP / 2 for i in taps}


    def heading(t, x, y, body=""):
        s.text(t, x, y, 2.0, bold=True)
        if body:
            s.text(body, x, y + 4.5, 1.27)


    s.rect(12.7, 12.7, 213.36, 142.24)
    s.rect(218.44, 12.7, 406.4, 142.24)
    s.rect(12.7, 147.32, 406.4, 246.38)

    # ================= CC detection =================
    heading("USB-C current advertisement (CC detection)", 20.32, 20.32,
            "Is the host port allowed to give us >= 1.5 A? If so, pull TERMPWR_EN_INVERTED low. Hardware only, no firmware.")

    # threshold reference: R203 feeds the CJ431 shunt, which holds CC_REFERENCE_2V5 at 2.500 V;
    # R204-R206 divide that down to CC_THRESHOLD = 0.653 V
    chain(38.1, 45.72, [("R203", Rp("470R", "C25117", "CJ431 bias, >= 1.21 mA")),
                        ("R204", Rp("10k", "C25744", "Threshold divider top (10k + 3.3k)")),
                        ("R205", Rp("3.3k", "C25890", "Threshold divider top (10k + 3.3k)")),
                        ("R206", Rp("4.7k", "C25900", "Threshold divider bottom"))],
          "+3V3", "GND", taps={0: ("wire", 50.8), 2: "CC_THRESHOLD"})
    # nominal node voltages beside the chain (+3V3 = 3.30 V; U203 holds the top node at 2.500 V)
    for ty, v in ((52.07, "2.50 V"), (64.77, "1.11 V"), (77.47, "0.653 V")):
        s.note(v, 25.4, ty - 0.635)
    RY = 45.72 + 12.7 / 2          # the R203/R204 joint
    KX, KY = 58.42, 62.23          # U203 placed so cathode is on top, REF on the left
    s.part("scsi-adapter:CJ431", "U203", "CJ431", KX, KY, {"2": None, "1": None, "3": "GND"}, a=90,
           props=props("Package_TO_SOT_SMD:SOT-23", "C3113", note="2.500 V shunt reference, REF tied to cathode"),
           fields=((KX + 3.81, KY - 1.27, "right"), (KX + 3.81, KY + 1.27, "right")))
    s.wire(50.8, RY, KX, RY)
    s.wire(KX, RY, KX, KY - 2.54)            # to cathode
    s.wire(KX - 2.54, KY, 50.8, KY)          # from REF
    s.wire(50.8, KY, 50.8, RY)
    s.junction(50.8, RY)
    s.net_at("CC_REFERENCE_2V5", KX, RY, 0)
    for k in (("R203", "2"), ("R204", "1"), ("U203", "1"), ("U203", "2")):
        s.intended[k] = "CC_REFERENCE_2V5"
    s.note("CJ431 (U203) is a shunt regulator: it sinks current into its cathode (top) until its\n"
           "reference (side) sits at 2.500 V. REF is tied to the cathode, so the cathode is the 2.500 V output.\n"
           "It needs a bias resistor from the cathode to a supply, sized so it always gets at least 1 mA\n"
           "(its minimum for regulation). R203 470R from +3V3, nominal at 3.30 V:\n"
           "  R203: (3.30 - 2.50) / 470 = 1.70 mA; R204-R206 (18.0k) take 2.50 / 18.0k = 0.14 mA;\n"
           "  U203 sinks the rest, 1.56 mA (>= 1.21 mA worst case). CC_THRESHOLD = 2.500 x 4.7/18.0 = 0.653 V.\n"
           "Why a reference: the CC decision window is only 0.61-0.70 V. The +3V3 rail itself is +-3 %,\n"
           "which alone would move a rail-derived threshold by +-20 mV; the CJ431 is +-1 % (+-0.5 % rank).",
           20.32, 97.79)

    # comparators: CC through 10k / 1 uF (10 ms) into the inverting inputs
    CMP = props("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C7955", ds="https://www.onsemi.com/pdf/datasheet/lm393-d.pdf",
                note="LM393DR2G dual open-collector comparator")
    for unit, (cc, yc, rref, cref) in enumerate((("CC1", 60.96, "R201", "C201"), ("CC2", 91.44, "R202", "C202")), 1):
        ux = 142.24
        s.part("Comparator:LM393", "U202", "LM393DR2G", ux, yc,
               {"3" if unit == 1 else "5": "CC_THRESHOLD", "2" if unit == 1 else "6": None,
                "1" if unit == 1 else "7": EN_NODE},
               props=CMP, unit=unit, fields=((ux - 2.54, yc - 6.35, "left"), (ux - 2.54, yc + 6.35, "left")))
        yin = yc + 2.54                               # inverting input row
        rx = 104.14
        s.part("Device:R", rref, "10k", rx, yin, {"1": cc, "2": None}, a=90,
               props=props(R0402, "C25744", note=f"{cc} filter, 10 ms with {cref}"),
               fields=((rx, yin - 3.81, ""), (rx, yin + 3.81, "")))
        jx, lx = 111.76, 114.3
        s.wire(rx + 3.81, yin, jx, yin)
        s.wire(jx, yin, lx, yin)
        s.wire(lx, yin, ux - 7.62, yin)
        s.junction(jx, yin)
        s.net_at(f"{cc}_FILTERED", lx, yin, 0)
        s.wire(jx, yin, jx, yin + 3.81)
        s.part("Device:C", cref, "1uF 25V", jx, yin + 7.62, {"1": None, "2": "GND"},
               props=props(C0402, "C52923", note=f"{cc} filter"), fields="left")
        net = f"{cc}_FILTERED"
        for k in ((rref, "2"), (cref, "1"), ("U202", "2" if unit == 1 else "6")):
            s.intended[k] = net
    s.part("Comparator:LM393", "U202", "LM393DR2G", 190.5, 76.2, {"8": "+5V_SYS", "4": "GND"},
           props=CMP, unit=3, fields=((190.5, 86.36, "left"), (190.5, 88.9, "left")))
    s.part("Device:C", "C203", "100nF 50V", 205.74, 76.2, {"1": "+5V_SYS", "2": "GND"},
           props=props(C0402, "C307331", note="LM393 decoupling"), fields="left")
    s.part("Device:R", "R207", "1M", 165.1, 106.68, {"1": EN_NODE, "2": "CC_THRESHOLD"},
           props=props(R0402, "C26083", note="Hysteresis"), fields="left")
    s.note("CC voltage across our 5.1k Rd (usb-hub sheet): default USB <= 0.61 V, 1.5 A >= 0.70 V, 3 A >= 1.23 V.\n"
           "Only one CC is active (plug orientation), so each gets a comparator; the open-collector outputs are wired together.\n"
           "CC above CC_THRESHOLD -> output pulls TERMPWR_EN_INVERTED low. R207 adds hysteresis: 0.661 V rising / 0.651 V falling.\n"
           "Worst case (1 % R, +3V3 3.16-3.44 V, LM393 offset/bias, CJ431 tolerance and tempco): +6 to +11 mV inside the window.\n"
           "10 ms filters average out USB PD traffic (~1 ms bursts on CC). LM393 runs from +5V_SYS: its inputs work only up to\n"
           "Vcc - 1.5 V and a 3 A port puts ~2 V on CC. No capacitor on the CJ431 cathode: TL431-type shunts can oscillate with one.",
           20.32, 121.92)

    # ================= TERMPWR enable node =================
    heading("TERMPWR enable (TERMPWR_EN_INVERTED)", 226.06, 20.32,
            "Low = we supply TERMPWR. Wired-OR: either comparator (USB port offers >= 1.5 A) or Q201 (bench supply present).")
    s.part("Device:R", "R208", "10k", 236.22, 63.5, {"1": "+3V3", "2": EN_NODE},
           props=props(R0402, "C25744", note="Enable node pull-up"), fields="left")
    chain(274.32, 55.88, [("R209", Rp("1k", "C11702", "Enable LED")),
                          ("D201", LEDp("KT-0603R red", "C2286", "LED_SMD:LED_0603_1608Metric",
                                        "Lit = we are supplying TERMPWR"))],
          "+3V3", EN_NODE)
    QX, QY = 335.28, 62.23
    tap_y = chain(317.5, 55.88, [("R210", Rp("10k", "C25744", "Gate series (keeps a 24 V mistake off the gate)")),
                                 ("R211", Rp("100k", "C25741", "Gate pull-down"))],
                  "BENCH_5V", "GND", taps={0: ("wire", QX - 5.08)})
    s.part("Transistor_FET:2N7002", "Q201", "2N7002", QX, tap_y[0],
           {"1": None, "3": EN_NODE, "2": "GND"},
           props=props("Package_TO_SOT_SMD:SOT-23", "C8545", note="Bench present -> enable TERMPWR"),
           fields=((QX + 5.08, tap_y[0] - 1.27, "left"), (QX + 5.08, tap_y[0] + 1.27, "left")))
    s.intended[("Q201", "1")] = "~R210-R211"
    s.note("With the TPS2116 in priority mode, 'bench present' also means the bench is powering the board.\n"
           "Q201's gate comes from the bench eFuse output (BENCH_5V), 4.5 V at 5 V, never the raw terminal.\n"
           "The node sits at ~3.0 V when high (R208 against the eFuse OVLO divider R215/R216), not 3.3 V.\n"
           "The expander reads this node (P01), so firmware can tell why TERMPWR is on or off.\n"
           "For a few ms at power-up (+5V_SYS up, +3V3 not yet) the node reads low: harmless, the bus is idle.",
           226.06, 96.52)

    # ================= TERMPWR switch =================
    heading("TERMPWR switch (eFuse)", 20.32, 154.94,
            "Current limit 1.22 A (1.06-1.39 A): >= 900 mA required, <= 1.5 A recommended (SCSI-2 5.4.3). True reverse blocking,\n"
            "even unpowered, so another device's TERMPWR can't back-feed the board.")
    UX, UY = 162.56, 190.5
    s.part("scsi-adapter:TPS259470A", "U201", "TPS259470ARPWR", UX, UY,
           {"5": "+5V_SYS", "1": "TERMPWR_EFUSE_EN", "2": "TERMPWR_EFUSE_OV", "6": "TERMPWR_EFUSE_OUT",
            "4": "TERMPWR_EFUSE_FAULT_INVERTED", "3": "NC", "7": None, "9": None, "10": None, "8": "GND"},
           props=props("scsi-adapter:Texas_RPW0010A_VQFN-HR-10_2x2mm_P0.45mm", "C3662799", note="TERMPWR eFuse",
                       ds="https://www.ti.com/lit/ds/symlink/tps25947.pdf"),
           fields=((UX - 15.24, UY - 8.89, "left"), (UX + 15.24, UY - 8.89, "right")))
    BY = UY + 10.16 + 2.54 + 3.81
    for dx, ref, pin, net in ((-12.7, "C204", "1", "DVDT"), (-2.54, "R217", "1", "ILM"), (7.62, "C205", "1", "ITIMER")):
        s.wire(UX + dx, UY + 10.16, UX + dx, UY + 12.7)
        s.intended[(ref, pin)] = net
    s.intended[("U201", "7")], s.intended[("U201", "9")], s.intended[("U201", "10")] = "DVDT", "ILM", "ITIMER"
    place("C204", Cp("2.2nF", "C1531", "dVdt"), UX - 12.7, BY, None, "GND")
    chain(UX - 2.54, BY, [("R217", Rp("2.4k", "C25882", "R_ILM (2.4k + 330 = 2.73k)")),
                          ("R218", Rp("330R", "C25104", "R_ILM (2.4k + 330 = 2.73k)"))], None, "GND")
    place("C205", Cp("1nF", "", "ITIMER, DNP", dnp=True), UX + 7.62, BY, None, "GND")
    s.note("eFuse setting pins:\n"
           "C204 on DVDT (dV/dt, output voltage slew rate): turn-on\n  ramp, only at power-up; enabling through OVLO skips it.\n"
           "R217 + R218 on ILM (I-limit: sets the current limit, and the pin\n  voltage doubles as a load-current monitor): 1.22 A (R = 3334 / I).\n"
           "  2.73k from two no-fee parts; a single 2.4k could reach 1.59 A.\n"
           "C205 on ITIMER (I-timer: overcurrent blanking timer), DNP. Open =\n  limit strictly at 1.22 A, which suits SCSI-2's <= 1.5 A.\n"
           "  Fit ~1 nF (~0.84 ms) only if normal load steps trip it.", 182.88, 203.2)

    chain(30.48, 190.5, [("R213", Rp("39k", "C25783", "EN/UVLO top")), ("R214", Rp("15k", "C25756", "EN/UVLO bottom"))],
          "+5V_SYS", "GND", taps={0: "TERMPWR_EFUSE_EN"})
    s.note("UVLO: on above\n1.20 x 54/15\n= 4.32 V", 38.1, 212.09)
    chain(76.2, 190.5, [("R215", Rp("56k", "C25796", "OVLO divider top")), ("R216", Rp("47k", "C25792", "OVLO divider bottom"))],
          EN_NODE, "GND", taps={0: "TERMPWR_EFUSE_OV"})
    s.note("OVLO as active-low enable:\nnode high (~3.0 V) -> OVLO\n1.31-1.43 V > 1.22 V: off.\n"
           "node low (<= 0.7 V) -> OVLO\n<= 0.32 V < 1.08 V: on.", 83.82, 212.09)
    place("C206", Cp("100nF 50V", "C307331", "eFuse IN"), 109.22, 196.85, "+5V_SYS", "GND")

    # output side: eFuse OUT -> jumper -> TERMPWR
    place("C207", Cp("1uF 25V", "C52923", "eFuse OUT"), 248.92, 196.85, "TERMPWR_EFUSE_OUT", "GND")
    s.part("Device:D_Schottky", "D203", "SS14", 281.94, 196.85, {"1": "TERMPWR_EFUSE_OUT", "2": "GND"}, a=270,
           props=props("Diode_SMD:D_SMA", "C2480", True, "Negative-spike clamp on eFuse OUT, DNP"), dnp=True,
           fields=((284.48, 195.58, "right"), (284.48, 198.12, "right")))
    s.note("D203 DNP: TI suggests it against the\nnegative spike when the eFuse cuts a long\n"
           "cable. Fit only if OUT dips below -0.8 V\non the scope; its leakage counts against\n"
           "SCSI-2's 1 mA TERMPWR budget.", 264.16, 213.36)
    s.part("Connector_Generic:Conn_01x02", "J201", "TERMPWR jumper", 312.42, 187.96,
           {"1": "TERMPWR_EFUSE_OUT", "2": "TERMPWR"}, a=180,
           props=props("Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "", fit="Hand",
                       note="Shunt fitted = supply TERMPWR. Remove to never supply it."),
           fields=((309.88, 182.88, "right"), (309.88, 193.04, "right")))
    s.note("J201: shunt fitted = the board may supply TERMPWR\n(normal). Remove it to never drive TERMPWR, whatever\n"
           "CC or the bench say: e.g. another device already\nsupplies it, or to isolate a TERMPWR fault (R2a).",
           297.18, 165.1)
    s.part("Device:D_Zener", "D204", "SMF6.0A", 345.44, 196.85, {"1": "TERMPWR", "2": "GND"}, a=270,
           props=props("Diode_SMD:D_SOD-123F", "C19077499", note="TERMPWR ESD / TVS"),
           fields=((347.98, 195.58, "right"), (347.98, 198.12, "right")))
    chain(370.84, 190.5, [("R212", Rp("10k", "C25744", "TERMPWR present LED")),
                          ("D202", LEDp("KT-0805Y yellow", "C2296", "LED_SMD:LED_0805_2012Metric",
                                        "Lit = TERMPWR is present (from us or any device on the bus)"))],
          "TERMPWR", "GND")
    s.pwr_flag("#FLG201", "TERMPWR", 393.7, 180.34)
    s.note("TERMPWR also arrives from other devices on the bus,\n"
           "hence the PWR_FLAG to tell KiCad that TERMPWR is powered\n"
           "from outside the drawn parts (through J201 and the bus), so\n"
           "ERC doesn't report 'power input not driven'.\n\n"
           "D202 (yellow) shows TERMPWR from anyone;\nD201 (red) shows that we supply it.\n\n"
           "Our non-terminator draw from TERMPWR: D202 0.35 mA +\n"
           "ADC divider (rp2350 sheet) 0.03 mA + eFuse leakage\n<= 0.44 mA = 0.82 mA, under SCSI-2's 1 mA.",
           332.74, 220.98)
    s.note("Enabling through OVLO skips the dVdt ramp: TERMPWR\nrises at the 1.22 A limit (~0.2 ms into 50 uF). Harmless.",
           320.04, 154.94)

    s.write(out_path)
    return s.intended
