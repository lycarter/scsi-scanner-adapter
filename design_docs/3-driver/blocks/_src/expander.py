# Page 5, second diagram: TCA9555 I2C GPIO expander. Rendered into ../5-rp2350-pinout.md.
# Physical pins: TI TCA9555 datasheet SCPS200E, "Pin Functions" (PW / TSSOP-24).
from canvas import Diagram
D = Diagram()

# Port 0 = inputs (status), port 1 = outputs, so each port has one direction.
# All P pins power up as inputs with ~100 k pull-ups: resets read high (run), LEDs are off
# (they sink into the pin), and TERMINATOR_EN_INVERTED_FIRMWARE leaves the DIP default alone.
pins = {
    1: ('INT', 'test point (firmware polls)'),
    2: ('A1', 'GND (addr 0x20)'),
    3: ('A2', 'GND'),
    4: ('P00', 'in: SD_CD (socket switch)'),
    5: ('P01', 'in: TERMPWR_EN_INVERTED (enable node)'),
    6: ('P02', 'in: IS_BENCH_POWERED (TPS2116 ST, 1 = bench)'),
    7: ('P03', 'in: BENCH_EFUSE_FAULT_INVERTED (eFuse)'),
    8: ('P04', 'in: TERMPWR_EFUSE_FAULT_INVERTED (eFuse)'),
    9: ('P05', 'spare in/out'),
    10: ('P06', 'spare in/out'),
    11: ('P07', 'spare in/out'),
    12: ('GND', 'GND'),
    13: ('P10', 'out: LED1_N (status)'),
    14: ('P11', 'out: LED2_N (activity)'),
    15: ('P12', 'out/in: TERMINATOR_EN_INVERTED_FIRMWARE (DIP 2)'),
    16: ('P13', 'out: FT232H_RESET_INVERTED'),
    17: ('P14', 'out: HUB_RESET_INVERTED (Schottky)'),
    18: ('P15', 'out: SD_PWR_EN (optional)'),
    19: ('P16', 'spare in/out'),
    20: ('P17', 'spare in/out'),
    21: ('A0', 'GND'),
    22: ('SCL', 'GPIO 37 (I2C0), 4.7k up'),
    23: ('SDA', 'GPIO 36 (I2C0), 4.7k up'),
    24: ('VCC', '3.3 V, 100 nF'),
}
D.chip2('exp', 0, 0, pins, title=["TCA9555PWR", "TSSOP-24, top view"], name='TCA9555')
