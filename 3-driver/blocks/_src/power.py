# Page 1: power. Rendered into ../1-power.md by build.py.
from canvas import Diagram
D = Diagram()

D.box('usbc', 2, 0, 18, 5, "USB-C", "receptacle", "VBUS     CC1/2", name="USB-C receptacle")
D.box('bench', 62, 0, 26, 5, "Bench 5 V input", "2 clip terminals", "(test posts or screw)")
D.box('cc', 24, 5, 32, 6, "CC sense (sink side): 5.1k", "Rd on CC1/CC2 + detector",
      "or comparators -> CC_OK", "(port allows >= 1.5 A)", name="CC sense")
D.box('prot', 62, 7, 26, 5, "Reverse-polarity", "+ over-voltage", "protection", name="Reverse-polarity + OV protection")
D.box('dA', 2, 13, 18, 3, "Ideal diode A")
D.box('dB', 62, 13, 26, 3, "Ideal diode B")
D.box('tp', 2, 22, 26, 7, "Ideal diode + enable", "+ polyfuse (<= 1.5 A)", "+ disable jumper",
      "EN = CC_OK OR BENCH", "+ LED: we supply", name="TERMPWR switch (ideal diode + enable + polyfuse)")
D.box('reg', 34, 22, 24, 4, "3.3 V regulator", "(LDO or buck)")
D.box('tsense', 62, 22, 26, 6, "Senses TERMPWR node:", "TERMPWR_OK -> MCU", "(1 digital in)",
      "+ LED (< 1 mA draw)", name="TERMPWR sense")
D.box('t285', 2, 35, 26, 4, "2.85 V regulator", "-> terminators (p.2)")

D.link('usbc', 'dA', [(6, 5), (6, 12)], "VBUS", at=(7, 9))
D.link('usbc', 'cc', [(15, 5), (15, 7), (23, 7)], "CC1/2", at=(17, 6))
D.link('bench', 'prot', [(75, 5), (75, 6)])
D.link('prot', 'dB', [(75, 12), (75, 12)])
# +5V_SYS: both ideal diodes feed one bus; '+' marks the taps.
D.link('dA', '*+5V_SYS', [(11, 16), (11, 18), (45, 18)])
D.link('dB', '*+5V_SYS', [(75, 16), (75, 18), (45, 18)])
D.note(28, 17, "+5V_SYS  (budget <= 3 A)")
D.link('*+5V_SYS', 'tp', [(14, 18), (14, 21)])
D.link('*+5V_SYS', 'reg', [(45, 18), (45, 21)])
D.link('tp', 't285', [(14, 29), (14, 34)], "TERMPWR:\n4.25-5.25 V,\n>= 900 mA, to\nSCSI pin 26 (p.2)",
       at=(16, 30))
D.link('reg', '@+3V3 loads', [(45, 26), (45, 27)],
       "+3V3 -> RP2350B IOVDD (its 1.1 V core comes\n"
       "   from the RP2350's on-chip regulator),\n"
       "   QSPI flash, PSRAM, microSD, FT232H,\n"
       "   USB hub, LVT125 drivers, Schmitt\n"
       "   receivers, LA-header buffers", at=(34, 28))
