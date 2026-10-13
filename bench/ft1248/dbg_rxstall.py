# Debug: receive 8192 bytes in two DMA transfers with a deliberate pause between them, and
# show where the data first differs. Run via sustained-style harness: prints READY first.
import pio4_ft1248 as p, rp2, time
N = 8192
want = bytearray(N); p.fill_random(want, N // 4, 0)
keep = bytearray(N)
p.drain()
sm = p._sm(p.make_read4(4, 4), 8_000_000)
d = rp2.DMA()
ctrl = d.pack_ctrl(size=0, inc_read=False, inc_write=True, treq_sel=p.DREQ_PIO0_RX0)
mv = memoryview(keep)
d.config(read=p.RXF0 + 3, write=mv[:4096], count=4096, ctrl=ctrl, trigger=True)
sm.active(1); sm.put(N - 1)
print("READY")
while d.active(): pass
time.sleep_ms(20)
d.config(read=p.RXF0 + 3, write=mv[4096:], count=4096, ctrl=ctrl, trigger=True)
t = time.ticks_ms()
while d.active() and time.ticks_diff(time.ticks_ms(), t) < 3000: pass
sm.active(0); p._release()
bad = [i for i in range(N) if keep[i] != want[i]]
print("got", N - d.count, "bad", len(bad), "first", bad[:1])
if bad:
    i = bad[0]
    print("want", bytes(want[i-4:i+12]).hex()); print("got ", bytes(keep[i-4:i+12]).hex())
