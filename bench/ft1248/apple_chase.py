"""Chase the Apple-serial-node failures seen in the soak (see README).
    .venv/bin/python apple_chase.py STEP [STEP ...]
Steps: ok (plain Pico -> Mac capture), stall (reader stops reading for 8 s after 20 MB),
recover, libusb, rx. Every Pico -> Mac capture is saved to OUT/cap-N.bin with its record."""
import json, os, select, sys, threading, time, zlib
import numpy as np
import serial
import sustained4_test as t

OUT = os.environ.get("CHASE_OUT", "/tmp")
N = int(os.environ.get("CHASE_MB", "256")) * 1048576
seq = [0]


def capture(pause_at=None, pause_s=8.0):
    port = serial.Serial(t.FTDI, 3000000, timeout=0.5)
    port.reset_input_buffer()
    got, stop, paused = bytearray(), threading.Event(), [False]

    def reader():
        idle = 0
        while len(got) < N + (1 << 20) and idle < 6:
            if pause_at is not None and not paused[0] and len(got) >= pause_at:
                paused[0] = True; time.sleep(pause_s)
            ready = select.select([port.fd], [], [], 0.5)[0]
            data = os.read(port.fd, 1 << 20) if ready else b""
            if data:
                got.extend(data); idle = 0
            elif stop.is_set():
                idle += 1
    th = threading.Thread(target=reader); th.start()
    out = t.pico("p.tx_sustained(%d, freq=150000000, H=3, L=2)" % N).communicate(timeout=1800)[0]
    stop.set(); th.join(); port.close()
    want = t.tx_reference(N)
    m = min(len(got), N)
    bad = np.flatnonzero(np.frombuffer(bytes(got[:m]), np.uint8) != np.frombuffer(want[:m], np.uint8))
    seq[0] += 1
    name = "%s/cap-%d-%d.bin" % (OUT, os.getpid(), seq[0])
    rec = {"pico": out.strip()[-200:], "received": len(got), "wrong": int(len(bad)),
           "first_wrong": int(bad[0]) if len(bad) else None, "crc": "%08x" % zlib.crc32(bytes(got)),
           "ok": len(got) == N and len(bad) == 0}
    if not rec["ok"]:
        open(name, "wb").write(got); rec["file"] = name
    return rec


for step in sys.argv[1:]:
    t0 = time.time()
    if step == "ok":
        r = capture()
    elif step == "stall":
        r = capture(pause_at=20 << 20)
    elif step == "recover":
        r = {"drained": t.recover()}
    elif step == "libusb":
        r = t.run_tx_libusb(N / 1048576)
    elif step == "rx":
        r = t.run("rx", N / 1048576)
    print(time.strftime("%H:%M:%S"), step, "%.1fs" % (time.time() - t0), json.dumps(r, default=str), flush=True)
