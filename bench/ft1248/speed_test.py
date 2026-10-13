"""Mac side of the FT1248 PIO speed test. Copies pio_ft1248.py to the Pico and runs one test.
    .venv/bin/python speed_test.py tx|rx N_BYTES SCLK_HZ [H L]
tx = Pico -> Mac, rx = Mac -> Pico. SCLK = state-machine clock / (H + L); default H = L = 4.
"""
import subprocess, sys, threading, time
import serial

PICO = "/dev/cu.usbmodem12301"
FTDI = "/dev/cu.usbserial-BENCH1"
MPREMOTE = sys.executable.replace("python", "mpremote")


def pattern(n):
    return bytes((i * 167 + (i >> 8) * 31 + 13) & 0xFF for i in range(n))


BYPASS = "--bypass" in sys.argv
if BYPASS:
    sys.argv.remove("--bypass")


def pico(code):
    code = "import pio_ft1248 as p; p.SYNC_BYPASS = %s; " % BYPASS + code
    return subprocess.Popen([MPREMOTE, "connect", PICO, "exec", code],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def run(direction, n, sclk, H=4, L=4):
    freq = sclk * (H + L)
    args = "%d, freq=%d, H=%d, L=%d" % (n, freq, H, L)
    port = serial.Serial(FTDI, 3000000, timeout=0.5)
    port.reset_input_buffer()
    result = {"dir": direction, "n": n, "sclk": sclk, "H": H, "L": L, "bypass": BYPASS}
    if direction == "tx":
        got, stamps, stop = bytearray(), [], threading.Event()

        def reader():
            idle = 0
            while len(got) < n and idle < 8 and not (stop.is_set() and idle > 2):
                chunk = port.read(65536)
                if chunk:
                    stamps.append(time.time()); got.extend(chunk); idle = 0
                else:
                    idle += 1 if (got or stop.is_set()) else 0
        thread = threading.Thread(target=reader); thread.start()
        proc = pico("p.tx_test(%s)" % args)
        out = proc.communicate(timeout=90)[0]
        stop.set(); thread.join()
        want = pattern(32768) * (n // 32768 + 1)
        bad = sum(a != b for a, b in zip(got, want))
        line = [l for l in out.splitlines() if l.startswith("TX")]
        result.update(got=len(got), bad=bad, pico=out.strip() if not line else line[0])
        if line and int(line[0].split()[1]) == n:
            result["kB_per_s"] = round(n / (int(line[0].split()[2]) / 1e6) / 1000, 1)
    else:
        proc = pico("p.rx_test(%s)" % args)
        while True:
            line = proc.stdout.readline()
            if not line or line.startswith("READY"):
                break
        t0 = time.time()
        port.write(pattern(n)); port.flush()
        result["mac_write_s"] = round(time.time() - t0, 3)
        out = proc.communicate(timeout=90)[0]
        line = [l for l in out.splitlines() if l.startswith("RX")]
        result["pico"] = line[0] if line else out.strip()
        if line:
            _, got, bad, us, first_bad = line[0].split()
            result.update(got=int(got), bad=int(bad))
            if int(got) == n and int(us) > 0:
                result["kB_per_s"] = round(n / (int(us) / 1e6) / 1000, 1)
    port.close()
    return result


if __name__ == "__main__":
    direction, n, sclk = sys.argv[1], int(sys.argv[2]), int(float(sys.argv[3]))
    hl = [int(v) for v in sys.argv[4:6]] or [4, 4]
    print(run(direction, n, sclk, *hl))
