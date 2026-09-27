"""RP2350B and support: pcb/4-rp2350.kicad_sch.

Sources: blocks/5-rp2350-pinout.md (accepted pin map); NOTES "MCU support parts", "PSRAM", "Debug",
"Resistor and small-part values"; parts-list.md §3; Raspberry Pi "Hardware design with RP2350" (guide)
Appendix B and RP2350 datasheet 6.3.8 (core regulator).
"""
from schgen import Sheet, G

FILE = "4-rp2350.kicad_sch"
FILE_UUID = "279a1e8a-96c0-4411-8473-88cc72d09462"
ROOT = "2c5b21a9-7d0d-4304-8bd9-0602cba3b7b5"
SHEET_SYM = "09e6debe-d957-4263-8f90-e8efff15a584"          # the "rp2350" sheet symbol on the root

LINES = ["DB0", "DB1", "DB2", "DB3", "DB4", "DB5", "DB6", "DB7", "DBP", "ATN", "BSY", "ACK", "RST", "MSG",
         "SEL", "CD", "REQ", "IO"]                               # GPIO 0-17 = receiver outputs
GATES = ["DB0", "DB1", "DB2", "DB3", "DB4", "DB5", "DB6", "DB7", "DBP", "ATN", "BSY", "ACK", "RST", "SEL"]
FT1248 = {32: "FT232H_MIOSIO0", 33: "FT232H_MIOSIO1", 34: "FT232H_MIOSIO2", 35: "FT232H_MIOSIO3", 41: "FT232H_SCLK",
          42: "FT232H_SS_N", 43: "FT232H_MISO"}
REWORK = {36: ("I2C_SDA", "FT232H_D4", 17), 37: ("I2C_SCL", "FT232H_D5", 18), 38: ("SD_CLK", "FT232H_D6", 19),
          39: ("SD_CMD", "FT232H_D7", 20), 40: ("SD_D0", "FT232H_WR_N", 27)}   # GPIO: (fitted, DNP, FT232H pin)
MARKERS = {44: "LOGIC_ANALYZER_MARKER0", 45: "LOGIC_ANALYZER_MARKER1"}

R0402, R0603, C0402, C0805 = ("Resistor_SMD:R_0402_1005Metric", "Resistor_SMD:R_0603_1608Metric",
                              "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0805_2012Metric")


def props(fp, lcsc, dnp=False, note="", fit="JLC", ds=""):
    return {"Footprint": fp, "Datasheet": ds, "Description": note, "LCSC": lcsc, "Fit": "DNP" if dnp else fit}


def heading(s, t, x, y, body=""):
    s.text(t, x, y, 2.0, bold=True)
    if body:
        s.text(body, x, y + 4.5, 1.27)


def gpio_net(n):
    if n < 18:
        return LINES[n] + "_RX"
    if n < 32:
        return GATES[n - 18] + "_GATE"
    if n == 46:
        return "TERMPWR_SENSE"
    if n == 47:
        return "PSRAM_CE_INVERTED"
    return f"GPIO{n}"


