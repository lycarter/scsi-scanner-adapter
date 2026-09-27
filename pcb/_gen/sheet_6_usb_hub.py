"""USB-C and hub: pcb/6-usb-hub.kicad_sch.

Sources: blocks/4-usb.md, NOTES "USB hub", "ESD protection", "Connectors", "Resistor and small-part values"
(CH334 RESET#), parts-list.md §4; CH334 English datasheet V2.5 (pinout Fig. 1-1, PGANG 3.3.5).
"""
from schgen import Sheet, G

FILE = "6-usb-hub.kicad_sch"
FILE_UUID = "ae00fc07-ca5b-45f0-a859-79185e98da25"
ROOT = "2c5b21a9-7d0d-4304-8bd9-0602cba3b7b5"
SHEET_SYM = "f4f05d64-3bc1-4f44-b9d1-cb96479fcfcc"          # the "usb-hub" sheet symbol on the root

R0402, C0402, C0805 = ("Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric",
                       "Capacitor_SMD:C_0805_2012Metric")


def props(fp, lcsc, dnp=False, note="", fit="JLC", ds=""):
    return {"Footprint": fp, "Datasheet": ds, "Description": note, "LCSC": lcsc, "Fit": "DNP" if dnp else fit}


def heading(s, t, x, y, body=""):
    s.text(t, x, y, 2.0, bold=True)
    if body:
        s.text(body, x, y + 4.5, 1.27)


