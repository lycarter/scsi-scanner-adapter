"""FT1248 1-bit master in PIO (MicroPython, Pico 2 W), fed by DMA so Python is not in the data
path. For speed tests driven from the Mac by speed_test.py.

Pins (Pico GPIO = final-board GPIO - 22): MISO 13 = JMP pin, SS_n 14 + SCLK 15 = side-set
(bit 0 = SS_n, bit 1 = SCLK), MIOSIO0 16 = out/set/in pin.

One bit = H state-machine cycles with SCLK high, then L cycles low; SCLK = sm_freq / (H + L).
The master drives on the rising edge. It samples MIOSIO0 on the *next* rising edge (the latest
safe moment: the FT232H only changes the line after that edge) and tests MISO for ACK/NAK at
the end of the first clock of each byte, which is the only clock on which it is valid.
On a NAK the program raises SS_n, waits for the idle status line, and starts a new transaction
with the same byte, so back-pressure from USB never loses data.

The read and write programs do not fit in one 32-instruction PIO block together (21 + 28), so
only one is loaded at a time.
"""
import machine
import rp2
import time
from machine import Pin

PIO0_BASE = 0x50200000
TXF0, RXF0 = PIO0_BASE + 0x10, PIO0_BASE + 0x20
DREQ_PIO0_TX0, DREQ_PIO0_RX0 = 0, 4


def make_read(H, L):
    # side-set values (locals: module globals are not visible inside an asm_pio function)
    IDLE, LOW, HIGH = 1, 0, 2   # SS_n high / active with clock low / clock high
    @rp2.asm_pio(sideset_init=(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_LOW), set_init=rp2.PIO.IN_HIGH,
                 in_shiftdir=rp2.PIO.SHIFT_LEFT, autopush=True, push_thresh=8)
    def prog():
        wrap_target()
        pull()                  .side(IDLE)            # byte count - 1
        mov(y, osr)             .side(IDLE)
        label("start")
        wait(0, gpio, 13)       .side(IDLE)   [3]      # RXF# low: something to read
        set(pins, 0)            .side(LOW)    [3]      # SS_n low; FT232H releases MIOSIO0
        set(x, 4)               .side(LOW)
        set(pindirs, 1)         .side(HIGH)   [H - 1]  # command clock 1: CMD3 = 0
        nop()                   .side(LOW)    [L - 1]
        label("cmd")
        nop()                   .side(HIGH)   [H - 1]  # clocks 2-6: 0, 0, CMD2, 0, CMD1 = 0
        jmp(x_dec, "cmd")       .side(LOW)    [L - 1]
        set(pins, 1)            .side(HIGH)   [H - 1]  # clock 7: CMD0 = 1 (read)
        nop()                   .side(LOW)    [L - 1]
        set(pindirs, 0)         .side(HIGH)   [H - 1]  # turnaround clock: release MIOSIO0
        nop()                   .side(LOW)    [L - 1]
        label("byte")
        nop()                   .side(HIGH)   [H - 1]  # clock 1 of a byte: FT232H drives B7 + ACK
        set(x, 6)               .side(LOW)    [L - 2]
        jmp(pin, "nak")         .side(LOW)             # MISO high = NAK (buffer empty)
        label("bit")
        in_(pins, 1)            .side(HIGH)   [H - 1]  # sample the previous bit, clock the next
        jmp(x_dec, "bit")       .side(LOW)    [L - 1]
        in_(pins, 1)            .side(LOW)             # B0; autopush
        jmp(y_dec, "byte")      .side(LOW)
        wrap()
        label("nak")
        jmp("start")            .side(IDLE)   [7]
    return prog


def make_write(H, L):
    # side-set values (locals: module globals are not visible inside an asm_pio function)
    IDLE, LOW, HIGH = 1, 0, 2   # SS_n high / active with clock low / clock high
    @rp2.asm_pio(sideset_init=(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_LOW), set_init=rp2.PIO.IN_HIGH,
                 out_init=rp2.PIO.IN_HIGH, out_shiftdir=rp2.PIO.SHIFT_LEFT)
    def prog():
        wrap_target()
        pull()                  .side(IDLE)            # byte count - 1
        mov(y, osr)             .side(IDLE)
        pull()                  .side(IDLE)            # first byte, in bits 31..24
        label("start")
        mov(isr, osr)           .side(IDLE)            # keep a copy for a retry after NAK
        wait(0, pin, 0)         .side(IDLE)   [3]      # TXE# low on MIOSIO0: room to write
        set(pins, 0)            .side(LOW)    [3]      # SS_n low
        set(x, 5)               .side(LOW)
        set(pindirs, 1)         .side(HIGH)   [H - 1]  # 7 command clocks, all 0 = write
        nop()                   .side(LOW)    [L - 1]
        label("cmd")
        nop()                   .side(HIGH)   [H - 1]
        jmp(x_dec, "cmd")       .side(LOW)    [L - 1]
        set(pindirs, 0)         .side(HIGH)   [H - 1]  # turnaround clock
        nop()                   .side(LOW)    [L - 1]
        label("byte")
        out(pins, 1)            .side(LOW)             # preload B7 (not driven yet)
        set(pindirs, 1)         .side(HIGH)   [H - 1]  # clock 1: drive B7
        set(x, 6)               .side(LOW)    [L - 2]
        jmp(pin, "nak")         .side(LOW)             # MISO high = NAK (buffer full)
        label("bit")
        out(pins, 1)            .side(HIGH)   [H - 1]
        jmp(x_dec, "bit")       .side(LOW)    [L - 1]
        set(pindirs, 0)         .side(LOW)             # release between bytes and at the end
        jmp(y_dec, "next")      .side(LOW)
        push()                  .side(IDLE)            # all bytes sent: tell the CPU
        wrap()
        label("next")
        pull()                  .side(LOW)             # clock stretches here if the FIFO is empty
        mov(isr, osr)           .side(LOW)
        jmp("byte")             .side(LOW)
        label("nak")
        set(pindirs, 0)         .side(LOW)
        mov(osr, isr)           .side(IDLE)   [7]
        jmp("start")            .side(IDLE)
    return prog


