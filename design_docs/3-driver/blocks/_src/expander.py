# Page 5, second diagram: TCA9555 I2C GPIO expander. Rendered into ../5-rp2350-pinout.md.
# Physical pins: TI TCA9555 datasheet SCPS200E, "Pin Functions" (PW / TSSOP-24).
from canvas import Diagram
D = Diagram()

# Inputs and outputs are mixed across both ports: the map was reassigned during layout (2026-10) to suit the
# routing, replacing "port 0 = inputs, port 1 = outputs". Every pin has its own direction bit, so firmware
# must set direction per pin from this table. Do NOT drive P00, P01, P07, P10 or P11: they are inputs wired
# to open-drain outputs or a switch to GND.
# All P pins power up as inputs with ~100 k pull-ups: resets read high (run), LEDs are off
# (they sink into the pin), and TERMINATOR_EN_INVERTED_FIRMWARE leaves the DIP default alone.
pins = {
    1: ('INT', 'test point (firmware polls)'),
    2: ('A1', 'GND (addr 0x20)'),
    3: ('A2', 'GND'),
    4: ('P00', 'in: TERMPWR_EFUSE_FAULT_INVERTED (eFuse)'),
    5: ('P01', 'in: TERMPWR_EN_INVERTED (enable node)'),
    6: ('P02', 'out: LED_GREEN_INVERTED (spare LED)'),
    7: ('P03', 'out: LED_YELLOW_INVERTED (spare LED)'),
    8: ('P04', 'out: LED_RED_INVERTED (spare LED)'),
    9: ('P05', 'out: LED_ACTIVITY_INVERTED (red)'),
    10: ('P06', 'out: LED_STATUS_INVERTED (yellow)'),
    11: ('P07', 'in: BENCH_EFUSE_FAULT_INVERTED (eFuse)'),
    12: ('GND', 'GND'),
    13: ('P10', 'in: SD_CARD_DETECT (socket switch)'),
    14: ('P11', 'in: IS_BENCH_POWERED (TPS2116 ST, 1 = bench)'),
    15: ('P12', 'out/in: TERMINATOR_EN_INVERTED_FIRMWARE (DIP 2)'),
    16: ('P13', 'out: FT232H_RESET_INVERTED'),
    17: ('P14', 'out: HUB_RESET_INVERTED (Schottky)'),
    18: ('P15', 'spare, test pad'),
    19: ('P16', 'spare, test pad'),
    20: ('P17', 'spare, test pad'),
    21: ('A0', 'GND'),
    22: ('SCL', 'GPIO 43 (I2C1), 4.7k up'),
    23: ('SDA', 'GPIO 42 (I2C1), 4.7k up'),
    24: ('VCC', '3.3 V, 100 nF'),
}
D.chip2('exp', 0, 0, pins, title=["TCA9555PWR", "TSSOP-24, top view"], name='TCA9555')
