"""Small-packet round trip: Mac -> FT232H -> Pico -> FT232H -> Mac, timed on the Mac.
    .venv/bin/python latency_test.py [COUNT]
Runs each case with and without the FT1248 flush command (0x4) after the reply."""
import os, statistics, subprocess, sys, time
import serial

PICO, FTDI = "/dev/cu.usbmodem12301", "/dev/cu.usbserial-BENCH1"
MPREMOTE = sys.executable.replace("python", "mpremote")
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 300


def case(size, flush):
    port = serial.Serial(FTDI, 3000000, timeout=2)
    port.reset_input_buffer()
    code = "import pio4_ft1248 as p; p.drain(); p.echo(%d, size=%d, flush=%s)" % (COUNT, size, flush)
    proc = subprocess.Popen([MPREMOTE, "connect", PICO, "exec", code], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    seen = ""
    while True:
        line = proc.stdout.readline(); seen += line
        if not line or line.startswith("READY"):
            break
    if not line:
        port.close(); return "pico failed: " + seen.strip()[-200:]
    times, bad = [], 0
    for i in range(COUNT):
        msg = os.urandom(size)
        t0 = time.perf_counter()
        port.write(msg)
        reply = port.read(size)
        times.append((time.perf_counter() - t0) * 1000)
        if reply != msg:
            bad += 1
            if len(reply) < size:
                break
    port.close()
    try:
        out = proc.communicate(timeout=10)[0]
    except subprocess.TimeoutExpired:
        proc.kill(); out = ""
    pico = [l for l in out.splitlines() if l.startswith("ECHO")]
    times.sort()
    q = lambda f: times[min(len(times) - 1, int(f * len(times)))]
    return ("%4d bytes, flush %-5s: median %6.2f ms, p10 %6.2f, p90 %6.2f, min %6.2f, max %6.2f; "
            "wrong replies %d/%d; pico turnaround %s us"
            % (size, flush, statistics.median(times), q(0.1), q(0.9), times[0], times[-1], bad,
               len(times), pico[0].split()[2] if pico else "?"))


if __name__ == "__main__":
    for size in (10, 64, 600):
        for flush in (False, True):
            print(case(size, flush), flush=True)