def build(path):
    s = Sheet(FILE_UUID, "A3", "SCSI scanner adapter", f"/{ROOT}/{SHEET_SYM}", seed=FILE)
    s.refbase = 600
    s.rails = {"+3V3"}
    s.hier = {"USB_FT_D+": "bidirectional", "USB_FT_D-": "bidirectional", "USB_RP_D+": "bidirectional",
              "USB_RP_D-": "bidirectional", "HUB_RESET_INVERTED": "input", "VBUS": "output", "CC1": "output",
              "CC2": "output"}

    def vpart(lib, ref, val, x, y, top, bot, pr, a=0, tp="1", bp="2", dnp=False):
        s.part(lib, ref, val, x, y, {tp: top, bp: bot}, a=a, props=pr, dnp=dnp,
               fields="left" if a == 0 else ((x + 2.54, y - 1.27, "right"), (x + 2.54, y + 1.27, "right")))

    # ================= USB-C connector =================
    s.rect(12.7, 12.7, 162.56, 175.26)
    heading(s, "USB-C receptacle (USB 2.0)", 20.32, 20.32,
            "Both D+ pins and both D- pins are tied, so the plug works either way round. SBU unused.\n"
            "5.1k Rd on each CC makes us a sink; the CC voltage tells the TERMPWR sheet the port's current.")
    JX, JY = 50.8, 88.9
    s.part("Connector:USB_C_Receptacle_USB2.0_16P", "J601", "USB-C (HRO TYPE-C-31-M-12)", JX, JY,
           {"A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS", "A5": "CC1", "B5": "CC2",
            "A6": None, "B6": None, "A7": None, "B7": None, "A8": "NC", "B8": "NC",
            "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": None},
           props=props("Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "", fit="Hand",
                       note="Owner's USB-C receptacle (HRO TYPE-C-31-M-12 footprint; LCSC C165948 for reference)"),
           fields=((JX - 7.62, JY - 25.4, "left"), (JX - 7.62, JY - 22.86, "left")), inline=True)
    px = JX + 15.24
    # D-: A7 (y-2.54) and B7 (y) tied; D+: A6 (y+2.54) and B6 (y+5.08) tied
    for ya, yb, xs, net in ((JY - 2.54, JY, px + 5.08, "USB_D-"), (JY + 2.54, JY + 5.08, px + 2.54, "USB_D+")):
        s.wire(px, ya, xs, ya)
        s.wire(px, yb, xs, yb)
        s.wire(xs, ya, xs, yb)
    s.wire(px + 5.08, JY - 2.54, px + 15.24, JY - 2.54)
    s.junction(px + 5.08, JY - 2.54)
    s.net_at("USB_D-", px + 15.24, JY - 2.54, 0)
    s.wire(px + 2.54, JY + 5.08, px + 15.24, JY + 5.08)
    s.junction(px + 2.54, JY + 5.08)
    s.net_at("USB_D+", px + 15.24, JY + 5.08, 0)
    for p_ in ("A7", "B7"):
        s.intended[("J601", p_)] = "USB_D-"
    for p_ in ("A6", "B6"):
        s.intended[("J601", p_)] = "USB_D+"
    # shell to GND through a 0R (can become an RC later if EMC wants the shield separated)
    s.wire(JX - 7.62, JY + 22.86, JX - 7.62, JY + 25.4)
    s.part("Device:R", "R603", "0R", JX - 7.62, JY + 29.21, {"1": None, "2": "GND"},
           props=props(R0402, "C17168", note="USB-C shell to GND (replace with 1M || 4.7nF if EMC asks)"),
           fields="left")
    s.intended[("J601", "S1")] = s.intended[("R603", "1")] = "~shell"
    for i, (ref, net) in enumerate((("R601", "CC1"), ("R602", "CC2"))):
        vpart("Device:R", ref, "5.1k", 101.6 + i * 15.24, 139.7, net, "GND",
              props(R0402, "C25905", note=f"{net} Rd (sink)"))
    s.note("Shell: 0R to GND (R603). Swap for 1M || 4.7 nF if EMC\ntesting wants the shield separated from GND.",
           20.32, 157.48)

    # ================= ESD =================
    s.rect(12.7, 180.34, 162.56, 284.48)
    heading(s, "ESD at the connector", 20.32, 187.96,
            "Clamp static from the cable or a finger to GND before it reaches the hub or the CC comparators.\n"
            "D+/D-: H5VUD5BB, 0.3 pF (fine at 480 Mbit/s). CC: H7VL10B, 7 V working (CC can sit near 5.5 V).\n"
            "VBUS: SMF6.0A, above VBUS's 5.5 V max. Place all five right at the receptacle.")
    ESD = [("D601", "USB_D+", "H5VUD5BB", "C20615820", "Diode_SMD:D_SOD-523", "D_TVS"),
           ("D602", "USB_D-", "H5VUD5BB", "C20615820", "Diode_SMD:D_SOD-523", "D_TVS"),
           ("D603", "CC1", "H7VL10B", "C20615787", "Diode_SMD:D_0402_1005Metric", "D_TVS"),
           ("D604", "CC2", "H7VL10B", "C20615787", "Diode_SMD:D_0402_1005Metric", "D_TVS"),
           ("D605", "VBUS", "SMF6.0A", "C19077499", "Diode_SMD:D_SOD-123F", "D_Zener")]
    for i, (ref, net, val, lcsc, fp, sym) in enumerate(ESD):
        x = 33.02 + i * 27.94
        vpart(f"Device:{sym}", ref, val, x, 238.76, net, "GND",
              props(fp, lcsc, note=f"ESD on {net}" + (" (DFN1006: check the 0402 footprint)" if "0402" in fp else "")),
              a=270)
    s.note("D603/D604 are DFN1006 (1.0 x 0.6 mm); the 0402 footprint is a stand-in to check.", 20.32, 269.24)

    # ================= hub =================
    s.rect(167.64, 12.7, 406.4, 284.48)
    heading(s, "USB 2.0 hub (CH334P)", 175.26, 20.32,
            "Upstream from the USB-C; port 1 -> FT232H (high speed, the scan data), port 2 -> RP2350 native USB\n"
            "(full speed: updates and console). The hub's transaction translators keep port 1 at full HS bandwidth.\n"
            "USB_D+/- and USB_FT_D+/- are 90R pairs (net class USB_HS); each segment <= ~15 mm.")
    UX, UY = 279.4, 110.49
    s.part("scsi-adapter:CH334P", "U601", "CH334P", UX, UY,
           {"12": "USB_D+", "11": "USB_D-", "13": None, "14": None, "2": "HUB_XI", "1": "HUB_XO",
            "10": "USB_FT_D+", "9": "USB_FT_D-", "8": "USB_RP_D+", "7": "USB_RP_D-",
            "6": "NC", "5": "NC", "4": "NC", "3": "NC", "15": None, "16": None, "17": "GND"},
           props=props("Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.75x1.75mm", "C5373042",
                       note="USB 2.0 HS 4-port hub, external 3.3 V mode"),
           fields=((UX + 2.54, UY - 16.51, "left"), (UX + 2.54, UY + 24.13, "left")))
    # V5 and VDD33 tied together onto +3V3 (external 3.3 V mode)
    top = UY - 15.24
    for dx in (-2.54, 2.54):
        s.wire(UX + dx, top, UX + dx, top - G)
    s.wire(UX - 2.54, top - G, UX, top - G)                  # two segments: the rail tees in at UX
    s.wire(UX, top - G, UX + 2.54, top - G)
    s.wire(UX, top - G, UX, top - 2 * G)
    s.junction(UX, top - G)
    s.power("+3V3", UX, top - 2 * G, 90)
    s.intended[("U601", "15")] = s.intended[("U601", "16")] = "+3V3"
    # PGANG: long stub so its label clears the reset diode and label on the row above
    s.wire(UX - 12.7, UY + 2.54, UX - 45.72, UY + 2.54)
    s.net_at("HUB_ACTIVE_INVERTED", UX - 45.72, UY + 2.54, 180)
    s.intended[("U601", "14")] = "HUB_ACTIVE_INVERTED"
    # RESET#: no pull-up; the expander can only pull it low, through a Schottky
    rx = UX - 12.7
    s.wire(rx, UY, rx - 2.54, UY)
    s.part("Device:D_Schottky", "D606", "1N5819WS", rx - 6.35, UY, {"1": "HUB_RESET_INVERTED", "2": None},
           props=props("Diode_SMD:D_SOD-323", "C191023", note="Anode at RESET#, cathode at expander P14"),
           fields=((rx - 6.35, UY - 5.08, ""), (rx - 6.35, UY - 2.54, "")))
    s.intended[("U601", "13")] = s.intended[("D606", "2")] = "~reset"
    s.note("RESET#: no external pull-up. The internal ~25k means 'run'; a pin\ndriven high at power-up would enable "
           "CDP charging and turn off\nhub sleep (WCH). The expander (P14) can only pull it low, via D606.",
           175.26, 146.05)
    s.note("PGANG ('power gang': on bigger CH334 packages it selects ganged port power and\n"
           "overcurrent control; our reading, WCH doesn't spell it out). Its internal pull-up keeps the\n"
           "default mode at reset; afterwards it outputs low while the hub is active, high in suspend.\n"
           "D607 is the 'hub active' LED on it (datasheet 3.3.5, Fig. 3-3-5 left).", 175.26, 162.56)
    s.part("Device:R", "R604", "470R", 363.22, 50.8, {"1": "+3V3", "2": None},
           props=props(R0402, "C25117", note="Hub active LED"), fields="left")
    s.wire(363.22, 54.61, 363.22, 59.69)
    s.part("Device:LED", "D607", "KT-0805G green", 363.22, 63.5, {"2": None, "1": "HUB_ACTIVE_INVERTED"}, a=90,
           props=props("LED_SMD:LED_0805_2012Metric", "C2297", note="Hub active (PGANG low)"),
           fields=((365.76, 62.23, "right"), (365.76, 64.77, "right")))
    s.intended[("R604", "2")] = s.intended[("D607", "2")] = "~hubled"
    s.note("Hub active: lit while the\nhub isn't suspended.", 368.3, 45.72)
    s.note("Ports 3 and 4 unused (built-in pull-downs; leave open).", UX + 20.32, UY - 11.43)
    # supply: external 3.3 V mode, V5 and VDD33 both on +3V3
    for i, (ref, val, lcsc, fp, note) in enumerate((("C601", "10uF 25V", "C15850", C0805, "Hub bulk"),
                                                    ("C602", "100nF", "C307331", C0402, "V5 decoupling"),
                                                    ("C603", "100nF", "C307331", C0402, "VDD33 decoupling"))):
        vpart("Device:C", ref, val, 330.2 + i * 17.78, 177.8, "+3V3", "GND", props(fp, lcsc, note=note))
    s.note("External 3.3 V mode: V5 and VDD33 both on +3V3 (its low-voltage\nreset can trip as high as 3.2 V, so no "
           "internal LDO). Known flaw: no\nVBUS sense, so on the bench supply with the host off, the 1.5k D+\n"
           "pull-up back-drives the host. Switch the bench off first.", 318.77, 196.85)
    # crystal: ABM8-272-T3, internal ~16 pF load caps; external pads left unfitted
    YX, YY = 218.44, 226.06
    s.net_at("HUB_XI", YX - 17.78, YY, 180)
    s.wire(YX - 17.78, YY, YX - 10.16, YY)
    s.wire(YX - 10.16, YY, YX - 3.81, YY)
    s.junction(YX - 10.16, YY)
    s.wire(YX - 10.16, YY, YX - 10.16, YY + 3.81)
    s.part("Device:Crystal_GND24", "Y601", "12MHz ABM8-272-T3", YX, YY, {"1": None, "3": None, "2": "GND", "4": "GND"},
           props=props("Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "C20625731", note="Same crystal as the RP2350's"),
           fields=((YX, YY - 5.08, ""), (YX, YY - 7.62, "")))
    s.wire(YX + 3.81, YY, YX + 10.16, YY)
    s.wire(YX + 10.16, YY, YX + 17.78, YY)
    s.junction(YX + 10.16, YY)
    s.wire(YX + 10.16, YY, YX + 10.16, YY + 3.81)
    s.net_at("HUB_XO", YX + 17.78, YY, 0)
    for ref, x in (("C604", YX - 10.16), ("C605", YX + 10.16)):
        s.part("Device:C", ref, "DNP", x, YY + 7.62, {"1": None, "2": "GND"},
               props=props(C0402, "", True, "Crystal load-cap pad, unfitted (CH334 has ~16 pF inside)"), dnp=True,
               fields="left" if x < YX else ((x + 2.54, YY + 6.35, "left"), (x + 2.54, YY + 8.89, "left")))
    for k in (("Y601", "1"), ("C604", "1")):
        s.intended[k] = "HUB_XI"
    for k in (("Y601", "3"), ("C605", "1")):
        s.intended[k] = "HUB_XO"
    s.note("C604/C605 DNP: the CH334 has ~16 pF on each pin (datasheet\nV2.91 6.1), which suits the ABM8's CL 10 pF. Fit "
           "only if the\noscillator is off-frequency or slow to start.", 175.26, 246.38)

    s.write(path)
    return s.intended
