"""Mac -> Pico through libusb instead of Apple's serial node.
    .venv/bin/python libusb_tx_test.py MEGABYTES SCLK_MHZ H L"""
import subprocess, sys, time, zlib
from pyftdi.ftdi import Ftdi
from sustained4_test import rx_reference, MPREMOTE, PICO

mb, sclk, H, L = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
n = int(mb * 1048576) // 65536 * 65536
data = rx_reference(n)
code = "import pio4_ft1248 as p; p.rx_sustained(%d, freq=%d, H=%d, L=%d)" % (n, int(sclk * 1e6 * (H + L)), H, L)
proc = subprocess.Popen([MPREMOTE, "connect", PICO, "exec", code], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
while True:
    line = proc.stdout.readline()
    if not line or line.startswith("READY"):
        break
ftdi = Ftdi(); ftdi.open_from_url("ftdi://ftdi:232h/1")
view = memoryview(data)
for i in range(0, n, 1 << 16):
    ftdi.usb_dev.write(0x02, view[i:i + (1 << 16)], 20000)
out = proc.communicate(timeout=600)[0]
ftdi.close()
line = [l for l in out.splitlines() if l.startswith("RXS")]
print("pico:", out.strip()[-200:])
if line:
    _, got, us, crc, bad, first_bad, gap = line[0].split()
    print("got %s of %d, bad blocks %s, crc match %s, %.3f s = %.3f MB/s"
          % (got, n, bad, crc == "%08x" % zlib.crc32(data), int(us) / 1e6, int(got) / max(int(us), 1)))