def build(path):
    s = Sheet(FILE_UUID, "A2", "SCSI scanner adapter", f"/{ROOT}/{SHEET_SYM}", seed=FILE)
    s.refbase = 400
    s.rails = {"+3V3", "TERMPWR"}
    s.hier = {n + "_RX": "input" for n in LINES}
    s.hier.update({n + "_GATE": "output" for n in GATES})
    s.hier.update({v: ("bidirectional" if "MIOSIO" in v else ("input" if v == "FT232H_MISO" else "output"))
                   for v in FT1248.values()})
    s.hier.update({"FT232H_D4": "bidirectional", "FT232H_D5": "bidirectional", "FT232H_D6": "bidirectional",
                   "FT232H_D7": "bidirectional", "FT232H_WR_N": "bidirectional", "I2C_SDA": "bidirectional",
                   "I2C_SCL": "output", "SD_CLK": "output", "SD_CMD": "bidirectional", "SD_D0": "bidirectional",
                   "USB_RP_D+": "bidirectional", "USB_RP_D-": "bidirectional"})
    s.hier.update({v: "output" for v in MARKERS.values()})

    def chain(x, y0, elems, top, bottom, taps=None, step=12.7):
        """Vertical series chain; elems: (ref, lib, value, props, a, top_pin, bot_pin, half, dnp)."""
        taps = taps or {}
        for i, (ref, lib, val, pr, a, tp, bp, half, dnp) in enumerate(elems):
            y = y0 + i * step
            s.part(lib, ref, val, x, y, {tp: top if i == 0 else None, bp: bottom if i == len(elems) - 1 else None},
                   a=a, props=pr, dnp=dnp,
                   fields="left" if a == 0 else ((x + 2.54, y - 1.27, "right"), (x + 2.54, y + 1.27, "right")))
            if i == len(elems) - 1:
                break
            nref, _, _, _, _, ntp, _, nhalf, _ = elems[i + 1]
            ya, yb = y + half, y + step - nhalf
            tap = taps.get(i)
            net = tap if tap else f"~{ref}-{nref}"
            if tap:
                ty = (ya + yb) / 2
                s.wire(x, ya, x, ty)
                s.wire(x, ty, x, yb)
                s.junction(x, ty)
                s.wire(x, ty, x + G, ty)
                s.net_at(tap, x + G, ty, 0)
            else:
                s.wire(x, ya, x, yb)
            s.intended[(ref, bp)] = net
            s.intended[(nref, ntp)] = net

    def series(x, y, pin_net, out_net, ref, val, lcsc, note, fp=R0402, dnp=False):
        """Horizontal series part: label pin_net -> R -> out_net (hier or label)."""
        s.part("Device:R", ref, val, x, y, {"1": pin_net, "2": out_net}, a=90,
               props=props(fp, lcsc, dnp, note), dnp=dnp, fields=((x, y - 2.54, ""), (x, y + 2.54, "")), stub=G)

    # ================= RP2350B =================
    s.rect(160.02, 12.7, 345.44, 406.4)
    heading(s, "RP2350B", 167.64, 20.32,
            "Pin map: blocks/5-rp2350-pinout.md. GPIO 0-17 = receiver outputs (PIO0 in, read inverted),\n"
            "GPIO 18-31 = driver gates (1 = asserted). The only ground is the exposed pad (pin 81).\n"
            "Series resistors sit at the pins: 33R on the 7 FT1248 nets (damps ringing at 25 MHz, limits\n"
            "contention), 100R on the logic-analyzer markers, 27R 0603 on native USB (close to the chip).")
    MX, MY = 252.73, 158.75
    nets = {}
    import re
    emb, _ = s._lib("MCU_RaspberryPi:RP2350B")
    names = {num: nm for nm, num in re.findall(r'\(name "([^"]*)"[\s\S]*?\(number "([^"]*)"', emb)}
    for num, nm in names.items():
        m = re.match(r"GPIO(\d+)", nm)
        if m:
            nets[num] = gpio_net(int(m.group(1)))
    nets.update({"35": "RUN", "66": "RP2350_USB_D-", "67": "RP2350_USB_D+", "75": "QSPI_SS_INVERTED",
                 "71": "QSPI_SCLK", "72": "QSPI_SD0", "74": "QSPI_SD1", "73": "QSPI_SD2", "70": "QSPI_SD3",
                 "30": "XIN", "31": "XOUT", "33": "SWCLK", "34": "SWDIO"})
    SERIES = {"40": ("FT232H_MIOSIO0", "R407"), "42": ("FT232H_MIOSIO1", "R408"), "43": ("FT232H_MIOSIO2", "R409"),
              "44": ("FT232H_MIOSIO3", "R410"), "52": ("FT232H_SCLK", "R411"), "53": ("FT232H_SS_N", "R412"),
              "54": ("FT232H_MISO", "R413"), "55": ("LOGIC_ANALYZER_MARKER0", "R414"),
              "56": ("LOGIC_ANALYZER_MARKER1", "R415"), "67": ("USB_RP_D+", "R416"), "66": ("USB_RP_D-", "R417")}
    for num in SERIES:
        nets[num] = None
    # top and bottom pins are wired by hand below
    for num in ("61", "68", "59", "69", "50", "60", "76", "15", "24", "29", "41", "5", "64", "63", "65", "10",
                "51", "32", "62", "81"):
        nets[num] = None
    s.part("MCU_RaspberryPi:RP2350B", "U401", "RP2350B", MX, MY, nets,
           props=props("Package_DFN_QFN:QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm", "C42415655",
                       note="Plan for A4 silicon", ds="https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf"),
           fields=((MX - 25.4, MY - 67.31, "left"), (MX + 27.94, MY + 60.96, "left")))
    # inline series resistors, staggered in two columns so each keeps its reference readable
    _, upins = s._lib("MCU_RaspberryPi:RP2350B")
    VAL = {"FT": ("33R", "C25105", R0402, "FT1248 series R"), "LO": ("100R", "C25076", R0402,
           "Logic-analyzer marker series R"), "US": ("27R", "C25190", R0603, "Native USB series R")}
    rows = sorted(((s.pin_pos(upins, n, MX, MY, 0), n) for n in SERIES), key=lambda t: (t[0][2], t[0][1]))
    col = {}
    for (px, py, d), n in rows:                               # alternate columns down each run of pins
        prev = [k for k in col if k[0] == d and abs(k[1] - (py - G)) < 0.01]
        col[(d, py)] = 1 - col[prev[0]] if prev else 1         # start outside the neighbouring labels
        out, ref = SERIES[n]
        val, lcsc, fp, note = VAL[out[:2]]
        sg = 1 if d == 0 else -1
        c = col[(d, py)]
        near = px + sg * (5.08 + c * 12.7)
        xc = near + sg * 3.81
        far = near + sg * 7.62
        xe = px + sg * 30.48
        s.wire(px, py, near, py)
        s.part("Device:R", ref, val, xc, py, {"1": None, "2": None}, a=90, props=props(fp, lcsc, note=note),
               fields=((xc, py - 1.65, ""), (xc, py + 1.65, "")), hide_value=True, fsize=0.9)
        s.wire(far, py, xe, py)
        s.net_at(out, xe, py, d)
        pn, pf = ("1", "2") if sg > 0 else ("2", "1")
        s.intended[("U401", n)] = s.intended[(ref, pn)] = f"~pin{n}"
        s.intended[(ref, pf)] = out
    # what the rework-link GPIOs do (their links are in the rework box)
    for n, txt in (("45", "I2C0 SDA (rework: FT232H_D4)"), ("46", "I2C0 SCL (rework: FT232H_D5)"),
                   ("47", "microSD CLK (rework: FT232H_D6)"), ("48", "microSD CMD (rework: FT232H_D7)")):
        px, py, d = s.pin_pos(upins, n, MX, MY, 0)
        s.note(txt, px + 12.7, py - 0.635)
    px, py, d = s.pin_pos(upins, "49", MX, MY, 0)
    s.note("microSD D0 (rework: FT232H_WR_N)", px - 58.42, py - 0.635)

    top = MY - 55.88                                          # top pin ends
    Y1 = top - 5.08
    rail3 = [-12.7, -10.16, -5.08, -2.54, 2.54]               # USB_OTP, ADC_AVDD, QSPI_IOVDD, IOVDD, VREG_VIN
    for dx in rail3:
        s.wire(MX + dx, top, MX + dx, Y1)
    for a, b in zip(rail3, rail3[1:]):
        s.wire(MX + a, Y1, MX + b, Y1)
    for dx in rail3[1:-1]:
        s.junction(MX + dx, Y1)
    s.wire(MX - 12.7, Y1, MX - 12.7, Y1 - G)
    s.junction(MX - 12.7, Y1)
    s.power("+3V3", MX - 12.7, Y1 - G, 90)
    for num in ("68", "59", "69", "50", "60", "76", "15", "24", "29", "41", "5", "64"):
        s.intended[("U401", num)] = "+3V3"
    s.wire(MX - 17.78, top, MX - 17.78, top - 7.62)           # VREG_AVDD
    s.net_at("VREG_AVDD", MX - 17.78, top - 7.62, 180)
    s.intended[("U401", "61")] = "VREG_AVDD"
    s.wire(MX + 5.08, top, MX + 5.08, top - 12.7)            # VREG_LX
    s.net_at("VREG_LX", MX + 5.08, top - 12.7, 0)
    s.intended[("U401", "63")] = "VREG_LX"
    for dx in (7.62, 12.7):                                   # VREG_FB and DVDD tied: the 1.1 V core rail
        s.wire(MX + dx, top, MX + dx, Y1)
    s.wire(MX + 7.62, Y1, MX + 12.7, Y1)
    s.wire(MX + 12.7, Y1, MX + 20.32, Y1)
    s.junction(MX + 12.7, Y1)
    s.net_at("DVDD_1V1", MX + 20.32, Y1, 0)
    for num in ("65", "10", "51", "32"):
        s.intended[("U401", num)] = "DVDD_1V1"
    bot = MY + 58.42                                          # VREG_PGND and EP to GND
    s.wire(MX - 2.54, bot, MX - 2.54, bot + G)
    s.wire(MX, bot, MX, bot + G)
    s.wire(MX - 2.54, bot + G, MX, bot + G)
    s.power("GND", MX, bot + G, 270)
    s.intended[("U401", "62")] = s.intended[("U401", "81")] = "GND"
    s.note("Top pins: USB_OTP_VDD, ADC_AVDD, QSPI_IOVDD, IOVDD (x8) and\nVREG_VIN share +3V3; VREG_FB and DVDD (x3) "
           "are the 1.1 V core\nrail (DVDD_1V1), made by the on-chip regulator. Each supply\npin gets its own 100 nF "
           "(Decoupling box).", 167.64, 43.18)

    # ================= Core regulator =================
    s.rect(12.7, 12.7, 154.94, 104.14)
    heading(s, "Core regulator (on-chip, 1.1 V)", 20.32, 20.32,
            "Guide 2.1 / datasheet 6.3.8. Layout: inductor orientation per Fig. 23, VREG_PGND and CIN\n"
            "straight to the exposed pad, and a ground cut-out under VREG_LX on layer 2 (Fig. 24).")
    s.part("Device:L", "L401", "3.3uH", 60.96, 50.8, {"1": "VREG_LX", "2": "DVDD_1V1"}, a=90,
           props=props("", "C42411119",
                       note="Abracon AOTA-B201610S3R3-101-T, polarity-marked (datasheet requires it). 2016 footprint with polarity mark to do."),
           fields=((60.96, 46.99, ""), (60.96, 54.61, "")))
    s.note("Polarity dot per datasheet Fig. 23;\ncheck JLC's placement preview.", 43.18, 58.42)
    s.pwr_flag("#FLG401", "DVDD_1V1", 81.28, 38.1)
    s.pwr_flag("#FLG402", "VREG_AVDD", 124.46, 38.1)
    s.note("PWR_FLAGs: DVDD_1V1 is fed through L401 and VREG_AVDD\nthrough R401, which ERC sees as passive parts.",
           86.36, 71.12)
    chain(99.06, 45.72, [("R401", "Device:R", "33R", props(R0402, "C25105", note="VREG_AVDD filter"),
                          0, "1", "2", 3.81, False),
                         ("C401", "Device:C", "4.7uF 10V", props(C0402, "C23733", note="VREG_AVDD filter"),
                          0, "1", "2", 3.81, False)],
          "+3V3", "GND", taps={0: "VREG_AVDD"})
    for i, (ref, net, note) in enumerate((("C402", "+3V3", "CIN at VREG_VIN (pin 64)"),
                                          ("C403", "DVDD_1V1", "COUT at VREG_FB/DVDD"),
                                          ("C404", "DVDD_1V1", "Second DVDD cap at pin 32 (bottom edge, away from LX)"))):
        x = 25.4 + i * 20.32
        s.part("Device:C", ref, "4.7uF 10V", x, 88.9, {"1": net, "2": "GND"},
               props=props(C0402, "C23733", note=note), fields="left")
    s.part("Device:C", "C405", "10uF 25V", 124.46, 88.9, {"1": "+3V3", "2": "GND"},
           props=props(C0805, "C15850", note="3.3 V bulk near the MCU"), fields="left")
    s.note("C402 CIN, C403 COUT, C404 2nd DVDD (all 4.7 uF 0402;\nfallback 0603 C19666 for CIN if DC bias bites).",
           76.2, 81.28)

    # ================= Decoupling =================
    s.rect(12.7, 109.22, 154.94, 190.5)
    heading(s, "Decoupling (100 nF per supply pin, at the pin)", 20.32, 116.84)
    DEC = [("IOVDD 5", "+3V3"), ("IOVDD 15", "+3V3"), ("IOVDD 24", "+3V3"), ("IOVDD 29", "+3V3"),
           ("IOVDD 41", "+3V3"), ("IOVDD 50", "+3V3"), ("IOVDD 60", "+3V3"), ("IOVDD 76", "+3V3"),
           ("DVDD 10", "DVDD_1V1"), ("DVDD 32", "DVDD_1V1"), ("DVDD 51", "DVDD_1V1"),
           ("ADC_AVDD 59", "+3V3"), ("USB_OTP 68 + QSPI 69", "+3V3")]
    for i, (pin, net) in enumerate(DEC):
        col, row = i % 7, i // 7
        x, y = 22.86 + col * 19.05, 143.51 + row * 30.48
        s.part("Device:C", f"C{406 + i}", "100nF", x, y, {"1": net, "2": "GND"},
               props=props(C0402, "C307331", note=f"Decoupling, {pin}"), fields="left")
        s.note(pin.replace(" + ", "+\n"), x + 2.54, y - 1.27)

    # ================= Crystal =================
    s.rect(350.52, 12.7, 584.2, 76.2)
    heading(s, "Crystal (12 MHz)", 358.14, 20.32,
            "ABM8-272-T3 (CL 10 pF, ESR <= 50 R): 2 x 15 pF (7.5 pF + ~3 pF stray), 1k series on XOUT stops overdrive.")
    YX, YY = 431.8, 50.8
    s.part("Device:Crystal_GND24", "Y401", "12MHz ABM8-272-T3", YX, YY, {"1": None, "3": None, "2": "GND", "4": "GND"},
           props=props("Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "C20625731", note="Abracon ABM8-272-T3"),
           fields=((YX, YY - 5.08, ""), (YX, YY - 7.62, "")))
    s.net_at("XIN", 406.4, YY, 180)
    s.wire(406.4, YY, 416.56, YY)
    s.wire(416.56, YY, YX - 3.81, YY)
    s.junction(416.56, YY)
    s.wire(416.56, YY, 416.56, YY + 3.81)
    s.part("Device:C", "C419", "15pF", 416.56, YY + 7.62, {"1": None, "2": "GND"},
           props=props(C0402, "C1548", note="Crystal load cap"), fields="left")
    s.wire(YX + 3.81, YY, 447.04, YY)
    s.wire(447.04, YY, 452.12, YY)
    s.junction(447.04, YY)
    s.wire(447.04, YY, 447.04, YY + 3.81)
    s.part("Device:C", "C420", "15pF", 447.04, YY + 7.62, {"1": None, "2": "GND"},
           props=props(C0402, "C1548", note="Crystal load cap"),
           fields=((449.58, YY + 6.35, "left"), (449.58, YY + 8.89, "left")))
    s.part("Device:R", "R402", "1k", 455.93, YY, {"1": None, "2": "XOUT"}, a=90,
           props=props(R0402, "C11702", note="XOUT series R (guide 4)"), fields=((455.93, YY - 2.54, ""), (455.93, YY + 2.54, "")))
    s.wire(452.12, YY, 455.93 - 3.81, YY)
    for k in (("Y401", "1"), ("C419", "1")):
        s.intended[k] = "XIN"
    for k in (("Y401", "3"), ("C420", "1"), ("R402", "1")):
        s.intended[k] = "~xtal_out"

    # ================= QSPI flash and PSRAM =================
    s.rect(350.52, 81.28, 462.28, 175.26)
    heading(s, "QSPI flash", 358.14, 88.9,
            "W25Q128JVSIQ, 16 MB, on the dedicated\nchip select (QSPI_SS). Boot + firmware.")
    FX, FY = 381.0, 134.62
    s.part("Memory_Flash:W25Q128JVS", "U402", "W25Q128JVSIQ", FX, FY,
           {"1": "QSPI_SS_INVERTED", "6": "QSPI_SCLK", "5": "QSPI_SD0", "2": "QSPI_SD1", "3": "QSPI_SD2",
            "7": "QSPI_SD3", "8": "+3V3", "4": "GND"},
           props=props("Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", "C97521", note="16 MB QSPI flash (guide 3.1)"),
           fields=((FX + 2.54, FY - 15.24, "left"), (FX + 2.54, FY + 15.24, "left")))
    s.part("Device:C", "C421", "100nF", 403.86, 134.62, {"1": "+3V3", "2": "GND"},
           props=props(C0402, "C307331", note="Flash decoupling"), fields="left")
    s.part("Device:R", "R404", "10k", 426.72, 134.62, {"1": "+3V3", "2": "QSPI_SS_INVERTED"},
           props=props(R0402, "C25744", True, "QSPI_SS pull-up, DNP (guide R1 is DNF)"), dnp=True, fields="left")
    s.note("R404 DNP: this flash doesn't\nneed a CS pull-up (guide R1).", 358.14, 158.75)

    s.rect(467.36, 81.28, 584.2, 175.26)
    heading(s, "PSRAM", 474.98, 88.9,
            "APS6404L-3SQR-SN, 8 MB, on CS1 = GPIO 47:\nthe stall buffer between SCSI and the host.")
    PX, PY = 497.84, 134.62
    s.part("Memory_RAM:APS6404L-3SQRx-SN", "U403", "APS6404L-3SQR-SN", PX, PY,
           {"1": "PSRAM_CE_INVERTED", "6": "QSPI_SCLK", "5": "QSPI_SD0", "2": "QSPI_SD1", "3": "QSPI_SD2",
            "7": "QSPI_SD3", "8": "+3V3", "4": "GND"},
           props=props("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "C5333729",
                       note="8 MB QSPI PSRAM, 2.7-3.6 V (the -3 part)"),
           fields=((PX + 2.54, PY - 15.24, "left"), (PX + 2.54, PY + 15.24, "left")))
    s.part("Device:C", "C422", "100nF", 520.7, 134.62, {"1": "+3V3", "2": "GND"},
           props=props(C0402, "C307331", note="PSRAM decoupling"), fields="left")
    s.part("Device:C", "C423", "1uF 25V", 533.4, 134.62, {"1": "+3V3", "2": "GND"},
           props=props(C0402, "C52923", note="PSRAM bulk"), fields="left")
    s.part("Device:R", "R403", "3.3k", 553.72, 134.62, {"1": "+3V3", "2": "PSRAM_CE_INVERTED"},
           props=props(R0402, "C25890", note="PSRAM CS1 pull-up (fitted)"), fields="left")
    s.note("R403 3.3k: the RP2350 pulls GPIO 47 low at reset\n(36k min); 10k gave 2.58 V, under the PSRAM's VIH\n"
           "(VDD - 0.4 V). 3.3k gives 3.02 V.", 474.98, 156.21)

    # ================= Debug and buttons =================
    s.rect(350.52, 180.34, 584.2, 297.18)
    heading(s, "Debug and buttons", 358.14, 187.96,
            "Tag-Connect TC2030-IDC pads (no part on the BOM) for the J-Link EDU via an ARM20-CTX adapter.\n"
            "BOOTSEL + reset = USB bootloader; normally the host enters BOOTSEL in software.")
    JX, JY = 383.54, 226.06
    s.part("Connector:TC2030", "J401", "TC2030-IDC", JX, JY,
           {"1": "+3V3", "2": "SWDIO", "3": "RUN", "4": "SWCLK", "5": "GND", "6": "NC"},
           props=props("Connector:Tag-Connect_TC2030-IDC-FP_2x03_P1.27mm_Vertical", "", fit="None",
                       note="Footprint only (legged, clip holes). 1 VCC, 2 SWDIO, 3 nRESET, 4 SWCLK, 5 GND, 6 SWO (NC)"),
           fields=((JX - 5.08, JY - 6.35, "left"), (JX - 5.08, JY + 6.35, "left")))
    SWP = props("", "", fit="Hand", note="Owner's through-hole tact switch; footprint to do once the part is checked")
    for k, (lbl, rref, sref, val) in enumerate((("QSPI_SS_INVERTED", "R405", "SW401", "BOOTSEL"),
                                                 ("RUN", "R406", "SW402", "RUN"))):
        x = 459.74 + k * 45.72
        chain(x, 220.98, [(rref, "Device:R", "1k", props(R0402, "C11702", note=f"{val} button series R"),
                           0, "1", "2", 3.81, False),
                          (sref, "Switch:SW_Push", val, SWP, 270, "1", "2", 5.08, False)],
              lbl, "GND")
    s.note("BOOTSEL pulls QSPI_SS low through 1k at reset; RUN has no pull-up\n(the guide fits none; the RP2350 pulls RUN up internally).",
           358.14, 262.89)

    # ================= FT1248 rework links =================
    s.rect(12.7, 195.58, 154.94, 300.99)
    heading(s, "FT1248 rework links", 20.32, 203.2,
            "Fitted 0R: GPIO 36-40 -> I2C / microSD (normal). Unfitted 0R: the\n"
            "same GPIO -> FT232H pins 17-20, 27. Moving the links trades I2C +\n"
            "microSD for 8-bit FT1248 (36-39) or 245-FIFO mode (36-40).")
    for i, (n, (fit, dnp, ftpin)) in enumerate(sorted(REWORK.items())):
        x, y = 40.64 + (i % 2) * 58.42, 233.68 + (i // 2) * 22.86
        s.net_at(f"GPIO{n}", x - 7.62, y, 180)
        s.wire(x - 7.62, y, x - 2.54, y)
        s.wire(x - 2.54, y, x - 2.54, y + 7.62)
        s.junction(x - 2.54, y)
        s.part("Device:R", f"R{418 + 2 * i}", "0R", x + 3.81, y, {"1": None, "2": fit}, a=90,
               props=props(R0402, "C17168", note=f"GPIO{n} -> {fit} (fitted)"),
               fields=((x + 3.81, y - 2.54, ""), (x + 3.81, y + 2.54, "")))
        s.wire(x - 2.54, y, x, y)
        s.part("Device:R", f"R{419 + 2 * i}", "0R", x + 3.81, y + 7.62, {"1": None, "2": dnp}, a=90,
               props=props(R0402, "C17168", True, f"GPIO{n} -> FT232H pin {ftpin} (rework, DNP)"), dnp=True,
               fields=((x + 3.81, y + 10.16, ""), (x + 3.81, y + 12.7, "")))
        s.wire(x - 2.54, y + 7.62, x, y + 7.62)
        for k in ((f"R{418 + 2 * i}", "1"), (f"R{419 + 2 * i}", "1")):
            s.intended[k] = f"GPIO{n}"

    # ================= TERMPWR sense =================
    s.rect(12.7, 306.07, 154.94, 406.4)
    heading(s, "TERMPWR sense (ADC6)", 20.32, 313.69,
            "0.5 x TERMPWR on GPIO 46: 0-5.6 V -> 0-2.8 V.\nDraws 26 uA from TERMPWR.")
    chain(43.18, 340.36, [("R428", "Device:R", "100k", props(R0402, "C25741", note="TERMPWR sense top"),
                           0, "1", "2", 3.81, False),
                          ("R429", "Device:R", "100k", props(R0402, "C25741", note="TERMPWR sense bottom"),
                           0, "1", "2", 3.81, False)],
          "TERMPWR", "GND", taps={0: "TERMPWR_SENSE"})
    s.part("Device:C", "C424", "100nF", 73.66, 353.06, {"1": "TERMPWR_SENSE", "2": "GND"},
           props=props(C0402, "C307331", note="ADC input cap, at the pin"), fields="left")
    s.note("Firmware keeps GPIO 46's digital input\nbuffer off (analog use).", 20.32, 383.54)

    s.write(path)
    return s.intended
