"""FT1248 4-bit master in PIO (MicroPython, Pico 2 W) with a CPU-free sustained test.
Driven from the Mac by sustained4_test.py. Needs the EEPROM set to **LSB first** (see README):
then MIOSIO[i] carries bit i, low nibble on the first clock, which is exactly what PIO's
`in pins, 4` / `out pins, 4` with right shifts produce. (MSB-first puts B7 on MIOSIO0, i.e.
each nibble bit-reversed relative to the GPIO order.)

Pins: MISO 13 = JMP pin, SS_n 14 + SCLK 15 = side-set, MIOSIO0-3 = GPIO 16-19.
Wire format (AN_167 Fig. 5.8/5.9, confirmed with dbg_trace4.py):
  clock 1: MIOSIO0 = CMD3, 1 = 0, 2 = 0 (this low selects 4-bit), 3 = CMD2
  clock 2: MIOSIO0 = 0, 1 = CMD1, 2 = CMD0, 3 = don't care
  clock 3: turnaround, lines released
  then 2 clocks per byte; MISO low on the FIRST clock of a byte = ACK, high = NAK.
One clock = H cycles high + L cycles low (H >= 3 to read, >= 2 to write; L >= 2);
SCLK = sm_freq / (H + L).

Trap found the hard way: an `in` with autopush that stalls on a full RX FIFO still applies its
side-set at once but takes its sample when the stall ends. If that `in` also raises the clock,
the FT232H has moved on by then and the nibble is wrong (one bad byte per stall). So the read
program samples with a plain `in` and uses a separate blocking `push`.
"""
import machine
import micropython
import rp2
import time
from machine import Pin

PIO0_BASE = 0x50200000
TXF0, RXF0 = PIO0_BASE + 0x10, PIO0_BASE + 0x20
DREQ_PIO0_TX0, DREQ_PIO0_RX0 = 0, 4
DMA_BASE = 0x50000000
SNIFF_CTRL, SNIFF_DATA = DMA_BASE + 0x454, DMA_BASE + 0x458   # RP2350 offsets (16 channels)
SYNC_BYPASS = True      # skip the 2-flop input synchroniser on MISO and MIOSIO0-3
BLOCK = 131072


def make_read4(H, L):
    IDLE, LOW, HIGH = 1, 0, 2   # side-set: SS_n high / active, clock low / clock high
    @rp2.asm_pio(sideset_init=(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_LOW), set_init=(rp2.PIO.IN_HIGH,) * 4,
                 in_shiftdir=rp2.PIO.SHIFT_RIGHT)
    def prog():
        wrap_target()
        pull()                  .side(IDLE)            # byte count - 1
        mov(y, osr)             .side(IDLE)
        label("start")
        wait(0, gpio, 13)       .side(IDLE)   [3]      # RXF# low: something to read
        set(pins, 0)            .side(LOW)    [3]      # SS_n low; FT232H releases MIOSIO0
        set(pindirs, 15)        .side(HIGH)   [H - 1]  # clock 1: 0000 (CMD3 = CMD2 = 0, 4-bit)
        nop()                   .side(LOW)    [L - 1]
        set(pins, 12)           .side(HIGH)   [H - 1]  # clock 2: CMD1 = 0, CMD0 = 1 (read)
        nop()                   .side(LOW)    [L - 1]
        set(pindirs, 0)         .side(HIGH)   [H - 1]  # clock 3: turnaround
        nop()                   .side(LOW)    [L - 1]
        nop()                   .side(HIGH)   [H - 1]  # byte clock A: low nibble + ACK appear
        label("loop")
        nop()                   .side(LOW)    [L - 2]
        jmp(pin, "nak")         .side(LOW)             # MISO high at the end of clock A = NAK
        in_(pins, 4)            .side(HIGH)   [H - 1]  # clock B rises; take the low nibble
        jmp(y_dec, "more")      .side(LOW)    [L - 1]
        in_(pins, 4)            .side(LOW)             # last byte: take its high nibble
        push()                  .side(LOW)
        wrap()
        label("more")
        in_(pins, 4)            .side(HIGH)            # next clock A rises; take the high nibble
        push()                  .side(HIGH)   [H - 3]  # may stall here, AFTER the sample (see note)
        jmp("loop")             .side(HIGH)
        label("nak")
        jmp("start")            .side(IDLE)   [7]
    return prog