def pattern(n):
    buf = bytearray(n)
    for i in range(n):
        buf[i] = (i * 167 + (i >> 8) * 31 + 13) & 0xFF
    return buf


SYNC_BYPASS = False   # True: skip the 2-flop input synchroniser on MISO and MIOSIO0 (~2 cycles earlier data)


def _sm(prog, freq):
    rp2.PIO(0).remove_program()
    machine.mem32[PIO0_BASE + 0x38] = (1 << 13 | 1 << 16) if SYNC_BYPASS else 0
    return rp2.StateMachine(0, prog, freq=freq, sideset_base=Pin(14), set_base=Pin(16),
                            out_base=Pin(16), in_base=Pin(16), jmp_pin=Pin(13))


def _idle_ok():
    ss, d0 = Pin(14, Pin.IN), Pin(16, Pin.IN)
    return ss.value() == 1 or d0.value() == 0


def drain():
    """Throw away whatever the Mac has already sent (left over from a failed run). Returns the
    byte count. Slow clock, so it works even when the fast settings do not."""
    global SYNC_BYPASS
    keep, SYNC_BYPASS = SYNC_BYPASS, False
    sm = _sm(make_read(4, 4), 8_000_000)
    SYNC_BYPASS = keep
    miso = Pin(13, Pin.IN)
    sm.active(1)
    sm.put(0xFFFFFFFF)
    n, quiet = 0, time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), quiet) < 50:
        while sm.rx_fifo():
            sm.get(); n += 1; quiet = time.ticks_ms()
        if miso.value() == 0:
            quiet = time.ticks_ms()
    sm.active(0)
    Pin(16, Pin.IN); Pin(14, Pin.IN); Pin(15, Pin.IN)
    return n


def tx_test(n, freq=1_000_000, H=4, L=4, chunk=32768, timeout_ms=30000):
    """Send n pattern bytes to the Mac. Prints 'TX n_sent elapsed_us'."""
    buf = pattern(chunk)
    sm = _sm(make_write(H, L), freq)
    dma = rp2.DMA()
    ctrl = dma.pack_ctrl(size=0, inc_read=True, inc_write=False, treq_sel=DREQ_PIO0_TX0)
    sm.active(1)
    t0 = time.ticks_us()
    sm.put(n - 1)
    sent = 0
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    while sent < n:
        count = min(chunk, n - sent)
        dma.config(read=buf, write=TXF0, count=count, ctrl=ctrl, trigger=True)
        while dma.active():
            if time.ticks_diff(deadline, time.ticks_ms()) < 0:
                break
        sent += count - dma.count
        if dma.active():
            break
    while sent == n and sm.rx_fifo() == 0 and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        pass
    t1 = time.ticks_us()
    done = sm.rx_fifo() > 0
    sm.active(0)
    dma.close()
    Pin(16, Pin.IN); Pin(14, Pin.IN); Pin(15, Pin.IN)
    print("TX", sent if done else -sent, time.ticks_diff(t1, t0))


def rx_test(n, freq=1_000_000, H=4, L=4, timeout_ms=30000):
    """Receive n pattern bytes from the Mac. Prints 'READY', then 'RX n_got n_bad elapsed_us'
    (elapsed from the first byte's arrival, polled, so good to about 1 ms)."""
    want = pattern(n)
    buf = bytearray(n)
    stale = drain()
    if stale:
        print("drained", stale, "stale bytes")
    sm = _sm(make_read(H, L), freq)
    dma = rp2.DMA()
    ctrl = dma.pack_ctrl(size=0, inc_read=False, inc_write=True, treq_sel=DREQ_PIO0_RX0)
    dma.config(read=RXF0, write=buf, count=n, ctrl=ctrl, trigger=True)
    sm.active(1)
    sm.put(n - 1)
    print("READY")
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    t0 = None
    while dma.active() and time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if t0 is None and dma.count != n:
            t0 = time.ticks_us()
    t1 = time.ticks_us()
    got = n - dma.count
    sm.active(0)
    dma.close()
    Pin(16, Pin.IN); Pin(14, Pin.IN); Pin(15, Pin.IN)
    bad = sum(1 for i in range(got) if buf[i] != want[i])
    first_bad = next((i for i in range(got) if buf[i] != want[i]), -1)
    print("RX", got, bad, time.ticks_diff(t1, t0) if t0 is not None else -1, first_bad)
