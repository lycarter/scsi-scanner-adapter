"""FT1248 1-bit master, bit-banged in MicroPython on the Pico 2 W. Slow on purpose (a few kHz):
this is for learning the protocol and reading it on a scope, not for speed.

Run from the Mac, in bench/ft1248:
    .venv/bin/mpremote run ft1248_bitbang.py            # prints status, drains the read buffer
    .venv/bin/mpremote mount . repl                      # then: from ft1248_bitbang import *

Protocol per FTDI AN_167 v1.1, Fig. 5.2/5.3 (1-bit) and section 8 (CPHA = 1), with the EEPROM set
to clock idle low, MSB first, flow control on:
  - SS_n high: the FT232H drives MIOSIO0 = TXE# (low: room to write) and MISO = RXF# (low: a
    byte is waiting). The master must not drive MIOSIO0.
  - SS_n low, then 7 command clocks on MIOSIO0: CMD3, 0, 0, CMD2, 0, CMD1, CMD0. The master
    starts driving only at the first clock edge.
  - 1 turnaround clock with MIOSIO0 released.
  - 8 clocks per byte, MSB first, for as long as SS_n stays low. MISO low = ACK, high = NAK
    (ACK polarity is our reading of the figures; confirmed or corrected by the first run).
  - The driving side changes MIOSIO0 on the rising edge; the receiving side samples on the
    falling edge.
"""
from machine import Pin
import time

# Pico GPIO = final-board GPIO - 22 (see README.md)
MISO = Pin(13, Pin.IN)
SS_N = Pin(14, Pin.IN)   # stays an input (FT232H pull-up holds it high) until init()
SCLK = Pin(15, Pin.IN)
D0 = Pin(16, Pin.IN)

CMD_WRITE, CMD_READ, CMD_FLUSH = 0x0, 0x1, 0x4
HALF_PERIOD_US = 100     # 5 kHz clock; raise for a slower scope sweep


def status():
    """Idle status lines as (can_write, can_read). Only meaningful while SS_n is high."""
    return (D0.value() == 0, MISO.value() == 0)


def init():
    """Check the FT232H is idling like an FT1248 slave, then take over SS_n and SCLK."""
    D0.init(Pin.IN)
    if SS_N.value() == 0 or D0.value() == 1 and MISO.value() == 1:
        # D0 high means either a full write buffer or a UART's idle TXD: don't drive into it
        print("warning: idle lines look odd (SS_n=%d D0=%d MISO=%d)"
              % (SS_N.value(), D0.value(), MISO.value()))
    SS_N.init(Pin.OUT, value=1)
    SCLK.init(Pin.OUT, value=0)


def _clock_out(bit):
    SCLK.value(1)
    D0.init(Pin.OUT, value=bit)   # drive only from the first rising edge onwards
    time.sleep_us(HALF_PERIOD_US)
    SCLK.value(0)                 # the FT232H samples here
    time.sleep_us(HALF_PERIOD_US)


def _clock_in():
    SCLK.value(1)                 # the FT232H shifts its next bit out here
    time.sleep_us(HALF_PERIOD_US)
    bit = D0.value()
    nak = MISO.value()
    SCLK.value(0)
    time.sleep_us(HALF_PERIOD_US)
    return bit, nak


def _command(cmd):
    SS_N.value(0)                 # the FT232H lets go of MIOSIO0
    time.sleep_us(HALF_PERIOD_US)
    for bit in ((cmd >> 3) & 1, 0, 0, (cmd >> 2) & 1, 0, (cmd >> 1) & 1, cmd & 1):
        _clock_out(bit)
    SCLK.value(1)                 # turnaround clock
    D0.init(Pin.IN)
    time.sleep_us(HALF_PERIOD_US)
    SCLK.value(0)
    time.sleep_us(HALF_PERIOD_US)


def _end():
    D0.init(Pin.IN)               # release before SS_n rises: the FT232H drives TXE# again
    SS_N.value(1)
    time.sleep_us(HALF_PERIOD_US)


def write(data):
    """Send bytes to the Mac. Returns how many the FT232H accepted (stops at the first NAK)."""
    _command(CMD_WRITE)
    sent = 0
    for byte in data:
        nak = 0
        for i in range(7, -1, -1):
            _clock_out((byte >> i) & 1)
            nak |= MISO.value()
        if nak:
            break
        sent += 1
    _end()
    return sent


def read(max_bytes=64):
    """Read bytes the Mac has sent. Stops at the first NAK (buffer empty)."""
    _command(CMD_READ)
    out = bytearray()
    for _ in range(max_bytes):
        byte = nak = 0
        for _ in range(8):
            bit, n = _clock_in()
            byte = (byte << 1) | bit
            nak |= n
        if nak:
            break
        out.append(byte)
    _end()
    return bytes(out)


def flush():
    """Ask the FT232H to send its write buffer to the Mac now (no latency-timer wait)."""
    _command(CMD_FLUSH)
    _end()


if __name__ == "__main__":
    print("before init: SS_n=%d D0=%d MISO=%d" % (SS_N.value(), D0.value(), MISO.value()))
    init()
    print("can_write, can_read =", status())
    got = read()
    print("read %d byte(s): %r" % (len(got), got))
    print("can_write, can_read =", status())
