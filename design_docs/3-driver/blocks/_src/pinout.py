# Page 5: RP2350B pin map. Rendered into ../5-rp2350-pinout.md by build.py.
# Physical pins: RP2350 datasheet §1.2.1, Figure 3 (QFN-80, top view).
from canvas import Diagram
D = Diagram()

# Package pin -> pad name, counter-clockwise from pin 1 (datasheet Figure 3).
PADS = {n: f"GPIO{g}" for n, g in zip(range(1, 5), range(4, 8))}
PADS.update({5: 'IOVDD', 6: 'GPIO8', 7: 'GPIO9', 8: 'GPIO10', 9: 'GPIO11', 10: 'DVDD',
             11: 'GPIO12', 12: 'GPIO13', 13: 'GPIO14', 14: 'GPIO15', 15: 'IOVDD',
             16: 'GPIO16', 17: 'GPIO17', 18: 'GPIO18', 19: 'GPIO19', 20: 'GPIO20',
             21: 'GPIO21', 22: 'GPIO22', 23: 'GPIO23', 24: 'IOVDD', 25: 'GPIO24',
             26: 'GPIO25', 27: 'GPIO26', 28: 'GPIO27', 29: 'IOVDD', 30: 'XIN', 31: 'XOUT',
             32: 'DVDD', 33: 'SWCLK', 34: 'SWDIO', 35: 'RUN', 36: 'GPIO28', 37: 'GPIO29',
             38: 'GPIO30', 39: 'GPIO31', 40: 'GPIO32',
             41: 'IOVDD', 42: 'GPIO33', 43: 'GPIO34', 44: 'GPIO35', 45: 'GPIO36',
             46: 'GPIO37', 47: 'GPIO38', 48: 'GPIO39', 49: 'GPIO40_ADC0', 50: 'IOVDD',
             51: 'DVDD', 52: 'GPIO41_ADC1', 53: 'GPIO42_ADC2', 54: 'GPIO43_ADC3',
             55: 'GPIO44_ADC4', 56: 'GPIO45_ADC5', 57: 'GPIO46_ADC6', 58: 'GPIO47_ADC7',
             59: 'ADC_AVDD', 60: 'IOVDD',
             61: 'VREG_AVDD', 62: 'VREG_PGND', 63: 'VREG_LX', 64: 'VREG_VIN', 65: 'VREG_FB',
             66: 'USB_DM', 67: 'USB_DP', 68: 'USB_OTP_VDD', 69: 'QSPI_IOVDD', 70: 'QSPI_SD3',
             71: 'QSPI_SCLK', 72: 'QSPI_SD0', 73: 'QSPI_SD2', 74: 'QSPI_SD1', 75: 'QSPI_SS',
             76: 'IOVDD', 77: 'GPIO0', 78: 'GPIO1', 79: 'GPIO2', 80: 'GPIO3'})

# What each GPIO carries (accepted 2026-09-25; review changes 2026-09-26: ATN on PIO0 out+9,
# GPIO 46 = TERMPWR ADC, CS1 pull-up 3.3k). Both SCSI blocks follow the SCSI-2 connector
# order (Table 2: DB0-7, DBP, ATN, BSY, ACK, RST, MSG, SEL, C/D, REQ, I/O). "in" = receiver output (INOVER: 1 = asserted),
# "gate" = FDV301N gate (1 = asserted).
DB = ['DB0', 'DB1', 'DB2', 'DB3', 'DB4', 'DB5', 'DB6', 'DB7', 'DBP']
GPIO = {}
for k, s in enumerate(DB):
    GPIO[k] = (f"{s} in", f"PIO0 in+{k}")
for k, s in enumerate(['ATN', 'BSY', 'ACK', 'RST', 'MSG', 'SEL', 'C/D', 'REQ', 'I/O'], start=9):
    GPIO[k] = (f"{s} in", f"PIO0 in+{k}")
for k, s in enumerate(DB):
    GPIO[18 + k] = (f"{s} gate", f"PIO0 out+{k}")
GPIO.update({
    27: ('ATN gate', 'PIO0 out+9'), 28: ('BSY gate', 'CPU'), 29: ('ACK gate', 'PIO0 side-set'),
    30: ('RST gate', 'CPU only'), 31: ('SEL gate', 'CPU'),
    # GPIO 32-46 order from the crossing-count solver (../tools/ft1248_pinsolve.py, 2026-09-27).
    32: ('LA marker 1', 'CPU'), 33: ('LA marker 0', 'CPU'),
    # Fallback (NOTES "FT1248 fallback plan"): move the 0R links and these pins become FT232H
    # FIFO / 8-bit FT1248 lines. FT pin numbers are FT232H package pins (DS v2.0).
    34: ('SD D0', '0R >> FIFO WR# (FT 27)'),
    35: ('FT MISO', 'PIO1; FIFO RD#'), 36: ('FT SS_n', 'PIO1; FIFO TXE#'),
    37: ('FT SCLK', 'PIO1; FIFO RXF#'),
    38: ('FT MIOSIO0', 'PIO1; FIFO D0'), 39: ('FT MIOSIO1', 'PIO1; FIFO D1'),
    40: ('FT MIOSIO2', 'PIO1; FIFO D2'), 41: ('FT MIOSIO3', 'PIO1; FIFO D3'),
    42: ('I2C1 SDA', '0R >> FIFO D4 (FT 17)'), 43: ('I2C1 SCL', '0R >> FIFO D5 (FT 18)'),
    44: ('SD CLK', '0R >> FIFO D6 (FT 19)'), 45: ('SD CMD', '0R >> FIFO D7 (FT 20)'),
    46: ('TERMPWR ADC', 'ADC6, 100k/100k'),
    47: ('PSRAM CS1', 'QMI, 3.3k up'),
})
OTHER = {
    'IOVDD': '3.3 V', 'DVDD': '1.1 V core', 'ADC_AVDD': '3.3 V', 'USB_OTP_VDD': '3.3 V',
    'QSPI_IOVDD': '3.3 V', 'XIN': '12 MHz crystal', 'XOUT': '12 MHz crystal',
    'SWCLK': 'TC2030 pad 4', 'SWDIO': 'TC2030 pad 2', 'RUN': 'RUN btn; TC2030 pad 3',
    'VREG_AVDD': 'core reg (33R+4u7)', 'VREG_PGND': 'core reg GND', 'VREG_LX': 'core reg L',
    'VREG_VIN': 'core reg 3.3 V in', 'VREG_FB': 'core reg -> DVDD',
    'USB_DM': 'hub port 2 D-', 'USB_DP': 'hub port 2 D+',
    'QSPI_SS': 'flash CS, BOOTSEL', 'QSPI_SCLK': 'flash + PSRAM',
    'QSPI_SD0': 'flash + PSRAM', 'QSPI_SD1': 'flash + PSRAM',
    'QSPI_SD2': 'flash + PSRAM', 'QSPI_SD3': 'flash + PSRAM',
}

pins = {}
for num, pad in PADS.items():
    if pad.startswith('GPIO'):
        g = int(pad[4:].split('_')[0])
        sig, owner = GPIO[g]
        pins[num] = (pad, f"{sig:<11} {owner}")
    else:
        pins[num] = (pad, OTHER[pad])

D.chip45('rp', 0, 0, 20, pins, name='RP2350B',
         inner=["RP2350B", "QFN-80, top view", "", "rotated 45 deg CCW:", "package top edge",
                "faces upper-left", "", "* = pin 1", "EP (81) = GND"])
