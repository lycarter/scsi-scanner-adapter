"""Mac side of the loopback test: Mac -> FT232H -> Pico -> FT232H -> Mac.
    .venv/bin/python mac_loopback.py [/dev/cu.usbmodemXXXX]
Sends bytes into /dev/cu.usbserial-BENCH1, has the Pico read them over FT1248 and write them
back (via mpremote), and checks what arrives on the serial port."""
import subprocess, sys, time
import serial

PICO = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbmodem12301"
MPREMOTE = [sys.executable.replace("python", "mpremote"), "connect", PICO, "mount", "."]


def pico(code):
    out = subprocess.run(MPREMOTE + ["exec", "from ft1248_bitbang import *; init(); " + code],
                         capture_output=True, text=True, timeout=60)
    return (out.stdout + out.stderr).replace("Local directory . is mounted at /remote", "").strip()


port = serial.Serial("/dev/cu.usbserial-BENCH1", 115200, timeout=3)
port.reset_input_buffer()

msg = bytes(range(256)) + b"Howtek D4000 says hi\n"
port.write(msg); port.flush(); time.sleep(0.3)
print("pico:", pico("d = read(400); print(len(d), status()); n = write(d); print('wrote', n); flush()"))
back = port.read(len(msg))
print("Mac -> Pico -> Mac: sent %d, got %d, match: %s" % (len(msg), len(back), back == msg))
