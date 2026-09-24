# Page 4: the USB path. Rendered into ../4-usb.md by build.py.
from canvas import Diagram
D = Diagram()

D.box('host', 0, 0, 22, 4, "Host computer", "sees 3 USB devices")
D.box('usbc', 0, 7, 22, 6, "USB-C receptacle", "USB 2.0 only:", "both D+/D- pairs", "tied; SBU n/c")
D.box('pwr', 32, 6, 24, 4, "POWER (p.1)", "VBUS ORing, CC_OK")
D.box('esd', 0, 16, 22, 4, "ESD array", "(TVS, low-C)")
D.box('hub', 0, 23, 22, 6, "USB 2.0 HS hub", "CH334P + 12 MHz", "crystal (no caps)", "4 ports, 2 used")
D.box('hxtal', 2, 30, 18, 3, "12 MHz crystal")
D.box('ft', 40, 21, 24, 6, "FT232H", "USB 2.0 HS bridge", "async 245 FIFO", "<= 8 MB/s")
D.box('ee', 40, 28, 24, 5, "93LC56B EEPROM", "(sets FIFO mode)", "+ 12 MHz crystal")
D.box('rp', 76, 17, 30, 14, "RP2350B", "", "native USB on dedicated", "pins (0 GPIO)", "",
      "over USB:", "- ROM BOOTSEL: UF2 /", "  picotool (can't brick)", "- CDC console",
      "- reset-to-BOOTSEL", "  interface")

D.link('host', 'usbc', [(10, 4), (10, 6)], "USB-C cable", at=(12, 5))
D.link('usbc', 'pwr', [(22, 8), (31, 8)], "VBUS, CC", at=(23, 7))
D.link('usbc', 'esd', [(10, 13), (10, 15)], "D+/D-", at=(12, 14))
D.link('esd', 'hub', [(10, 20), (10, 22)], "90 ohm diff pair", at=(12, 21))
D.link('hub', 'hxtal', [(10, 29), (10, 29)], arrow=None)
D.link('hub', 'ft', [(22, 24), (39, 24)], "port 1: HS\n480 Mbit/s", at=[(24, 23), (24, 25)])
D.link('ft', 'ee', [(52, 27), (52, 27)], arrow=None)
D.link('ft', 'rp', [(64, 23), (75, 23)], "245 FIFO\n12 GPIO PIO1",
       at=[(66, 22), (64, 24)], arrow='<>')
D.link('hub', 'rp', [(22, 27), (30, 27), (30, 35), (90, 35), (90, 31)],
       "port 2: FS 12 Mbit/s; 27 ohm series R x2 near RP2350", at=(34, 36))
