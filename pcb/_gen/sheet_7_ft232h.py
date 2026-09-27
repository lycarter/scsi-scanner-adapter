"""FT232H: pcb/7-ft232h.kicad_sch.

Sources: FTDI DS_FT232H v2.0 (Table 3.13 FT1248 pins, Fig. 6.2 power, Table 3.3 EEPROM), NOTES "FT232H pins in
detail", "FT232H package and crystal", blocks/4-usb.md, parts-list.md §4; Microchip 93LC56B (SOT-23 pinout p. 2).
"""
from schgen import Sheet, G

FILE = "7-ft232h.kicad_sch"
FILE_UUID = "3a9de44d-f34a-475f-93d3-509c397aace8"
ROOT = "2c5b21a9-7d0d-4304-8bd9-0602cba3b7b5"
SHEET_SYM = "ecb82d7b-30c9-4e3c-9876-96abfe1bc821"          # the "ft232h" sheet symbol on the root

R0402, C0402 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric"
V3 = "FT232H_3V3"


def props(fp, lcsc, dnp=False, note="", fit="JLC", ds=""):
    return {"Footprint": fp, "Datasheet": ds, "Description": note, "LCSC": lcsc, "Fit": "DNP" if dnp else fit}


def heading(s, t, x, y, body=""):
    s.text(t, x, y, 2.0, bold=True)
    if body:
        s.text(body, x, y + 4.5, 1.27)


