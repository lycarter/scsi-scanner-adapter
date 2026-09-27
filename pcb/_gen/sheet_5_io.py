"""I/O: pcb/5-io.kicad_sch. TCA9555 expander, status LEDs, microSD socket, board test points.

Sources: blocks/5-rp2350-pinout.md (TCA9555 pinout, accepted), NOTES "Resistor and small-part values",
"Connectors" (microSD), parts-list.md §3 and §6.
"""
from schgen import Sheet, G

FILE = "5-io.kicad_sch"
FILE_UUID = "041be861-a36d-4acc-983c-7af91692c802"
ROOT = "2c5b21a9-7d0d-4304-8bd9-0602cba3b7b5"
SHEET_SYM = "e668c732-65b6-44b8-a62c-386a17bfcd95"          # the "io" sheet symbol on the root

R0402, C0402, C0805 = ("Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric",
                       "Capacitor_SMD:C_0805_2012Metric")
TPAD = "TestPoint:TestPoint_Pad_D1.5mm"


def props(fp, lcsc, dnp=False, note="", fit="JLC", ds=""):
    return {"Footprint": fp, "Datasheet": ds, "Description": note, "LCSC": lcsc, "Fit": "DNP" if dnp else fit}


def heading(s, t, x, y, body=""):
    s.text(t, x, y, 2.0, bold=True)
    if body:
        s.text(body, x, y + 4.5, 1.27)