def make_write4(H, L):
    IDLE, LOW, HIGH = 1, 0, 2
    @rp2.asm_pio(sideset_init=(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_LOW), set_init=(rp2.PIO.IN_HIGH,) * 4,
                 out_init=(rp2.PIO.IN_HIGH,) * 4, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
    def prog():
        wrap_target()
        pull()                  .side(IDLE)            # byte count - 1
        mov(y, osr)             .side(IDLE)
        pull()                  .side(IDLE)            # first byte, in bits 7..0
        label("start")
        mov(isr, osr)           .side(IDLE)            # keep a copy for a retry after NAK
        wait(0, pin, 0)         .side(IDLE)   [3]      # TXE# low on MIOSIO0: room to write
        set(pins, 0)            .side(LOW)    [3]      # SS_n low
        set(pindirs, 15)        .side(HIGH)   [H - 1]  # clock 1: 0000
        nop()                   .side(LOW)    [L - 1]
        set(pins, 8)            .side(HIGH)   [H - 1]  # clock 2: CMD1 = CMD0 = 0 (write)
        nop()                   .side(LOW)    [L - 1]
        set(pindirs, 0)         .side(HIGH)   [H - 1]  # clock 3: turnaround
        out(pins, 4)            .side(LOW)    [L - 1]  # preload the low nibble (not driven yet)
        set(pindirs, 15)        .side(HIGH)   [H - 2]  # byte clock A: drive it
        jmp("ack")              .side(HIGH)
        label("loop")
        out(pins, 4)            .side(HIGH)   [H - 1]  # clock A of later bytes: low nibble
        label("ack")
        nop()                   .side(LOW)    [L - 2]
        jmp(pin, "nak")         .side(LOW)             # MISO high at the end of clock A = NAK
        out(pins, 4)            .side(HIGH)            # clock B: high nibble
        jmp(y_dec, "more")      .side(HIGH)
        nop()                   .side(LOW)    [L - 1]  # last byte
        set(pindirs, 0)         .side(LOW)
        push()                  .side(IDLE)            # tell the CPU we are done
        wrap()
        label("more")
        pull()                  .side(HIGH)            # next byte (clock stretches high if empty)
        mov(isr, osr)           .side(HIGH)
        jmp("loop")             .side(LOW)    [L - 1]
        label("nak")
        set(pindirs, 0)         .side(LOW)
        mov(osr, isr)           .side(IDLE)   [7]
        jmp("start")            .side(IDLE)
    return prog


def make_flush4(H, L):
    IDLE, LOW, HIGH = 1, 0, 2
    @rp2.asm_pio(sideset_init=(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_LOW), set_init=(rp2.PIO.IN_HIGH,) * 4)
    def prog():
        wrap_target()
        pull()                  .side(IDLE)            # any word: send one flush command (0x4)
        set(pins, 8)            .side(LOW)    [3]      # SS_n low; preload CMD2 = 1 on MIOSIO3
        set(pindirs, 15)        .side(HIGH)   [H - 1]  # clock 1: CMD3 = 0, 0, 0, CMD2 = 1
        nop()                   .side(LOW)    [L - 1]
        nop()                   .side(HIGH)   [H - 1]  # clock 2: 0, CMD1 = 0, CMD0 = 0, x
        nop()                   .side(LOW)    [L - 1]
        set(pindirs, 0)         .side(HIGH)   [H - 1]  # clock 3: turnaround
        nop()                   .side(LOW)    [L - 1]
        push()                  .side(IDLE)
        wrap()
    return prog


IO_BANK0 = 0x40028000


def _select(funcsel):
    """Hand the six FT1248 pins to one PIO block (funcsel 6 = PIO0, 7 = PIO1, 8 = PIO2)."""
    for g in (14, 15, 16, 17, 18, 19):
        machine.mem32[IO_BANK0 + 4 + 8 * g] = funcsel


def echo(count, size=10, flush=True, H=3, L=2):
    """Latency test: read `size` bytes from the Mac, write them straight back, `count` times.
    Read, write and flush programs live in PIO0, PIO1 and PIO2 (they do not fit in one block)
    and the pins are switched between them. Prints 'READY' then
    'ECHO count mean_turnaround_us' (time from last byte read to reply + flush finished)."""
    import gc
    gc.collect()
    freq = machine.freq()
    for i in range(3):
        rp2.PIO(i).remove_program()
        machine.mem32[PIO0_BASE + 0x100000 * i + 0x38] = (1 << 13 | 0xF << 16)
    kw = dict(freq=freq, sideset_base=Pin(14), set_base=Pin(16), out_base=Pin(16), in_base=Pin(16), jmp_pin=Pin(13))
    sm_r = rp2.StateMachine(0, make_read4(H, L), **kw)
    sm_w = rp2.StateMachine(4, make_write4(H, L), **kw)
    sm_f = rp2.StateMachine(8, make_flush4(H, L), **kw)
    for sm in (sm_r, sm_w, sm_f):
        sm.active(1)
    _select(6)
    print("READY")
    total = 0
    for _ in range(count):
        sm_r.put(size - 1)
        buf = [sm_r.get() >> 24 for _ in range(size)]
        t = time.ticks_us()
        _select(7)
        sm_w.put(size - 1)
        for b in buf:
            sm_w.put(b)
        sm_w.get()
        if flush:
            _select(8)
            sm_f.put(0)
            sm_f.get()
        _select(6)
        total += time.ticks_diff(time.ticks_us(), t)
    for sm in (sm_r, sm_w, sm_f):
        sm.active(0)
    _release()
    print("ECHO", count, total // count)


@micropython.viper
def fill_random(buf, nwords: int, start: int):
    """buf = MurmurHash3-finaliser(start), (start + 1), ... as little-endian 32-bit words."""
    p = ptr32(buf)
    hi1 = 0x85EB                 # built at run time: viper cannot load a literal above 2**30
    hi2 = 0xC2B2
    c1 = (hi1 << 16) | 0xCA6B
    c2 = (hi2 << 16) | 0xAE35
    for i in range(nwords):
        h = start + i
        h ^= (h >> 16) & 0xFFFF
        h = h * c1
        h ^= (h >> 13) & 0x7FFFF
        h = h * c2
        h ^= (h >> 16) & 0xFFFF
        p[i] = h


def _sm(prog, freq):
    rp2.PIO(0).remove_program()
    machine.mem32[PIO0_BASE + 0x38] = (1 << 13 | 0xF << 16) if SYNC_BYPASS else 0
    return rp2.StateMachine(0, prog, freq=freq, sideset_base=Pin(14), set_base=Pin(16),
                            out_base=Pin(16), in_base=Pin(16), jmp_pin=Pin(13))


def _release():
    for g in (14, 15, 16, 17, 18, 19):
        Pin(g, Pin.IN)


def _sniff_start(dma):
    """Hardware CRC-32 (zlib-compatible) over every byte this DMA channel moves."""
    machine.mem32[SNIFF_DATA] = 0xFFFFFFFF
    machine.mem32[SNIFF_CTRL] = 1 | dma.channel << 1 | 1 << 5 | 1 << 10 | 1 << 11


def _sniff_result():
    return machine.mem32[SNIFF_DATA] & 0xFFFFFFFF


def sniff_selftest():
    """Check the DMA sniffer against binascii.crc32 on a memory-to-memory copy."""
    import binascii
    src = bytearray(4096); fill_random(src, 1024, 7)
    dst = bytearray(4096)
    dma = rp2.DMA()
    _sniff_start(dma)
    for _ in range(2):   # two transfers: the CRC must carry across them
        dma.config(read=src, write=dst, count=4096, trigger=True,
                   ctrl=dma.pack_ctrl(size=0, sniff_en=1))
        while dma.active():
            pass
    got, want = _sniff_result(), binascii.crc32(src, binascii.crc32(src))
    dma.close()
    print("SNIFF %08x %08x %s" % (got, want, got == want and dst == src))


def drain():
    """Discard anything the Mac already sent. Slow clock, so it always works."""
    sm = _sm(make_read4(4, 4), 8_000_000)
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
    _release()
    return n


def tx_sustained(n, freq=150_000_000, H=3, L=2, stall_ms=5000):
    """Pico -> Mac, n bytes (a multiple of BLOCK), no per-byte CPU work.
    Two BLOCK-sized pseudorandom buffers are generated up front and played alternately by DMA;
    pass p uses buffer p & 1 with its first 4 bytes replaced by p (little-endian), written
    while the other buffer is on the wire. The DMA sniffer keeps the running CRC-32.
    Prints 'TXS n_sent elapsed_us crc32 max_gap_us'."""
    import gc
    gc.collect()
    bufs = (bytearray(BLOCK), bytearray(BLOCK))
    fill_random(bufs[0], BLOCK // 4, 0)
    fill_random(bufs[1], BLOCK // 4, BLOCK // 4)
    stamps = (memoryview(bufs[0])[0:4], memoryview(bufs[1])[0:4])
    stamps[0][:] = (0).to_bytes(4, "little")
    stamps[1][:] = (1).to_bytes(4, "little")
    sm = _sm(make_write4(H, L), freq)
    dma = rp2.DMA()
    ctrl = dma.pack_ctrl(size=0, inc_read=True, inc_write=False, treq_sel=DREQ_PIO0_TX0, sniff_en=1)
    _sniff_start(dma)
    passes = n // BLOCK
    sm.active(1)
    t0 = time.ticks_us()
    sm.put(n - 1)
    sent, ok, max_gap = 0, True, 0
    g0 = time.ticks_us()
    for p in range(passes):
        dma.config(read=bufs[p & 1], write=TXF0, count=BLOCK, ctrl=ctrl, trigger=True)
        max_gap = max(max_gap, time.ticks_diff(time.ticks_us(), g0)) if p else 0
        if p + 1 < passes and p >= 1:
            stamps[(p + 1) & 1][:] = (p + 1).to_bytes(4, "little")
        last, since = BLOCK, time.ticks_ms()
        while dma.active():
            c = dma.count
            if c != last:
                last, since = c, time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), since) > stall_ms:
                ok = False
                break
        g0 = time.ticks_us()
        sent += BLOCK - dma.count
        if not ok:
            break
    since = time.ticks_ms()
    while ok and sm.rx_fifo() == 0 and time.ticks_diff(time.ticks_ms(), since) < stall_ms:
        pass
    t1 = time.ticks_us()
    ok = ok and sm.rx_fifo() > 0
    sm.active(0)
    crc = _sniff_result()
    dma.close()
    _release()
    print("TXS", sent if ok else -sent, time.ticks_diff(t1, t0), "%08x" % crc, max_gap)


RXBLOCK = 65536


def rx_sustained(n, freq=150_000_000, H=3, L=2, stall_ms=5000):
    """Mac -> Pico, n bytes (a multiple of RXBLOCK), verified bytewise at full speed.
    The Mac sends one pseudorandom RXBLOCK over and over, each pass stamped with its number in
    the first 4 bytes. DMA drops pass p into buffer p & 1; while the next pass arrives, the CPU
    checks the stamp and compares the whole block (one memcmp). The sniffer CRCs everything.
    Prints 'READY stale' then 'RXS n_got elapsed_us crc32 bad_blocks first_bad_block max_gap_us'."""
    import gc
    gc.collect()
    want = bytearray(RXBLOCK)
    fill_random(want, RXBLOCK // 4, 0)
    keeps = (bytearray(RXBLOCK), bytearray(RXBLOCK))
    head = bytes(want[0:4])
    stale = drain()
    sm = _sm(make_read4(H, L), freq)
    dma = rp2.DMA()
    _sniff_start(dma)
    ctrl = dma.pack_ctrl(size=0, inc_read=False, inc_write=True, treq_sel=DREQ_PIO0_RX0, sniff_en=1)
    rx_top = RXF0 + 3            # right-shifted bytes land in bits 31..24 of the FIFO word
    passes = n // RXBLOCK
    dma.config(read=rx_top, write=keeps[0], count=RXBLOCK, ctrl=ctrl, trigger=True)
    sm.active(1)
    sm.put(n - 1)
    print("READY", stale)
    got, t0, ok, bad_blocks, first_bad, max_gap = 0, None, True, 0, -1, 0
    for p in range(passes):
        last, since = RXBLOCK, time.ticks_ms()
        while dma.active():
            c = dma.count
            if c != last:
                if t0 is None:
                    t0 = time.ticks_us()
                last, since = c, time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), since) > (stall_ms if t0 else 20000):
                ok = False
                break
        g0 = time.ticks_us()
        got += RXBLOCK - dma.count
        if not ok:
            break
        if p + 1 < passes:
            dma.config(read=rx_top, write=keeps[(p + 1) & 1], count=RXBLOCK, ctrl=ctrl, trigger=True)
            max_gap = max(max_gap, time.ticks_diff(time.ticks_us(), g0))
        k = keeps[p & 1]
        stamp_ok = int.from_bytes(k[0:4], "little") == p
        k[0:4] = head
        if not (stamp_ok and k == want):
            bad_blocks += 1
            if first_bad < 0:
                first_bad = p
                i = 0 if not stamp_ok else next(j for j in range(RXBLOCK) if k[j] != want[j])
                detail = (i, bytes(want[i:i + 8]), bytes(k[i:i + 8]), stamp_ok)
    t1 = time.ticks_us()
    sm.active(0)
    crc = _sniff_result()
    dma.close()
    _release()
    print("RXS", got, time.ticks_diff(t1, t0) if t0 else -1, "%08x" % crc, bad_blocks, first_bad, max_gap)
    if bad_blocks:
        print("first bad block: offset %d want %s got %s stamp_ok %s" % (detail[0], detail[1].hex(), detail[2].hex(), detail[3]))