def build(path):
    s = Sheet(FILE_UUID, "A3", "SCSI scanner adapter", f"/{ROOT}/{SHEET_SYM}", seed=FILE)
    s.refbase = 700
    s.rails = {"+5V_SYS", V3}
    s.hier = {"FT232H_MIOSIO0": "bidirectional", "FT232H_MIOSIO1": "bidirectional", "FT232H_MIOSIO2": "bidirectional",
              "FT232H_MIOSIO3": "bidirectional", "FT232H_D4": "bidirectional", "FT232H_D5": "bidirectional",
              "FT232H_D6": "bidirectional", "FT232H_D7": "bidirectional", "FT232H_WRITE_INVERTED": "bidirectional",
              "FT232H_SCLK": "input", "FT232H_SS_N": "input", "FT232H_MISO": "output",
              "FT232H_RESET_INVERTED": "input", "USB_FT_D+": "bidirectional", "USB_FT_D-": "bidirectional"}

    def vpart(lib, ref, val, x, y, top, bot, pr, dnp=False):
        s.part(lib, ref, val, x, y, {"1": top, "2": bot}, props=pr, dnp=dnp, fields="left")

    # ================= FT232H =================
    s.rect(12.7, 12.7, 241.3, 177.8)
    heading(s, "FT232H (USB 2.0 high speed <-> FT1248)", 20.32, 20.32,
            "FT1248 4-bit to the RP2350 (MIOSIO0-3, SCLK, SS_N, MISO; 33R series at the RP2350 end). The EEPROM selects\n"
            "FT1248 mode: without it the chip starts in UART mode. D4-D7 and WR# only reach the RP2350 through the\n"
            "unfitted rework links (245-FIFO fallback). SCLK/SS_N/MISO sit on the FIFO's RXF#/TXE#/RD# pins.")
    UX, UY = 137.16, 104.14
    nets = {"40": None, "39": None, "38": "FT232H_VCORE", "37": "FT232H_VCCA", "6": "USB_FT_D-", "7": "USB_FT_D+",
            "34": "FT232H_RESET_INVERTED", "5": "FT232H_REF", "45": "FT232H_EECS", "44": "FT232H_EECLK",
            "43": "FT232H_EEDATA", "1": "FT232H_XCSI", "2": "FT232H_XCSO", "42": "GND",
            "13": "FT232H_MIOSIO0", "14": "FT232H_MIOSIO1", "15": "FT232H_MIOSIO2", "16": "FT232H_MIOSIO3",
            "17": "FT232H_D4", "18": "FT232H_D5", "19": "FT232H_D6", "20": "FT232H_D7",
            "21": "FT232H_SCLK", "25": "FT232H_SS_N", "26": "FT232H_MISO", "27": "FT232H_WRITE_INVERTED",
            "28": "FT232H_SIWU_N", "29": "NC", "30": "NC", "31": "NC", "32": "NC", "33": "NC"}
    for n in ("3", "8", "12", "24", "46", "4", "9", "41", "10", "11", "22", "23", "35", "36", "47", "48"):
        nets[n] = None                                    # top and bottom pins wired by hand
    s.part("scsi-adapter:FT232H", "U701", "FT232HL", UX, UY, nets,
           props=props("Package_QFP:LQFP-48_7x7mm_P0.5mm", "C51997", note="FT232HL-REEL (LQFP-48)",
                       ds="https://ftdichip.com/wp-content/uploads/2020/07/DS_FT232H.pdf"),
           fields=((UX + 20.32, UY - 40.64, "left"), (UX + 20.32, UY + 43.18, "left")), inline=True)
    top, bot = UY - 38.1, UY + 38.1
    # VREGIN and VCCD: short doglegs up to their power symbols, staggered so neither
    # symbol sits on top of the pin numbers
    pins = s._lib("scsi-adapter:FT232H")[1]
    for n, net, run, rise in (("40", "+5V_SYS", 5.08, 5.08), ("39", V3, 15.24, 15.24)):
        px, py, _ = s.pin_pos(pins, n, UX, UY, 0)
        s.wire(px, py, px - run, py)
        s.wire(px - run, py, px - run, py - rise)
        s.power(net, px - run, py - rise, 90)
        s.intended[("U701", n)] = net
    # VPHY and VPLL: own labels, staggered so their text clears
    s.wire(UX - 5.08, top, UX - 5.08, top - 5.08)
    s.net_at("FT232H_VPHY", UX - 5.08, top - 5.08, 180)
    s.wire(UX - 2.54, top, UX - 2.54, top - 10.16)
    s.net_at("FT232H_VPLL", UX - 2.54, top - 10.16, 180)
    s.intended[("U701", "3")], s.intended[("U701", "8")] = "FT232H_VPHY", "FT232H_VPLL"
    # VCCIO x3 onto FT232H_3V3
    xs = [UX, UX + 2.54, UX + 5.08]
    for x in xs:
        s.wire(x, top, x, top - 5.08)
    s.wire(UX, top - 5.08, UX + 2.54, top - 5.08)
    s.wire(UX + 2.54, top - 5.08, UX + 5.08, top - 5.08)
    s.junction(UX + 2.54, top - 5.08)
    s.wire(UX + 5.08, top - 5.08, UX + 5.08, top - 7.62)
    s.junction(UX + 5.08, top - 5.08)
    s.power(V3, UX + 5.08, top - 7.62, 90)
    for n in ("12", "24", "46"):
        s.intended[("U701", n)] = V3
    # ground pins onto one bus
    gx = [UX - 10.16, UX - 7.62, UX - 5.08, UX - 2.54, UX, UX + 2.54, UX + 5.08, UX + 7.62, UX + 10.16,
          UX + 12.7, UX + 15.24]
    for x in gx:
        s.wire(x, bot, x, bot + G)
    for a, b in zip(gx, gx[1:]):
        s.wire(a, bot + G, b, bot + G)
    for x in gx[1:-1]:
        s.junction(x, bot + G)
    s.wire(UX, bot + G, UX, bot + 2 * G)
    s.power("GND", UX, bot + 2 * G, 270)
    for n in ("4", "9", "41", "10", "11", "22", "23", "35", "36", "47", "48"):
        s.intended[("U701", n)] = "GND"
    s.note("ACBUS5/6/8/9: free (CBUS bit-bang possible later). ACBUS7 = PWRSAV#: leave\nopen, with 'Suspend on "
           "ACBus7 Low' OFF in the EEPROM. TEST (42) to GND.", UX + 27.94, UY + 25.4)

    # ================= power =================
    s.rect(246.38, 12.7, 406.4, 157.48)
    heading(s, "Power (DS Fig. 6.2, exactly)", 254.0, 20.32,
            "VREGIN from +5V_SYS. VCCD is then an OUTPUT: the chip's own 3.3 V\n"
            "(FT232H_3V3), feeding VCCIO x3, VPHY and VPLL (through 600R ferrites)\n"
            "and the EEPROM. Never connect FT232H_3V3 to the board's +3V3.")
    caps = [("C701", "4.7uF 10V", "C23733", "+5V_SYS", "VREGIN"), ("C702", "100nF", "C307331", "+5V_SYS", "VREGIN"),
            ("C703", "4.7uF 10V", "C23733", V3, "VCCD (output)"), ("C704", "100nF", "C307331", V3, "VCCD"),
            ("C705", "100nF", "C307331", V3, "VCCIO pin 12"), ("C706", "100nF", "C307331", V3, "VCCIO pin 24"),
            ("C707", "100nF", "C307331", V3, "VCCIO pin 46"),
            ("C712", "100nF", "C307331", "FT232H_VCCA", "VCCA (output; don't load)"),
            ("C713", "100nF", "C307331", "FT232H_VCORE", "VCORE (output; don't load)")]
    for i, (ref, val, lcsc, net, note) in enumerate(caps):
        x = 261.62 + i * 15.24
        vpart("Device:C", ref, val, x, 58.42, net, "GND", props(C0402 if "4.7" not in val else C0402, lcsc, note=note))
    for k, (fb, pin, c1, c2) in enumerate((("FB701", "FT232H_VPHY", "C708", "C709"),
                                           ("FB702", "FT232H_VPLL", "C710", "C711"))):
        y = 96.52 + k * 30.48
        s.part("Device:FerriteBead_Small", fb, "600R@100MHz", 269.24, y, {"1": V3, "2": pin}, a=90,
               props=props("Inductor_SMD:L_0603_1608Metric", "C1002", note="Sunlord GZ1608D601TF"),
               fields=((269.24, y - 3.81, ""), (269.24, y + 3.81, "")))
        vpart("Device:C", c1, "100nF", 302.26, y + 5.08, pin, "GND", props(C0402, "C307331", note=pin))
        vpart("Device:C", c2, "4.7uF", 317.5, y + 5.08, pin, "GND",
              props(C0402, "C23733", True, f"{pin} bulk pad, DNP"), dnp=True)
    for i, (flg, net) in enumerate((("#FLG702", "FT232H_VPHY"), ("#FLG703", "FT232H_VPLL"))):
        s.pwr_flag(flg, net, 345.44 + i * 17.78, 93.98)
    s.part("Connector:TestPoint", "TP701", "FT232H_3V3", 345.44, 127.0, {"1": V3},
           props=props("TestPoint:TestPoint_Pad_D1.5mm", "", fit="None", note="Test pad: FT232H_3V3"),
           fields=((346.71, 121.92, "left"), (346.71, 124.46, "left")))
    s.note("PWR_FLAGs: VPHY and VPLL are fed through ferrites (passive to ERC).\n"
           "U701 is a project copy of KiCad's FT232H with VCCD, EECS, EECLK typed\nas outputs.\nC709/C711 DNP: 4.7 uF pads per FTDI, fit if the PHY/PLL rails\nneed more bulk.", 254.0, 147.32)

    # ================= EEPROM =================
    s.rect(246.38, 162.56, 406.4, 246.38)
    heading(s, "Configuration EEPROM (93LC56B, required)", 254.0, 170.18,
            "Holds FT1248 mode. Programmed over USB after assembly (USAGE.md). The 93LC46B won't work.")
    EX, EY = 294.64, 210.82
    s.part("Memory_EEPROM:93LCxxBxxOT", "U702", "93LC56BT-I/OT", EX, EY,
           {"5": "FT232H_EECS", "4": "FT232H_EECLK", "3": "FT232H_EEDATA", "1": "FT232H_EEPROM_DO", "6": V3, "2": "GND"},
           props=props("Package_TO_SOT_SMD:SOT-23-6", "C190271", note="Microchip 93LC56B, SOT-23-6 (OT)"),
           fields=((EX + 2.54, EY - 10.16, "left"), (EX + 2.54, EY + 10.16, "left")))
    vpart("Device:R", "R703", "10k", 342.9, 210.82, V3, "FT232H_EEPROM_DO", props(R0402, "C25744", note="EEPROM DO pull-up"))
    vpart("Device:R", "R704", "2.2k", 365.76, 210.82, "FT232H_EEPROM_DO", "FT232H_EEDATA",
          props(R0402, "C25879", note="EEPROM DO -> DI (DS Table 3.3)"))
    vpart("Device:C", "C714", "100nF", 396.24, 210.82, V3, "GND", props(C0402, "C307331", note="EEPROM decoupling"))
    s.note("EEDATA drives DI directly and reads DO through R704 (DS Table 3.3; the figure shows 2k).", 254.0, 236.22)

    # ================= support parts =================
    s.rect(12.7, 182.88, 241.3, 284.48)
    heading(s, "Support parts", 20.32, 190.5,
            "12 MHz crystal (same ABM8 as the RP2350 and hub) with 2 x 15 pF; REF 12k 1 % (DS Table 3.2);\n"
            "RESET# 10k + 10 nF (the expander's P13 can also pull it low); WR#/SIWU# pull-ups for the FIFO fallback.")
    YX, YY = 50.8, 223.52
    s.net_at("FT232H_XCSI", YX - 15.24, YY, 180)
    s.wire(YX - 15.24, YY, YX - 8.89, YY)
    s.wire(YX - 8.89, YY, YX - 3.81, YY)
    s.junction(YX - 8.89, YY)
    s.wire(YX - 8.89, YY, YX - 8.89, YY + 3.81)
    s.part("Device:Crystal_GND24", "Y701", "12MHz ABM8-272-T3", YX, YY, {"1": None, "3": None, "2": "GND", "4": "GND"},
           props=props("Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "C20625731", note="Abracon ABM8-272-T3"),
           fields=((YX, YY - 5.08, ""), (YX, YY - 7.62, "")))
    s.wire(YX + 3.81, YY, YX + 8.89, YY)
    s.wire(YX + 8.89, YY, YX + 15.24, YY)
    s.junction(YX + 8.89, YY)
    s.wire(YX + 8.89, YY, YX + 8.89, YY + 3.81)
    s.net_at("FT232H_XCSO", YX + 15.24, YY, 0)
    for ref, x in (("C715", YX - 8.89), ("C716", YX + 8.89)):
        s.part("Device:C", ref, "15pF", x, YY + 7.62, {"1": None, "2": "GND"},
               props=props(C0402, "C1548", note="Crystal load cap"),
               fields="left" if x < YX else ((x + 2.54, YY + 6.35, "left"), (x + 2.54, YY + 8.89, "left")))
    for k in (("Y701", "1"), ("C715", "1")):
        s.intended[k] = "FT232H_XCSI"
    for k in (("Y701", "3"), ("C716", "1")):
        s.intended[k] = "FT232H_XCSO"
    vpart("Device:R", "R701", "12k 1%", 99.06, 226.06, "FT232H_REF", "GND", props(R0402, "C25752", note="REF (DS Table 3.2)"))
    vpart("Device:R", "R702", "10k", 124.46, 220.98, V3, "FT232H_RESET_INVERTED", props(R0402, "C25744", note="RESET# pull-up"))
    vpart("Device:C", "C717", "10nF", 124.46, 246.38, "FT232H_RESET_INVERTED", "GND",
          props(C0402, "C15195", note="RESET# delay"))
    vpart("Device:R", "R705", "10k", 165.1, 226.06, V3, "FT232H_WRITE_INVERTED", props(R0402, "C25744", note="WR# pull-up (FIFO fallback)"))
    vpart("Device:R", "R706", "10k", 205.74, 226.06, V3, "FT232H_SIWU_N",
          props(R0402, "C25744", note="SIWU# pull-up: tied high, the latency timer flushes short packets"))
    s.note("WR# (27) and SIWU# (28) are pulled up so the 245-FIFO\nfallback never floats them; harmless in FT1248 mode.",
           147.32, 256.54)

    s.write(path)
    return s.intended
