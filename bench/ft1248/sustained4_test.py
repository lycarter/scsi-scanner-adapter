"""Mac side of the 4-bit FT1248 sustained test (CPU-free on the Pico; see pio4_ft1248.py).
    .venv/bin/python sustained4_test.py tx|rx MEGABYTES [SCLK_MHZ H L]
tx: Pico -> Mac. The Mac records everything, then rebuilds the expected stream (two pseudorandom
    128 KB blocks alternating, each pass stamped with its number) and compares every byte, plus
    its CRC-32 of the received bytes against the Pico's hardware CRC of the bytes it sent.
rx: Mac -> Pico. One pseudorandom 64 KB block repeated, each pass stamped; the Pico compares
    every block bytewise as it arrives and CRCs everything in hardware.
"""
import subprocess, sys, threading, time, zlib
import numpy as np
import serial

PICO, FTDI = "/dev/cu.usbmodem12301", "/dev/cu.usbserial-BENCH1"
MPREMOTE = sys.executable.replace("python", "mpremote")
BLOCK = 131072


def murmur(start, nwords):
    h = np.arange(start, start + nwords, dtype=np.uint32)
    h ^= h >> 16; h *= np.uint32(0x85EBCA6B); h ^= h >> 13; h *= np.uint32(0xC2B2AE35); h ^= h >> 16
    return h.astype("<u4")


