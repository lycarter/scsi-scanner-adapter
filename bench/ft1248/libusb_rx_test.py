"""Pico -> Mac through libusb (pyftdi/pyusb) instead of Apple's /dev/cu.usbserial node, to see
whether the ~5.8 MB/s ceiling belongs to Apple's serial driver. Reads raw bulk-IN packets and
strips the 2 FTDI status bytes from each 512-byte packet afterwards.
    .venv/bin/python libusb_rx_test.py MEGABYTES SCLK_MHZ H L"""
import subprocess, sys, threading, time, zlib
import numpy as np
from pyftdi.ftdi import Ftdi
from sustained4_test import tx_reference, MPREMOTE, PICO, BLOCK

mb, sclk, H, L = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
n = int(mb * 1048576) // BLOCK * BLOCK
ftdi = Ftdi(); ftdi.open_from_url("ftdi://ftdi:232h/1")
ftdi.set_latency_timer(2)
dev, ep = ftdi.usb_dev, 0x81
raw, stop = [], threading.Event()


def reader():
    idle = 0
    while idle < 20:
        try:
            chunk = dev.read(ep, 1 << 16, 100)
        except Exception:
            chunk = b""
        if len(chunk) > 2 or (len(chunk) and len(chunk) % 512 != 2):
            raw.append(bytes(chunk)); idle = 0
        elif stop.is_set():
            idle += 1


thread = threading.Thread(target=reader); thread.start()
code = "import pio4_ft1248 as p; p.tx_sustained(%d, freq=%d, H=%d, L=%d)" % (n, int(sclk * 1e6 * (H + L)), H, L)
out = subprocess.run([MPREMOTE, "connect", PICO, "exec", code], capture_output=True, text=True, timeout=600).stdout
stop.set(); thread.join(); ftdi.close()
data = bytearray()
for chunk in raw:                      # each USB packet: 2 status bytes + up to 510 data bytes
    for i in range(0, len(chunk), 512):
        data += chunk[i + 2:i + 512]
line = [l for l in out.splitlines() if l.startswith("TXS")]
print("pico:", line[0] if line else out.strip()[-300:])
print("received %d of %d, bytewise identical: %s" % (len(data), n, bytes(data) == tx_reference(n)))
if line and int(line[0].split()[1]) == n:
    us = int(line[0].split()[2])
    print("%.3f s = %.3f MB/s; crc match: %s" % (us / 1e6, n / us, line[0].split()[3] == "%08x" % zlib.crc32(bytes(data))))
