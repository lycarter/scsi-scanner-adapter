# Page 3: RP2350B and its support parts. Rendered into ../3-mcu-support.md by build.py.
from canvas import Diagram
D = Diagram()

D.box('rp', 32, 2, 28, 22, *[""] * 7, "RP2350B", "QFN-80, 48 GPIO", "520 KB SRAM", "3 PIO blocks")
D.box('xtal', 2, 3, 24, 3, "12 MHz ABM8-272-T3")
D.box('swd', 2, 8, 24, 4, "SWD: TC2030-IDC pads", "(J-Link EDU)", name="SWD (Tag-Connect TC2030)")
D.box('btn', 2, 14, 24, 4, "BOOTSEL + RUN", "buttons (owner THT)")
D.box('core', 2, 19, 24, 4, "1.1 V core: on-chip", "reg + 3.3 uH Abracon")
D.box('flash', 70, 2, 20, 4, "QSPI flash", "W25Q128 16 MB")
D.box('psram', 70, 7, 20, 6, "PSRAM 8 MB", "APS6404L-3SQR", "shares QSPI bus")
D.box('sd', 70, 14, 20, 5, "microSD socket", "1-bit SDIO, PIO2", "CD: expander")
D.box('usb', 70, 20, 20, 5, "USB hub port 2", "(p.4): updates,", "CDC console")
budget = [("SCSI front end (p.2), PIO0", "32"), ("FT232H FT1248 4-bit, PIO1", "7"),
          ("microSD 1-bit SDIO, PIO2", "3"), ("PSRAM CS1 (GPIO 47)", "1"),
          ("I2C to TCA9555 expander", "2"), ("LA markers", "2"), ("TERMPWR ADC (GPIO 46)", "1")]
D.box('gpio', 26, 27, 40, 11, "Other GPIO users (see NOTES budget):",
      *[f"{k:<30}{v:>5}" for k, v in budget], "TOTAL 48 of 48 (none spare)", name="Other GPIO users")

D.link('xtal', 'rp', [(26, 4), (31, 4)])
D.link('swd', 'rp', [(26, 9), (31, 9)], arrow='<>')
D.link('btn', 'rp', [(26, 15), (31, 15)])
D.link('core', 'rp', [(26, 20), (31, 20)], arrow='<>')
D.link('rp', 'flash', [(60, 5), (67, 5), (67, 3), (69, 3)], "QSPI", at=(61, 4), net='QSPI')
D.link('*QSPI', 'psram', [(67, 5), (67, 9), (69, 9)])
D.link('rp', 'psram', [(60, 11), (69, 11)], "CS1", at=(61, 10))
D.link('rp', 'sd', [(60, 16), (69, 16)], "3", at=(61, 15), arrow='<>')
D.link('rp', 'usb', [(60, 22), (69, 22)], "USB (FS)", at=(61, 21), arrow='<>')
D.link('rp', 'gpio', [(46, 24), (46, 26)])
