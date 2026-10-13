"""Sustained Pico -> Mac transfer of pseudorandom data over FT1248, verified byte for byte.
    .venv/bin/python sustained_test.py [MEGABYTES] [SM_FREQ_HZ H L]
The Pico generates the data (pio_ft1248.fill_random) and keeps a running CRC-32. The Mac records
everything from /dev/cu.usbserial-BENCH1, regenerates the same stream independently with numpy,
compares every byte, and compares its CRC-32 of the *received* bytes with the Pico's CRC of the
*generated* bytes."""
import subprocess, sys, threading, time, zlib
import numpy as np
import serial

PICO, FTDI = "/dev/cu.usbmodem12301", "/dev/cu.usbserial-BENCH1"
MPREMOTE = sys.executable.replace("python", "mpremote")
CHUNK = 32768


def reference(n):
    h = np.arange(n // 4, dtype=np.uint32)
    h ^= h >> 16; h *= np.uint32(0x85EBCA6B); h ^= h >> 13; h *= np.uint32(0xC2B2AE35); h ^= h >> 16
    return h.astype("<u4").tobytes()


def main():
    mb = float(sys.argv[1]) if len(sys.argv) > 1 else 100
    freq, H, L = (int(float(v)) for v in sys.argv[2:5]) if len(sys.argv) > 4 else (150_000_000, 3, 2)
    n = int(mb * 1024 * 1024) // CHUNK * CHUNK
    port = serial.Serial(FTDI, 3000000, timeout=0.5)
    port.reset_input_buffer()
    got, stamps, stop = bytearray(), [], threading.Event()

    def reader():
        idle = 0
        while len(got) < n and idle < 6:
            data = port.read(1 << 20)
            if data:
                got.extend(data); stamps.append((time.time(), len(got))); idle = 0
            elif stop.is_set():
                idle += 1
    thread = threading.Thread(target=reader); thread.start()
    code = "import pio_ft1248 as p; p.tx_random(%d, freq=%d, H=%d, L=%d)" % (n, freq, H, L)
    out = subprocess.run([MPREMOTE, "connect", PICO, "exec", code], capture_output=True,
                         text=True, timeout=1800)
    stop.set(); thread.join(); port.close()
    line = [l for l in out.stdout.splitlines() if l.startswith("TXR")]
    print("SCLK %.2f MHz (H=%d L=%d), %d bytes requested" % (freq / (H + L) / 1e6, H, L, n))
    print("pico:", line[0] if line else (out.stdout + out.stderr).strip())
    print("mac received %d bytes" % len(got))
    if stamps:
        span = stamps[-1][0] - stamps[0][0]
        print("mac first-to-last read: %.3f s" % span)
        gaps = sorted((b[0] - a[0] for a, b in zip(stamps, stamps[1:])), reverse=True)[:3]
        print("longest gaps between reads: %s s" % [round(g, 3) for g in gaps])
    want = reference(n)
    same = bytes(got) == want
    if not same:
        a, b = np.frombuffer(bytes(got[:n]), np.uint8), np.frombuffer(want[:len(got)], np.uint8)
        bad = np.flatnonzero(a != b)
        print("WRONG BYTES: %d, first at offset %d" % (len(bad), bad[0] if len(bad) else -1))
    print("bytewise identical to the regenerated stream:", same)
    mac_crc = "%08x" % zlib.crc32(bytes(got))
    if line:
        _, sent, us, pico_crc, gen_us = line[0].split()
        print("crc32 pico (generated) %s, mac (received) %s, match: %s" % (pico_crc, mac_crc, pico_crc == mac_crc))
        if int(sent) == n:
            s = int(us) / 1e6
            print("pico elapsed %.3f s = %.3f MB/s (%.1f Mbit/s); generation used %.1f %% of that"
                  % (s, n / s / 1e6, n * 8 / s / 1e6, 100 * int(gen_us) / int(us)))


if __name__ == "__main__":
    main()
