"""Loop Pico -> Mac captures on one serial node; when the stream stalls, diagnose in place.
   expB.py NODE MINUTES MODE     MODE: peek | flush | reopen | wait"""
import fcntl, json, os, select, struct, subprocess, sys, termios, threading, time
import numpy as np, serial
import sustained4_test as t
NODE, MINUTES, MODE = sys.argv[1], float(sys.argv[2]), sys.argv[3]
N = int(os.environ.get("MB", "128")) << 20
OUT = os.environ.get("CHASE_OUT", "/tmp")
FREQ = int(os.environ.get("PIO_HZ", "150000000"))   # SCLK = PIO_HZ / 5; byte rate = SCLK / 2 at most
want = t.tx_reference(N)
wn = np.frombuffer(want, np.uint8)
def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)
def check(got):
    m = min(len(got), N)
    bad = np.flatnonzero(np.frombuffer(bytes(got[:m]), np.uint8) != wn[:m])
    return {"received": len(got), "extra": len(got) - N, "wrong": int(len(bad)),
            "first_wrong": int(bad[0]) if len(bad) else None,
            "leading_zeros": len(got) - len(bytes(got).lstrip(b"\0"))}
def inq(fd):
    return struct.unpack("i", fcntl.ioctl(fd, termios.FIONREAD, b"\0\0\0\0"))[0]
def pump(fd, got, secs):
    end, n0 = time.time() + secs, len(got)
    while time.time() < end:
        if select.select([fd], [], [], 0.1)[0]:
            got.extend(os.read(fd, 1 << 20))
    return len(got) - n0
def where(payload, near):
    """offset in the reference stream of this payload, searching forward from `near`"""
    if len(payload) < 32: return None
    p = want.find(bytes(payload[:32]), max(0, near - 4096))
    return p
def usb_peek():
    import usb.core
    dev = usb.core.find(idVendor=0x0403, idProduct=0x6014)
    out = []
    for _ in range(4):
        try: raw = bytes(dev.read(0x81, 16384, 300))
        except Exception as e: out.append(repr(e)[:60]); continue
        pay = b"".join(raw[i + 2:i + 512] for i in range(0, len(raw), 512))
        out.append((len(raw), raw[:2].hex(), pay))
    import usb.util; usb.util.dispose_resources(dev)
    return out
def after(g, at, i):
    """Describe what arrived after the receive path was revived, against the reference."""
    name = "%s/after-%d-%d.bin" % (OUT, os.getpid(), i)
    open(name, "wb").write(g)
    # the tail of g must be the tail of the stream if nothing was lost after the restart
    tail_ok = len(g) >= 4096 and bytes(g[-4096:]) == want[N - 4096:]
    log("  after the restart: %d bytes; stream had %d left at the stall, so net %d missing; ends with the true end of stream: %s; saved %s"
        % (len(g), N - at, N - at - len(g), tail_ok, name))
