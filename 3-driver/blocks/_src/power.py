# Page 1: power. Rendered into ../1-power.md by build.py.
from canvas import Diagram
D = Diagram()

D.box('usbc', 2, 0, 18, 5, "USB-C", "receptacle", "VBUS     CC1/2", name="USB-C receptacle")
D.box('bench', 62, 0, 26, 5, "Bench 5 V input", "5.08 mm screw term.", "+ test loop per pole")
D.box('cc', 24, 5, 32, 6, "CC sense (sink side): 5.1k", "Rd on CC1/CC2 + LM393",
      "vs 0.66 V (CJ431 ref)", "-> CC_OK_N (>= 1.5 A)", name="CC sense")
D.box('prot', 62, 7, 26, 5, "TPS259470A eFuse", "-15..28 V, OVLO 5.35 V", "ILIM ~2.2 A, EN zener", name="Bench eFuse (reverse + OV + current limit)")
D.box('dA', 2, 13, 18, 3, "U1 TPS2116 IN2", name="Power mux input 2 (USB)")
D.box('dB', 62, 13, 26, 3, "U1 TPS2116 IN1 (prio)", name="Power mux input 1 (bench, priority)")
D.box('tp', 2, 22, 26, 7, "U2 TPS259470A eFuse", "ILIM ~1.2 A, rev.block", "+ disable jumper",
      "OVLO<-CC_OK_N or BENCH", "3.3V pull-up + divider", name="TERMPWR switch (eFuse + enable + current limit)")
D.box('reg', 34, 22, 24, 4, "3.3 V regulator", "TPS73701 LDO")
D.box('tsense', 62, 22, 26, 6, "Senses TERMPWR node:", "100k/100k -> GPIO 46", "(ADC6)",
      "+ LED (< 1 mA draw)", name="TERMPWR sense")
D.box('t285', 2, 35, 26, 4, "TPS73701 @ 2.83 V", "-> terminators (p.2)")

D.link('usbc', 'dA', [(6, 5), (6, 12)], "VBUS", at=(7, 9))
D.link('usbc', 'cc', [(15, 5), (15, 7), (23, 7)], "CC1/2", at=(17, 6))
D.link('bench', 'prot', [(75, 5), (75, 6)])
D.link('prot', 'dB', [(75, 12), (75, 12)])
# +5V_SYS: both mux inputs feed one bus; '+' marks the taps.
D.link('dA', '*+5V_SYS', [(11, 16), (11, 18), (45, 18)])
D.link('dB', '*+5V_SYS', [(75, 16), (75, 18), (45, 18)])
D.note(28, 17, "+5V_SYS  (<= 2.5 A: TPS2116)")
D.link('*+5V_SYS', 'tp', [(14, 18), (14, 21)])
D.link('*+5V_SYS', 'reg', [(45, 18), (45, 21)])
D.link('tp', 't285', [(14, 29), (14, 34)], "TERMPWR:\n4.25-5.25 V,\n>= 900 mA, to\nSCSI pin 26 (p.2)",
       at=(16, 30))
D.link('reg', '@+3V3 loads', [(45, 26), (45, 27)],
       "+3V3 -> RP2350B IOVDD (its 1.1 V core comes\n"
       "   from the RP2350's on-chip regulator),\n"
       "   QSPI flash, PSRAM, microSD, USB hub,\n"
       "   front end, receivers, expander\n"
       "   (FT232H makes its own 3.3 V: VCCD)", at=(34, 28))
