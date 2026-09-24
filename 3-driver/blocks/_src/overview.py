# Page 0: overview of the driver board. Rendered into ../0-overview.md by build.py.
from canvas import Diagram
D = Diagram()

D.frame(0, 3, 104, 30, "DRIVER BOARD")
D.box('usbc', 3, 5, 13, 5, "USB-C", "connector")
D.box('hub', 21, 5, 15, 5, "USB 2.0", "HS hub", "(p.4)", name="USB 2.0 HS hub")
D.box('ft', 41, 5, 14, 5, "FT232H", "HS bridge", "(p.4)")
D.box('rp', 61, 5, 14, 20, "RP2350B", "", "(p.3)")
D.box('scsi', 82, 5, 20, 8, "SCSI front end", "(p.2)", "drivers,", "receivers,", "terminator,",
      "IDC50 / HD50")
D.box('la', 82, 16, 20, 5, "LA header", "(Digital", "Discovery 2x16)")
D.box('pwr', 3, 13, 22, 7, "POWER  (p.1)", "USB + bench 5 V", "ORing, TERMPWR,", "regulators")
D.box('sup', 28, 27, 50, 5, "MCU support (p.3): QSPI flash, 8 MB PSRAM,",
      "microSD (SDIO), 12 MHz crystal, SWD header,", "BOOTSEL/RUN buttons, LEDs", name="MCU support (p.3)")

D.link('@Host computer', 'usbc', [(6, 1), (6, 4)], "USB-C cable (HS data + 5 V)", at=(8, 1))
D.note(8, 0, "Host computer")
D.link('usbc', 'hub', [(16, 7), (20, 7)], "D+/D-", at=(16, 6))
D.link('hub', 'ft', [(36, 7), (40, 7)], "HS", at=(37, 6))
D.link('ft', 'rp', [(55, 7), (60, 7)], "FIFO", at=(56, 6), arrow='<>')
D.link('hub', 'rp', [(28, 10), (28, 11), (60, 11)], "FS: updates, console", at=(30, 12))
D.link('rp', 'scsi', [(75, 8), (81, 8)], "PIO", at=(77, 7), arrow='<>')
D.link('scsi', '@D4000 scanner (+ G4)', [(92, 4), (92, 1)], "ribbon", at=(94, 2), arrow='<>')
D.note(80, 0, "D4000 scanner (+ G4)")
D.link('scsi', 'la', [(92, 13), (92, 15)], "copies", at=(94, 14))
D.link('rp', 'la', [(75, 18), (81, 18)], "markers", at=(75, 17))
D.link('usbc', 'pwr', [(6, 10), (6, 12)], "VBUS", at=(7, 11))
D.link('usbc', 'pwr', [(12, 10), (12, 12)], "CC level", at=(13, 11))
D.link('@bench 5 V in', 'pwr', [(8, 22), (8, 20)], "bench 5 V in (clip terminals)", at=(3, 23))
D.note(28, 14, "+5V_SYS, +3V3", "-> all blocks", "", "TERMPWR -> p.2")
D.link('rp', 'sup', [(68, 25), (68, 26)], arrow=None)