def tx_reference(n):
    passes = n // BLOCK
    two = murmur(0, 2 * BLOCK // 4).reshape(2, BLOCK // 4)
    out = np.empty((passes, BLOCK // 4), dtype="<u4")
    out[0::2] = two[0]; out[1::2] = two[1]
    out[:, 0] = np.arange(passes, dtype=np.uint32)
    return out.tobytes()


def rx_reference(n):
    block = 65536
    out = np.tile(murmur(0, block // 4), (n // block, 1))
    out[:, 0] = np.arange(n // block, dtype=np.uint32)
    return out.astype("<u4").tobytes()


progress = {"bytes": 0}   # payload bytes moved so far, updated live for soak.py's status line
CLK_MHZ = 150      # --clk=N overclocks the Pico's system clock, so SCLK = N / (H + L)
BYPASS = True      # --nobypass leaves the input synchroniser in


def pico(code):
    code = ("import machine, pio4_ft1248 as p; machine.freq(%d); p.SYNC_BYPASS = %s; "
            "\ntry:\n    %s\nfinally:\n    machine.freq(150000000)" % (CLK_MHZ * 1000000, BYPASS, code))
    return subprocess.Popen([MPREMOTE, "connect", PICO, "exec", code],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def recover():
    """After a failed run the Mac's driver and the FT232H can still hold megabytes of the old
    stream, which makes every later run look corrupt. Throw it all away: flush the tty, reset
    the FT232H over USB, then drain what is left from the Pico side."""
    try:
        port = serial.Serial(FTDI, 3000000, timeout=0.2, write_timeout=1)
        port.reset_output_buffer(); port.reset_input_buffer(); port.close()
    except Exception:
        pass
    from pyftdi.eeprom import FtdiEeprom
    try:
        eeprom = FtdiEeprom(); eeprom.open("ftdi://ftdi:232h/1"); eeprom.reset_device()
    except Exception:
        pass     # macOS sometimes reports "no such device" as the chip re-enumerates; harmless
    time.sleep(4)
    out = subprocess.run([MPREMOTE, "connect", PICO, "exec",
                          "import machine, pio4_ft1248 as p; machine.freq(150000000); print(p.drain(), p.drain())"],
                         capture_output=True, text=True, timeout=60)
    return out.stdout.strip()


def run(direction, mb, sclk_mhz=30.0, H=3, L=2, quiet=False):
    n = max(BLOCK, int(mb * 1024 * 1024) // BLOCK * BLOCK)
    freq = int(sclk_mhz * 1e6 * (H + L))
    args = "%d, freq=%d, H=%d, L=%d" % (n, freq, H, L)
    port = serial.Serial(FTDI, 3000000, timeout=0.5)
    port.reset_input_buffer()
    res = {"dir": direction, "MB": n / 1048576, "sclk_MHz": sclk_mhz, "H": H, "L": L, "ok": False}
    if direction == "tx":
        got, stop, times = bytearray(), threading.Event(), []

        def reader():
            idle = 0
            import os, select
            while len(got) < n and idle < 6:
                # raw os.read on the tty: pyserial's read() loop was not the limit, but this
                # keeps Python's share of the work as small as it can be
                ready = select.select([port.fd], [], [], 0.5)[0]
                data = os.read(port.fd, 1 << 20) if ready else b""
                if data:
                    got.extend(data); times.append(time.time()); idle = 0
                    progress["bytes"] += len(data)
                elif stop.is_set():
                    idle += 1
        thread = threading.Thread(target=reader); thread.start()
        out = pico("p.tx_sustained(%s)" % args).communicate(timeout=1800)[0]
        stop.set(); thread.join()
        line = [l for l in out.splitlines() if l.startswith("TXS")]
        res["pico"] = line[0] if line else out.strip()[-300:]
        res["received"] = len(got)
        want = tx_reference(n)
        res["bytewise_identical"] = bytes(got) == want
        if not res["bytewise_identical"] and got:
            m = min(len(got), n)
            a, b = np.frombuffer(bytes(got[:m]), np.uint8), np.frombuffer(want[:m], np.uint8)
            bad = np.flatnonzero(a != b)
            res["wrong_bytes"] = int(len(bad)); res["first_wrong"] = int(bad[0]) if len(bad) else None
        res["crc_mac_received"] = "%08x" % zlib.crc32(bytes(got))
        if line:
            _, sent, us, crc, gap = line[0].split()
            res["crc_pico_sent"] = crc
            res["crc_match"] = crc == res["crc_mac_received"]
            if int(sent) == n:
                res["seconds"] = round(int(us) / 1e6, 3)
                res["MB_per_s"] = round(n / int(us), 3)
                res["ok"] = res["bytewise_identical"] and res["crc_match"]
    else:
        data = rx_reference(n)
        proc = pico("p.rx_sustained(%s)" % args)
        seen = ""
        while True:
            line = proc.stdout.readline()
            seen += line
            if not line or line.startswith("READY"):
                break
        if not line:
            res["pico"] = seen.strip()[-300:]
            port.close()
            return res
        port.write_timeout = 20
        t0 = time.time()
        try:
            # In 64 KB pieces: pyserial re-slices (copies) the whole remaining buffer after
            # every partial write, which made one 100 MB write() crawl.
            view = memoryview(data)
            for i in range(0, n, 65536):
                port.write(view[i:i + 65536])
                progress["bytes"] += min(65536, n - i)
        except serial.SerialTimeoutException:
            res["mac_write"] = "timed out"
        res["mac_write_s"] = round(time.time() - t0, 3)
        out = proc.communicate(timeout=1800)[0]
        line = [l for l in out.splitlines() if l.startswith("RXS")]
        res["pico"] = out.strip()[-300:]
        res["crc_mac_sent"] = "%08x" % zlib.crc32(data)
        if line:
            _, got, us, crc, bad, first_bad, gap = line[0].split()
            res["crc_pico_received"] = crc
            res["crc_match"] = crc == res["crc_mac_sent"]
            res["bad_blocks"] = int(bad)
            if int(got) == n and int(us) > 0:
                res["seconds"] = round(int(us) / 1e6, 3)
                res["MB_per_s"] = round(n / int(us), 3)
                res["ok"] = res["crc_match"] and int(bad) == 0
    port.close()
    return res


def run_tx_libusb(mb, sclk_mhz=30.0, H=3, L=2):
    """Pico -> Mac through libusb (pyusb bulk reads) instead of Apple's serial node. Raw USB
    packets are kept and the 2 FTDI status bytes per 512-byte packet stripped afterwards."""
    from pyftdi.ftdi import Ftdi
    n = max(BLOCK, int(mb * 1048576) // BLOCK * BLOCK)
    res = {"dir": "tx_libusb", "MB": n / 1048576, "sclk_MHz": sclk_mhz, "H": H, "L": L, "ok": False}
    ftdi = Ftdi(); ftdi.open_from_url("ftdi://ftdi:232h/1")
    ftdi.set_latency_timer(2)
    dev, raw, stop = ftdi.usb_dev, [], threading.Event()

    def reader():
        idle = 0
        while idle < 20:
            try:
                chunk = dev.read(0x81, 1 << 16, 100)
            except Exception:
                chunk = b""
            if len(chunk) > 2 or (len(chunk) and len(chunk) % 512 != 2):
                raw.append(bytes(chunk)); idle = 0
                progress["bytes"] += len(chunk) - 2 * ((len(chunk) + 511) // 512)
            elif stop.is_set():
                idle += 1
    thread = threading.Thread(target=reader); thread.start()
    args = "%d, freq=%d, H=%d, L=%d" % (n, int(sclk_mhz * 1e6 * (H + L)), H, L)
    out = pico("p.tx_sustained(%s)" % args).communicate(timeout=1800)[0]
    stop.set(); thread.join(); ftdi.close()
    data = bytearray()
    for chunk in raw:
        for i in range(0, len(chunk), 512):
            data += chunk[i + 2:i + 512]
    line = [l for l in out.splitlines() if l.startswith("TXS")]
    res["pico"] = line[0] if line else out.strip()[-300:]
    res["received"] = len(data)
    want = tx_reference(n)
    res["bytewise_identical"] = bytes(data) == want
    if not res["bytewise_identical"] and data:
        m = min(len(data), n)
        bad = np.flatnonzero(np.frombuffer(bytes(data[:m]), np.uint8) != np.frombuffer(want[:m], np.uint8))
        res["wrong_bytes"] = int(len(bad)) + abs(n - len(data))
    if line:
        _, sent, us, crc, gap = line[0].split()
        res["crc_match"] = crc == "%08x" % zlib.crc32(bytes(data))
        if int(sent) == n:
            res["seconds"] = round(int(us) / 1e6, 3)
            res["MB_per_s"] = round(n / int(us), 3)
            res["ok"] = res["bytewise_identical"] and res["crc_match"]
    return res


if __name__ == "__main__":
    for arg in [a for a in sys.argv if a.startswith("--")]:
        sys.argv.remove(arg)
        if arg.startswith("--clk="):
            CLK_MHZ = int(arg[6:])
        if arg == "--nobypass":
            BYPASS = False
    direction, mb = sys.argv[1], float(sys.argv[2])
    extra = sys.argv[3:6]
    r = run(direction, mb, *( [float(extra[0]), int(extra[1]), int(extra[2])] if len(extra) == 3 else []))
    if not r["ok"]:
        r["recovered_drained"] = recover()
    print(r)