def one(i):
    port = serial.Serial(NODE, 3000000, timeout=0.5); port.reset_input_buffer()
    fd, got = port.fd, bytearray()
    proc = t.pico("p.tx_sustained(%d, freq=%d, H=3, L=2, stall_ms=90000)" % (N, FREQ))
    last, stalled = time.time(), False
    while len(got) < N + (1 << 20):
        if select.select([fd], [], [], 0.25)[0]:
            d = os.read(fd, 1 << 20)
            if d: got.extend(d); last = time.time()
        if proc.poll() is not None and time.time() - last > 1.5: break
        if time.time() - last > (2.5 if got else 15) and proc.poll() is None:
            stalled = True; break
    if not stalled:
        out = proc.communicate()[0]; port.close()
        r = check(got); r["pico"] = out.strip()[-80:]
        ok = r["wrong"] == 0 and r["extra"] == 0
        if not ok: open("%s/bad-%d-%d.bin" % (os.path.dirname(__file__), os.getpid(), i), "wb").write(got)
        log("run", i, "OK" if ok else "BAD", json.dumps(r)); return ok
    at = len(got)
    log("run", i, "STALL at", at, check(got), "FIONREAD", inq(fd), "mode", MODE)
    log("  waited 3 s more: +%d" % pump(fd, got, 3), "FIONREAD", inq(fd))
    if MODE == "nudge":
        # least destructive first; the Pico keeps offering data for 90 s, so anything that
        # un-sticks the receive path shows up as bytes arriving
        def second_open():
            fd2 = os.open(NODE, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            try: return pump(fd2, got, 2)
            finally: os.close(fd2)
        def set_speed():
            fcntl.ioctl(fd, 0x80085402, struct.pack("L", 3000000))      # IOSSIOSPEED
        nudges = [("TIOCMGET", lambda: fcntl.ioctl(fd, termios.TIOCMGET, b"\0\0\0\0")),
                  ("tcflow TCION", lambda: termios.tcflow(fd, termios.TCION)),
                  ("write one byte", lambda: (os.write(fd, b"\0"), None)[1]),
                  ("second open of the node", second_open),
                  ("IOSSIOSPEED 3000000 again", set_speed)]
        resumed = False
        for name, fn in nudges:
            try: extra = fn()
            except Exception as e: log("  nudge", name, "failed", repr(e)); continue
            gain = pump(fd, got, 3) + (extra if isinstance(extra, int) else 0)
            log("  nudge %-26s -> +%d in 3 s, FIONREAD %d" % (name, gain, inq(fd)))
            if gain:
                while len(got) < N and pump(fd, got, 2): pass
                log("  RESUMED by", name, "; whole transfer now:", json.dumps(check(got))); resumed = True
                break
        log("  driver processes:", subprocess.run("ps -axo pid,lstart,command | grep -E 'AppleUSBFTDI|ftdi.vcp' | grep -v grep | cut -c1-40",
                                               shell=True, capture_output=True, text=True).stdout.replace("\n", " | "))
        if not resumed:
            termios.tcflush(fd, termios.TCIFLUSH)
            g = bytearray(); gain = pump(fd, g, 4)
            log("  tcflush(TCIFLUSH)              -> +%d in 4 s" % gain)
            if not gain:
                port.close(); time.sleep(0.5)
                port = serial.Serial(NODE, 3000000, timeout=0.5); fd = port.fd
                gain = pump(fd, g, 4)
                log("  close + reopen (no flush call) -> +%d in 4 s" % gain)
            while gain and pump(fd, g, 2): pass
            after(g, at, i)
    if MODE == "wait":
        log("  waited 20 s more: +%d" % pump(fd, got, 20))
    if MODE == "flush":
        termios.tcflush(fd, termios.TCIFLUSH)
        g = bytearray(); log("  after tcflush(TCIFLUSH), 5 s: +%d" % pump(fd, g, 5))
        log("   flushed-then-received begins at stream offset", where(g, at), "len", len(g), "zeros", len(g) - len(bytes(g).lstrip(b"\0")))
        got2 = g
    if MODE == "reopen":
        port.close(); time.sleep(0.5)
        port = serial.Serial(NODE, 3000000, timeout=0.5); fd = port.fd
        g = bytearray(); gain = pump(fd, g, 4)
        log("  close + reopen, nothing else -> +%d in 4 s" % gain)
        while gain and pump(fd, g, 2): pass
        after(g, at, i)
    if MODE == "peek":
        for item in usb_peek():
            if isinstance(item, str): log("  usb read:", item); continue
            ln, status, pay = item
            log("  usb read: %d raw bytes, status %s, payload %d, stream offset %s (tty had %d, so %s in limbo before it)"
                % (ln, status, len(pay), where(pay, at), len(got), (where(pay, at) or 0) - len(got)))
        log("  after usb peek, tty 3 s: +%d" % pump(fd, got, 3), "FIONREAD", inq(fd))
    try: port.close()
    except Exception: pass
    proc.kill()
    log("  recover:", t.recover())
    return False
end, i, bad = time.time() + MINUTES * 60, 0, 0
while time.time() < end:
    i += 1
    if not one(i): bad += 1
log("done", i, "runs", bad, "not ok")
