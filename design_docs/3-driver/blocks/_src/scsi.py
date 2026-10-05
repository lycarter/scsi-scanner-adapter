# Page 2: SCSI front end. Rendered into ../2-scsi-frontend.md by build.py.
from canvas import Diagram
D = Diagram()

D.box('idc', 2, 0, 22, 4, "IDC50 (fitted)", "to scanner / G4")
D.box('hd50', 62, 0, 28, 4, "HD50 footprint (DNP)", "pass-through / alt.")
D.box('term', 2, 10, 24, 7, "Switchable active", "terminator: 18 x", "(2 x 220 ohm) to",
      "2.83 V, fed from", "TERMPWR; EN<-DIP sw", name="Switchable active terminator")
D.box('drv', 30, 10, 28, 9, "DRIVERS: 14 x FDV301N", "N-FET, gate <- MCU pin",
      "open-drain, <=0.5V@48mA", "14: DB0-7, DBP, ATN,", "ACK, SEL, BSY, RST",
      "4.7k gate pull-downs:", "off in reset / unpowered", name="DRIVERS (14 x FDV301N)")
D.box('rcv', 62, 10, 28, 8, "RECEIVERS: 18 x", "Nexperia 74LVC1G17", "VT+ <= 2.0, VT- >= 0.8",
      "5 V-tolerant, Ioff", "all 18, always on", "out: 3.3 V logic", name="RECEIVERS (18 x 74LVC1G17)")
D.box('rp', 30, 21, 28, 7, "RP2350B PIO", "14 out + 18 in", "= 32 GPIO, one", "32-pin PIO window",
      name="RP2350B (PIO; CPU for the markers)")
D.note(2, 21, "One cluster per line:", "FET + 3 passives +", "1G17 + 100 nF.",
       "Fallbacks: 4 x LVTH125,", "3 x Nexperia LVC14A", "",
       "ESD at the connector:", "18 x H5VUD5BB (0.3 pF),", "SMF6.0A on TERMPWR")
D.box('la', 67, 25, 24, 5, "LA header 2x17", "(Digital Discovery)", "18 sig + 2 markers")

# The bus runs straight between the two connectors; everything else taps it.
D.link('idc', 'hd50', [(12, 4), (12, 6), (75, 6), (75, 4)], arrow=None, net='SCSI',
       label="SCSI bus: 18 signals + TERMPWR + GND", at=(24, 5))
D.note(15, 8, "(straight run; stub <= 0.1 m)")
D.link('*SCSI', 'term', [(12, 6), (12, 9)], arrow=None)
D.link('drv', '*SCSI', [(44, 9), (44, 6)])
D.link('*SCSI', 'rcv', [(75, 6), (75, 9)])
D.link('rp', 'drv', [(44, 20), (44, 19)], "14 x gate", at=(46, 19))
D.link('rcv', 'rp', [(66, 18), (66, 23), (58, 23)], "18 in", at=(59, 22))
D.link('rcv', 'la', [(86, 18), (86, 24)], "isolation:\n20 x 100 ohm\nseries R", at=(72, 19))
# The markers are GPIO 32/33, outside PIO0's 0-31 window: the CPU drives them (see pinout.py).
D.link('rp', 'la', [(58, 26), (66, 26)], "markers", at=(59, 25))