def build(path):
    s = Sheet(FILE_UUID, "A3", "SCSI scanner adapter", f"/{ROOT}/{SHEET_SYM}", seed=FILE)
    s.refbase = 500
    s.rails = {"+3V3", "+5V_SYS", "VTERMINATOR", "TERMPWR"}
    s.hier = {"I2C_SDA": "bidirectional", "I2C_SCL": "input", "SD_CLK": "input", "SD_CMD": "bidirectional",
              "SD_D0": "bidirectional", "TERMPWR_EN_INVERTED": "input", "IS_BENCH_POWERED": "input",
              "BENCH_EFUSE_FAULT_INVERTED": "input", "TERMPWR_EFUSE_FAULT_INVERTED": "input",
              "TERMINATOR_EN_INVERTED_FIRMWARE": "bidirectional", "FT232H_RESET_INVERTED": "output",
              "HUB_RESET_INVERTED": "output"}

    def vpart(lib, ref, val, x, y, top, bot, pr, a=0, tp="1", bp="2"):
        s.part(lib, ref, val, x, y, {tp: top, bp: bot}, a=a, props=pr,
               fields="left" if a == 0 else ((x + 2.54, y - 1.27, "right"), (x + 2.54, y + 1.27, "right")))

    # ================= I/O expander =================
    s.rect(12.7, 12.7, 254.0, 198.12)
    heading(s, "I/O expander (TCA9555, I2C0 address 0x20)", 20.32, 20.32,
            "Slow signals: status in on port 0, controls out on port 1 (our convention; every pin has its own\n"
            "direction bit). All pins power up as inputs with ~100k pull-ups, so the board is safe with no firmware.")
    UX, UY = 139.7, 104.14
    nets = {"23": "I2C_SDA", "22": "I2C_SCL", "1": "EXPANDER_INTERRUPT_INVERTED", "3": None, "2": None, "21": None,
            "24": "+3V3", "12": "GND",
            "4": "SD_CARD_DETECT", "5": "TERMPWR_EN_INVERTED", "6": "IS_BENCH_POWERED",
            "7": "BENCH_EFUSE_FAULT_INVERTED", "8": "TERMPWR_EFUSE_FAULT_INVERTED", "9": None,
            "10": "LED_YELLOW_INVERTED", "11": "LED_GREEN_INVERTED",
            "13": "LED_STATUS_INVERTED", "14": "LED_ACTIVITY_INVERTED", "15": "TERMINATOR_EN_INVERTED_FIRMWARE",
            "16": "FT232H_RESET_INVERTED", "17": "HUB_RESET_INVERTED", "18": None, "19": "EXPANDER_P16",
            "20": "EXPANDER_P17"}
    s.part("Interface_Expansion:TCA9555PWR", "U501", "TCA9555PWR", UX, UY, nets,
           props=props("Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", "C465732", note="16-bit I2C expander",
                       ds="https://www.ti.com/lit/ds/symlink/tca9555.pdf"),
           fields=((UX + 2.54, UY - 30.48, "left"), (UX + 2.54, UY + 30.48, "left")))
    # P05 and P15 sit under sheet-pin labels: longer stubs so their labels clear them
    for pin, net, ln in (("9", "LED_RED_INVERTED", 38.1), ("18", "EXPANDER_P15", 25.4)):
        yy = UY - {"9": 7.62, "18": -15.24}[pin]
        s.wire(UX + 17.78, yy, UX + 17.78 + ln, yy)
        s.net_at(net, UX + 17.78 + ln, yy, 0)
        s.intended[("U501", pin)] = net
    # A0-A2 to GND on a short bus: address 0x20
    ax = UX - 20.32
    for yy in (UY + 15.24, UY + 17.78, UY + 20.32):
        s.wire(UX - 17.78, yy, ax, yy)
    s.wire(ax, UY + 15.24, ax, UY + 17.78)
    s.wire(ax, UY + 17.78, ax, UY + 20.32)
    s.junction(ax, UY + 17.78)
    s.wire(ax, UY + 20.32, ax, UY + 22.86)
    s.power("GND", ax, UY + 22.86, 270)
    for p in ("2", "3", "21"):
        s.intended[("U501", p)] = "GND"
    s.part("Device:C", "C501", "100nF", UX - 12.7, UY - 35.56, {"1": "+3V3", "2": "GND"},
           props=props(C0402, "C307331", note="U501 decoupling"), fields="left")
    for i, (ref, val, lcsc, net, note) in enumerate((("R501", "4.7k", "C25900", "I2C_SDA", "I2C SDA pull-up"),
                                                      ("R502", "4.7k", "C25900", "I2C_SCL", "I2C SCL pull-up"),
                                                      ("R503", "10k", "C25744", "EXPANDER_INTERRUPT_INVERTED",
                                                       "INT pull-up (open drain)"))):
        vpart("Device:R", ref, val, 38.1 + i * 20.32, 63.5, "+3V3", net, props(R0402, lcsc, note=note))
    s.table(20.32, 148.59, [["Pin", "Net", "Meaning"],
                            ["P00 in", "SD_CARD_DETECT", "microSD card present (switch polarity: check the socket datasheet)"],
                            ["P01 in", "TERMPWR_EN_INVERTED", "low = we supply TERMPWR (CC >= 1.5 A or bench)"],
                            ["P02 in", "IS_BENCH_POWERED", "high = running on the bench input (TPS2116 ST)"],
                            ["P03/P04 in", "*_EFUSE_FAULT_INVERTED", "low = bench / TERMPWR eFuse fault (or reverse block)"],
                            ["P05-P07 out", "LED_RED/YELLOW/GREEN_INVERTED", "spare LEDs (red, yellow, green); use to be decided in firmware"],
                            ["P10/P11 out", "LED_STATUS/ACTIVITY_INVERTED", "drive low to light the status (yellow) / activity (red) LED"],
                            ["P12 out/in", "TERMINATOR_EN_INVERTED_FIRMWARE", "through DIP 2; reads the /OE node back"],
                            ["P13/P14 out", "FT232H / HUB_RESET_INVERTED", "low >= 4 us resets the chip; idle high or input"],
                            ["P15-P17", "EXPANDER_P15..P17", "spare, brought out to test pads"]],
            [22.86, 60.96, 142.24], row_h=4.445, size=1.016, header_fill=(220, 220, 220))

    # ================= LEDs =================
    s.rect(12.7, 203.2, 195.58, 284.48)
    heading(s, "LEDs", 20.32, 210.82, "Lit when the expander drives the pin low. P05-P07: spare, use decided in firmware.")
    LEDS = [("R504", "D501", "LED_STATUS_INVERTED", "status", "KT-0805Y yellow", "C2296", "LED_0805", "1k", "C11702"),
            ("R505", "D502", "LED_ACTIVITY_INVERTED", "activity", "KT-0603R red", "C2286", "LED_0603", "1k", "C11702"),
            ("R511", "D503", "LED_RED_INVERTED", "spare red", "KT-0603R red", "C2286", "LED_0603", "1k", "C11702"),
            ("R512", "D504", "LED_YELLOW_INVERTED", "spare yellow", "KT-0805Y yellow", "C2296", "LED_0805", "1k",
             "C11702"),
            ("R513", "D505", "LED_GREEN_INVERTED", "spare green", "KT-0805G green", "C2297", "LED_0805", "470R",
             "C25117")]
    FPS = {"LED_0603": "LED_SMD:LED_0603_1608Metric", "LED_0805": "LED_SMD:LED_0805_2012Metric"}
    for i, (ref_r, ref_d, net, what, dval, dlcsc, dfp, rval, rlcsc) in enumerate(LEDS):
        x = 33.02 + i * 33.02
        vpart("Device:R", ref_r, rval, x, 236.22, "+3V3", None, props(R0402, rlcsc, note=f"{what} LED"))
        s.wire(x, 240.03, x, 245.11)
        vpart("Device:LED", ref_d, dval, x, 248.92, None, net, props(FPS[dfp], dlcsc, note=f"{what} LED"),
              a=90, tp="2", bp="1")
        s.intended[(ref_r, "2")] = s.intended[(ref_d, "2")] = f"~{ref_d}"
    s.note("1k: ~1.3 mA red/yellow. Green (KT-0805G, Vf 2.6-3.1 V at 5 mA) gets 470R: ~2.4 V at\n"
           "low current, so ~1.8 mA typical, >= ~0.7 mA at the top of the Vf spread.", 20.32, 269.24)

    # ================= microSD =================
    s.rect(259.08, 12.7, 406.4, 198.12)
    heading(s, "microSD (1-bit SDIO on PIO2)", 266.7, 20.32,
            "Spill-over storage when the host stalls. CLK, CMD, D0 go to the RP2350\n"
            "(through the rework links); D1-D3 are only pulled up.")
    SX, SY = 355.6, 83.82
    s.part("Connector:Micro_SD_Card_Det1", "J501", "TF PUSH", SX, SY,
           {"1": "SD_D2", "2": "SD_D3", "3": "SD_CMD", "4": "+3V3", "5": "SD_CLK", "6": "GND", "7": "SD_D0",
            "8": "SD_D1", "9": "SD_CARD_DETECT", "10": "GND"},
           props=props("", "C393941", note="SHOU HAN TF PUSH, push-push with card detect. Footprint to do "
                                           "(EasyEDA/LCSC, checked against the drawing)."),
           fields=((SX - 20.32, SY - 15.24, "left"), (SX - 20.32, SY + 17.78, "left")), stub=2 * G,
           inline=True)                                   # rails inline: the pins are only 2.54 apart
    for i, net in enumerate(("SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3")):
        vpart("Device:R", f"R{506 + i}", "10k", 279.4 + i * 15.24, 139.7, "+3V3", net,
              props(R0402, "C25744", note=f"SDIO pull-up ({net})"))
    s.part("Device:C", "C502", "10uF 25V", 368.3, 139.7, {"1": "+3V3", "2": "GND"},
           props=props(C0805, "C15850", note="microSD bulk"), fields="left")
    s.part("Device:C", "C503", "100nF", 386.08, 139.7, {"1": "+3V3", "2": "GND"},
           props=props(C0402, "C307331", note="microSD decoupling"), fields="left")
    s.note("Pull-ups 10k (SD spec: 10-100k) on CMD and D0-D3. D3 doubles as\ncard detect in SPI mode; "
           "we use the socket's switch instead (DET -> P00).\nUnverified: DET pin number and switch polarity "
           "(LCSC datasheet\nwasn't downloadable by script). Check before drawing the footprint.", 266.7, 160.02)

    # ================= Test points =================
    s.rect(200.66, 203.2, 406.4, 284.48)
    heading(s, "Test points", 208.28, 210.82, "Bare pads for probing at bring-up (not on the BOM). P15-P17: spare expander pins;\n"
            "INT: the expander interrupt (firmware polls, so it goes nowhere else).")
    TPS = [("+5V_SYS", "+5V_SYS", 213.36, 233.68), ("+3V3", "+3V3", 237.49, 233.68),
           ("VTERMINATOR", "VTERM", 261.62, 233.68), ("TERMPWR", "TERMPWR", 285.75, 233.68),
           ("TERMPWR_EN_INVERTED", "TP_EN", 213.36, 256.54), ("GND", "GND", 309.88, 233.68),
           ("EXPANDER_P15", "P15", 334.01, 233.68), ("EXPANDER_P16", "P16", 358.14, 233.68),
           ("EXPANDER_P17", "P17", 382.27, 233.68),
           ("EXPANDER_INTERRUPT_INVERTED", "INT", 251.46, 256.54)]   # second row stays clear of the title block
    for i, (net, lbl, x, y) in enumerate(TPS):
        s.part("Connector:TestPoint", "TP501" if lbl == "INT" else f"TP{502 + i}", lbl, x, y, {"1": net},
               props=props(TPAD, "", fit="None", note=f"Test pad: {net}"),
               fields=((x + 1.27, y - 5.08, "left"), (x + 1.27, y - 2.54, "left")))
    s.note("FT232H_3V3 gets its own pad on the ft232h sheet.", 208.28, 276.86)

    s.write(path)
    return s.intended
