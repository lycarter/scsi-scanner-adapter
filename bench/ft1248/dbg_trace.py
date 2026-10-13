from ft1248_bitbang import *
import ft1248_bitbang as f
init()
print("idle", status())
SS_N.value(0); time.sleep_us(100)
print("after SS low: D0=%d MISO=%d" % (D0.value(), MISO.value()))
tr = []
for bit in (0, 0, 0, 0, 0, 0, 1):
    SCLK.value(1); D0.init(Pin.OUT, value=bit); time.sleep_us(100)
    m1 = MISO.value(); SCLK.value(0); time.sleep_us(100); tr.append((bit, m1, MISO.value()))
print("cmd (bit, miso@hi, miso@lo):", tr)
SCLK.value(1); D0.init(Pin.IN); time.sleep_us(100); a = (D0.value(), MISO.value())
SCLK.value(0); time.sleep_us(100); print("turnaround hi:", a, "lo:", (D0.value(), MISO.value()))
tr = []
for i in range(32):
    SCLK.value(1); time.sleep_us(100); a = (D0.value(), MISO.value())
    SCLK.value(0); time.sleep_us(100); tr.append((a, (D0.value(), MISO.value())))
    if i % 8 == 7:
        print("byte %d (d0,miso)@hi/(d0,miso)@lo:" % (i // 8), tr); tr = []
SS_N.value(1); time.sleep_us(100); print("idle", status())
