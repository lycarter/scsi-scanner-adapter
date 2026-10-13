"""Slow bit-banged 4-bit FT1248 trace (MicroPython). Prints every clock of one read and one
write transaction so the wire format can be compared with AN_167 Fig. 5.8/5.9.
Before running, send two bytes from the Mac:  printf xy > /dev/cu.usbserial-BENCH1
Then on the Mac read what the Pico wrote:      the write below sends 0x41 0x5a ("AZ")."""
from machine import Pin
import time
MISO, SS, CLK = Pin(13, Pin.IN), Pin(14, Pin.IN), Pin(15, Pin.IN)
D = [Pin(16 + i, Pin.IN) for i in range(4)]
T = 100


def lines():
    return "".join(str(p.value()) for p in D) + " miso=%d" % MISO.value()


def drive(vals):          # vals[i] goes on MIOSIO[i]
    CLK.value(1)
    for p, v in zip(D, vals):
        p.init(Pin.OUT, value=v)
    time.sleep_us(T); CLK.value(0); time.sleep_us(T)


def release_clock():
    CLK.value(1)
    for p in D:
        p.init(Pin.IN)
    time.sleep_us(T); hi = lines(); CLK.value(0); time.sleep_us(T)
    return hi, lines()


def start(cmd):
    c3, c2, c1, c0 = (cmd >> 3) & 1, (cmd >> 2) & 1, (cmd >> 1) & 1, cmd & 1
    SS.value(0); time.sleep_us(T)
    print("  SS low:      MIO0..3=%s" % lines())
    drive((c3, 0, 0, c2))
    drive((0, c1, c0, 1))
    print("  turnaround:  hi %s | lo %s" % release_clock())


def stop():
    for p in D:
        p.init(Pin.IN)
    SS.value(1); time.sleep_us(T)
    print("  idle:        MIO0..3=%s" % lines())


print("idle:          MIO0..3=%s  (SS_n=%d)" % (lines(), SS.value()))
SS.init(Pin.OUT, value=1); CLK.init(Pin.OUT, value=0)
print("READ (cmd 1), three bytes' worth of clocks:")
start(1)
for i in range(6):
    print("  clock %d:     hi %s | lo %s" % ((i, ) + release_clock()))
stop()
print("WRITE (cmd 0) of 0x41 0x5a, MSB nibble first with B7 on MIO0:")
start(0)
for byte in (0x41, 0x5A):
    for nib in (byte >> 4, byte & 15):
        CLK.value(1)
        for i, p in enumerate(D):
            p.init(Pin.OUT, value=(nib >> (3 - i)) & 1)
        time.sleep_us(T); a = MISO.value(); CLK.value(0); time.sleep_us(T)
        print("  nibble %x:    miso hi %d | lo %d" % (nib, a, MISO.value()))
stop()
for p in (SS, CLK):
    p.init(Pin.IN)
