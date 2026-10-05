"""Populate pcb/1-power.kicad_sch. Values and parts: design_docs/3-driver/parts-list.md §1 and
NOTES "Resistor and small-part values", "Power mux", "eFuse startup", "Bench 5 V input protection",
"Terminator LDO"."""
from schgen import Sheet, G

FILE = "1-power.kicad_sch"
FILE_UUID = "2878b58b-b435-4b0a-bf30-9c356a27963a"      # the sheet file's own uuid; keep it stable

ROOT = "2c5b21a9-7d0d-4304-8bd9-0602cba3b7b5"
SHEET_SYM = "c5f4e78b-92c1-44f5-913e-e393dcfaf39d"      # the "power" sheet symbol on the root
def build(out_path):
    """Write the sheet to out_path; return the intended {(ref, pin): net} map."""
    s = Sheet(FILE_UUID, "A3", "SCSI scanner adapter", f"/{ROOT}/{SHEET_SYM}")
    s.refbase = 100
    s.rails = {"+5V_SYS", "+3V3", "VTERMINATOR", "TERMPWR"}
    s.hier = {"VBUS": "input", "BENCH_5V": "output", "IS_BENCH_POWERED": "output", "BENCH_EFUSE_FAULT_INVERTED": "output"}

    R0402, R0603 = "Resistor_SMD:R_0402_1005Metric", "Resistor_SMD:R_0603_1608Metric"
    C0402, C0805 = "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0805_2012Metric"


    def props(fp, lcsc, dnp=False, note="", fit="JLC"):
        return {"Footprint": fp, "Datasheet": "", "Description": note, "LCSC": lcsc, "Fit": "DNP" if dnp else fit}


    def R(ref, val, lcsc, x, y, top, bot, fp=R0402, dnp=False, fields="left", note=""):
        s.part("Device:R", ref, val, x, y, {"1": top, "2": bot}, props=props(fp, lcsc, dnp, note), dnp=dnp, fields=fields)


    def C(ref, val, lcsc, x, y, top, bot, fp=C0402, dnp=False, fields="left", note=""):
        s.part("Device:C", ref, val, x, y, {"1": top, "2": bot}, props=props(fp, lcsc, dnp, note), dnp=dnp, fields=fields)


    STEP = 12.7          # centre-to-centre spacing of parts in a vertical chain


    def chain(x, y0, parts, top, bottom, taps=None):
        """Vertical series chain. parts: list of (lib, ref, val, lcsc, kwargs). Adjacent parts are
        joined by a wire; taps = {i: net} labels the joint below part i with a stub to the right."""
        taps = taps or {}
        n = len(parts)
        for i, (lib, ref, val, lcsc, kw) in enumerate(parts):
            y = y0 + i * STEP
            t = top if i == 0 else None
            b = bottom if i == n - 1 else None
            (R if lib == "R" else C)(ref, val, lcsc, x, y, t, b, **kw)
            if i < n - 1:
                nxt = parts[i + 1][1]
                ya, yb = y + 3.81, y + STEP - 3.81
                net = taps.get(i, f"~{ref}-{nxt}")
                if i in taps:
                    ty = y + STEP / 2
                    s.wire(x, ya, x, ty)
                    s.wire(x, ty, x, yb)
                    s.junction(x, ty)
                    s.wire(x, ty, x + G, ty)
                    s.net_at(net, x + G, ty, 0)
                else:
                    s.wire(x, ya, x, yb)
                s.intended[(ref, "2")] = net
                s.intended[(nxt, "1")] = net


    def heading(t, x, y, body=""):
        s.text(t, x, y, 2.0, bold=True)
        if body:
            s.text(body, x, y + 4.5, 1.27)


    # section boxes
    s.rect(12.7, 12.7, 213.36, 152.4)
    s.rect(218.44, 12.7, 406.4, 152.4)
    s.rect(12.7, 157.48, 213.36, 246.38)
    s.rect(218.44, 157.48, 406.4, 246.38)

    # ============ Bench 5 V input and eFuse ============
    heading("Bench 5 V input", 20.32, 20.32,
            "Set the bench supply to 5.0 V (5.1 V max). eFuse: OVLO 5.35 V, UVLO 4.22 V, ILIM 2.22 A, auto-retry.\n"
            "String R101-R105: UV = 1.2 x 712.9k/202.9k, OV = 1.2 x 712.9k/160k. D102 keeps EN <= 6.5 V abs max on a 24 V mistake.")

    s.part("Connector:Screw_Terminal_01x02", "J101", "Bench 5V", 55.88, 45.72,
           {"1": "BENCH_RAW", "2": "GND"},
           props=props("scsi-adapter:TerminalBlock_Kangnex_WJ500V-5.08-2P_1x02_P5.08mm_Horizontal", "C8465", note="Kangnex WJ500V-5.08-2P, 5.08 mm", fit="Hand"),
           fields=((55.88, 40.64, "left"), (55.88, 52.07, "left")))
    s.pwr_flag("#FLG101", "BENCH_RAW", 71.12, 38.1)
    s.note("PWR_FLAG is not a part. It tells KiCad's ERC that a net\nis powered from outside the drawn symbols (the terminal,\n"
           "USB VBUS), so it doesn't report 'power input not driven'.", 66.04, 48.26)
    s.pwr_flag("#FLG102", "GND", 83.82, 38.1)
    # TP101 (BENCH+) and TP102 (GND) test loops were removed during layout: probe the bench voltage at J101.

    s.part("Device:D_TVS", "D101", "SMF15CA", 50.8, 71.12, {"1": "BENCH_RAW", "2": "GND"}, a=270,
           props=props("Diode_SMD:D_SOD-123F", "C19077510", True, "Bidirectional TVS, footprint only"), dnp=True,
           fields=((53.34, 69.85, "right"), (53.34, 72.39, "right")))
    s.note("DNP. Fit if the terminal sees hot-plug\nspikes above the eFuse's 28 V abs max\n"
           "(long leads, inductive supply).", 38.1, 88.9)
    C("C101", "1uF 50V X7R", "C28323", 83.82, 71.12, "BENCH_RAW", "GND", fp=C0805)
    C("C102", "100nF 50V", "C307331", 101.6, 71.12, "BENCH_RAW", "GND")

    # eFuse U101
    UX, UY = 154.94, 50.8
    s.part("scsi-adapter:TPS259470A", "U101", "TPS259470ARPWR", UX, UY,
           {"5": "BENCH_RAW", "1": "BENCH_EFUSE_EN", "2": "BENCH_EFUSE_OV", "6": "BENCH_5V", "4": "BENCH_EFUSE_FAULT_INVERTED", "3": "NC",
            "7": None, "9": None, "10": None, "8": "GND"},
           props=dict(props("scsi-adapter:Texas_RPW0010A_VQFN-HR-10_2x2mm_P0.45mm", "C3662799", note="Bench eFuse"),
                      Datasheet="https://www.ti.com/lit/ds/symlink/tps25947.pdf"),
           fields=((UX - 15.24, UY - 8.89, "left"), (UX + 15.24, UY - 8.89, "right")))
    BY = UY + 10.16 + 2.54 + 3.81     # bottom-pin parts hang straight below the IC pins
    for dx, ref, net in ((-12.7, "C103", "DVDT"), (-2.54, "R106", "ILM"), (7.62, "C104", "ITIMER")):
        s.wire(UX + dx, UY + 10.16, UX + dx, UY + 12.7)
        s.intended[(ref, "1")] = net
    s.intended[("U101", "7")], s.intended[("U101", "9")], s.intended[("U101", "10")] = "DVDT", "ILM", "ITIMER"
    C("C103", "2.2nF", "C1531", UX - 12.7, BY, None, "GND", note="dVdt: ~5.5 ms ramp")
    R("R106", "1.5k", "C25867", UX - 2.54, BY, None, "GND", note="R_ILM: 2.22 A")
    C("C104", "1nF", "", UX + 7.62, BY, None, "GND", dnp=True, note="ITIMER: open by default")
    s.note("eFuse setting pins:\n"
           "C103 on DVDT (dV/dt, output voltage slew\n  rate): ~5.5 ms ramp to 5 V (limits inrush).\n"
           "R106 on ILM (I-limit: sets the current limit;\n  the pin voltage is also a current monitor):\n  2.22 A (R = 3334 / I).\n"
           "C104 on ITIMER (I-timer), DNP: overcurrent\n  blanking timer (how long current may\n  exceed the limit before the eFuse acts).\n"
           "  Open = shortest. Fit ~1 nF (~0.84 ms) if normal\n"
           "  load steps trip the limit (FAULT pulses\n  at bring-up).", 172.72, 83.82)
    C("C105", "1uF 25V", "C52923", 193.04, 132.08, "BENCH_5V", "GND", note="eFuse OUT / TPS2116 VIN1")

    # UVLO/OVLO string as a vertical chain, EN clamp beside it
    chain(127.0, 86.36, [("R", "R101", "510k", "C11616", {"note": "String R1"}),
                        ("R", "R102", "39k", "C25783", {"note": "String R2 (39k + 3.9k)"}),
                        ("R", "R103", "3.9k", "C51721", {"note": "String R2 (39k + 3.9k)"}),
                        ("R", "R104", "150k", "C25755", {"note": "String R3 (150k + 10k)"}),
                        ("R", "R105", "10k", "C25744", {"note": "String R3 (150k + 10k)"})],
          "BENCH_RAW", "GND", taps={0: "BENCH_EFUSE_EN", 2: "BENCH_EFUSE_OV"})
    # nominal tap voltages (BENCH_RAW = 5.0 V, 7.01 uA through 712.9k)
    for ty, v in ((92.71, "1.42 V"), (105.41, "1.15 V"), (118.11, "1.12 V"), (130.81, "0.07 V")):
        s.note(v, 115.57, ty - 0.635)
    s.note(
        "UVLO/OVLO string R101-R105 (712.9k total). Tap voltages at left are nominal for BENCH_RAW = 5.0 V (7.0 uA).\n"
        "EN/UVLO and OVLO share one threshold: 1.20 V rising, 1.09 V falling (typ; 1.183-1.223 / 1.076-1.116 V).\n"
        "BENCH_EFUSE_EN = BENCH_RAW x (R102..R105 = 202.9k) / 712.9k\n"
        "    turns on above 1.20 x 712.9 / 202.9 = 4.22 V, off below 1.09 x 712.9 / 202.9 = 3.83 V.\n"
        "    1.42 V at 5.0 V: on, with 0.22 V margin.\n"
        "BENCH_EFUSE_OV = BENCH_RAW x (R104 + R105 = 160k) / 712.9k\n"
        "    trips off above 1.20 x 712.9 / 160 = 5.35 V, recovers below 1.09 x 712.9 / 160 = 4.86 V.\n"
        "    1.12 V at 5.0 V: 78 mV under the trip, but inside the hysteresis band, so after a trip\n"
        "    the bench must come back below 4.86 V before the eFuse turns on again.\n"
        "Worst case (thresholds, 1 % R, +-0.1 uA pin leakage): UV 4.05-4.41 V, OV 5.14-5.59 V.\n"
        "R102 + R103 = 42.9k and R104 + R105 = 160k: no 43k or 160k 0402 1 % part is JLC basic/preferred,\n"
        "    so each is two no-fee parts. The unlabelled joints carry no function.\n"
        "R101 = 510k keeps the string >= 350k (TI's reverse-polarity guidance). Much bigger and the\n"
        "    +-0.1 uA pin leakage moves the OV trip enough to break the 5.5 V limit (NOTES, R059/R061).",
        20.32, 104.14)
    s.part("Device:D_Zener", "D102", "BZT52C5V6", 147.32, 101.6, {"1": "BENCH_EFUSE_EN", "2": "GND"}, a=270,
           props=props("Diode_SMD:D_SOD-123", "C19077402", note="EN clamp"),
           fields=((149.86, 100.33, "right"), (149.86, 102.87, "right")))

    # ============ Power mux ============
    heading("Power mux (bench priority)", 226.06, 20.32,
            "TPS2116 priority mode: MODE tied to VIN1. PR1 (MUX_BENCH_DETECT) = 0.281 x VIN1, so the bench wins above ~3.6 V.\n"
            "ST (IS_BENCH_POWERED) is high while running on the bench. VBUS snubber R110 + C107 damps plug-in ringing (5.7 uF on VBUS total).")
    MX, MY = 294.64, 50.8
    s.part("Power_Management:TPS2116DRL", "U102", "TPS2116DRLR", MX, MY,
           {"3": "BENCH_5V", "4": "MUX_BENCH_DETECT", "5": "BENCH_5V", "6": "VBUS", "1": "GND", "7": "+5V_SYS", "2": "+5V_SYS",
            "8": "IS_BENCH_POWERED"},
           props=dict(props("Package_TO_SOT_SMD:SOT-583-8", "C3235557", note="Power mux U1 in NOTES"),
                      Datasheet="https://www.ti.com/lit/ds/symlink/tps2116.pdf"),
           fields=((MX - 7.62, MY - 8.89, "left"), (MX + 2.54, MY + 12.7, "left")))
    s.pwr_flag("#FLG103", "VBUS", 254.0, 38.1)
    chain(241.3, 88.9, [("R", "R107", "100k", "C25741", {"note": "PR1 divider"}),
                        ("R", "R108", "39k", "C25783", {"note": "PR1 divider"})],
          "BENCH_5V", "GND", taps={0: "MUX_BENCH_DETECT"})
    C("C106", "1uF 25V", "C52923", 279.4, 95.25, "VBUS", "GND", note="VIN2")
    chain(297.18, 88.9, [("R", "R110", "1R", "C22936", {"fp": R0603, "note": "VBUS snubber"}),
                         ("C", "C107", "4.7uF 25V", "C1779", {"fp": C0805, "note": "VBUS snubber"})],
          "VBUS", "GND")
    s.text("VBUS snubber\n(reduce USB cable ringing)", 302.26, 109.22, 1.27)
    R("R109", "10k", "C25744", 322.58, 95.25, "+3V3", "IS_BENCH_POWERED", note="ST pull-up")
    C("C108", "100nF 50V", "C307331", 353.06, 95.25, "+5V_SYS", "GND")
    C("C109", "22uF 25V", "C45783", 373.38, 95.25, "+5V_SYS", "GND", fp=C0805, note="+5V_SYS bulk")

    # ============ 3.3 V LDO ============
    heading("3.3 V logic rail", 20.32, 165.1,
            "Vout = 1.204 x (R113 + R114) / R114 = 3.30 V. EN on above ~4.0 V (100k/75k).\n"
            "FEEDBACK: the LDO adjusts OUT until its FB pin sits at its 1.204 V reference, so the divider sets Vout.")
    LDO = props("Package_TO_SOT_SMD:SOT-223-6", "C56848")
    LDO["Datasheet"] = "https://www.ti.com/lit/ds/symlink/tps737.pdf"
    LX, LY = 88.9, 185.42
    s.part("scsi-adapter:TPS73701DCQ", "U103", "TPS73701DCQR", LX, LY,
           {"1": "+5V_SYS", "5": "LDO_3V3_EN", "2": "+3V3", "4": "LDO_3V3_FEEDBACK", "3": "GND", "6": "GND"},
           props=dict(LDO, Description="3.3 V logic LDO"),
           fields=((LX - 7.62, LY - 6.35, "left"), (LX + 10.16, LY + 7.62, "left")))
    C("C110", "1uF 25V", "C52923", 30.48, 212.09, "+5V_SYS", "GND", note="LDO C_IN")
    chain(48.26, 205.74, [("R", "R111", "100k", "C25741", {"note": "EN divider"}),
                          ("R", "R112", "75k", "C25798", {"note": "EN divider"})],
          "+5V_SYS", "GND", taps={0: "LDO_3V3_EN"})
    chain(111.76, 205.74, [("R", "R113", "47k", "C25792", {"note": "FB R1"}),
                           ("R", "R114", "27k", "C25771", {"note": "FB R2"})],
          "+3V3", "GND", taps={0: "LDO_3V3_FEEDBACK"})
    R("R115", "1M", "", 149.86, 218.44, "LDO_3V3_FEEDBACK", "GND", fp=R0603, dnp=True, note="Trim, DNP")
    s.note("R115 DNP: trim pad across R114. Fit ~1M if\n+3V3 measures low at bring-up (+55 mV).", 137.16, 233.68)
    C("C111", "10uF 25V", "C15850", 185.42, 212.09, "+3V3", "GND", fp=C0805, note="LDO C_OUT")

    # ============ 2.83 V terminator LDO ============
    heading("2.83 V terminator rail (VTERMINATOR)", 226.06, 165.1,
            "Powered from TERMPWR (SCSI-2 5.4.1). Vout = 1.204 x (44.6k + 33k) / 33k = 2.83 V (2.72-2.94 V worst case).\n"
            "R121 bleed keeps >= 10 mA load (TPS737 accuracy spec) and sinks current pushed in from the bus.")
    TX, TY = 294.64, 185.42
    s.part("scsi-adapter:TPS73701DCQ", "U104", "TPS73701DCQR", TX, TY,
           {"1": "TERMPWR", "5": "LDO_TERMINATOR_EN", "2": "VTERMINATOR", "4": "LDO_TERMINATOR_FEEDBACK", "3": "GND", "6": "GND"},
           props=dict(LDO, Description="2.83 V terminator LDO"),
           fields=((TX - 7.62, TY - 6.35, "left"), (TX + 10.16, TY + 7.62, "left")))
    C("C112", "1uF 25V", "C52923", 236.22, 212.09, "TERMPWR", "GND", note="LDO C_IN")
    chain(256.54, 205.74, [("R", "R116", "100k", "C25741", {"note": "EN divider"}),
                           ("R", "R117", "75k", "C25798", {"note": "EN divider"})],
          "TERMPWR", "GND", taps={0: "LDO_TERMINATOR_EN"})
    chain(335.28, 205.74, [("R", "R118", "39k", "C25783", {"note": "FB R1 (39k + 5.6k)"}),
                          ("R", "R119", "5.6k", "C25908", {"note": "FB R1 (39k + 5.6k)"}),
                          ("R", "R120", "33k", "C25779", {"note": "FB R2"})],
          "VTERMINATOR", "GND", taps={1: "LDO_TERMINATOR_FEEDBACK"})
    C("C113", "10uF 25V", "C15850", 375.92, 212.09, "VTERMINATOR", "GND", fp=C0805, note="LDO C_OUT")
    R("R121", "270R", "C22966", 396.24, 212.09, "VTERMINATOR", "GND", fp=R0603, note="Bleed, 10.5 mA, 30 mW")

    s.write(out_path)
    return s.intended
