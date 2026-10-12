#!/usr/bin/env python3
"""Read, back up and reconfigure the FT232H breakout's EEPROM for FT1248 mode.

Usage (from bench/ft1248, with the venv from README.md):
    .venv/bin/python ft232h_eeprom.py info                 # read-only; saves a backup
    .venv/bin/python ft232h_eeprom.py set-ft1248           # dry run: shows the byte changes
    .venv/bin/python ft232h_eeprom.py set-ft1248 --write   # really writes
    .venv/bin/python ft232h_eeprom.py set-uart --write     # back to the factory UART mode
    .venv/bin/python ft232h_eeprom.py restore backups/X.bin --write

pyftdi 0.57 can set the port type (byte 0x00, low nibble: 0 UART, 1 FIFO, 2 OPTO, 4 CPU,
8 FT1248) but not the three FT1248 option bits in byte 0x01, so this script pokes them:
    0x01 clock idles high (CPOL)   0x02 LSB first   0x04 flow control
Bit positions are from libftdi's ftdi.c (FT1284_CLK_IDLE_STATE / _DATA_LSB / _FLOW_CONTROL)
and pyftdi's CFG1. That 0x04 *set* means "show buffer status while SS_n is high" is taken
from D2XX's "FT1248FlowControl: enable" comment and is UNVERIFIED until the idle check in
README.md has been seen on the scope.
"""
import argparse
import sys
import time
from pathlib import Path

from pyftdi.eeprom import FtdiEeprom
from pyftdi.ftdi import Ftdi

HERE = Path(__file__).resolve().parent
PORT_TYPES = {0: "UART", 1: "FIFO (245)", 2: "OPTO", 4: "CPU", 8: "FT1248"}
CPOL_HIGH, LSB_FIRST, FLOW_CONTROL = 0x01, 0x02, 0x04


def open_eeprom(url):
    eeprom = FtdiEeprom()
    eeprom.open(url)
    return eeprom


def describe(raw):
    b0, b1 = raw[0], raw[1]
    print(f"  byte 0x00 = 0x{b0:02x}: port type {PORT_TYPES.get(b0 & 0x0F, '?')}, "
          f"driver {'VCP' if b0 & 0x10 else 'D2XX'}")
    print(f"  byte 0x01 = 0x{b1:02x}: clock idles {'high' if b1 & CPOL_HIGH else 'low'}, "
          f"{'LSB' if b1 & LSB_FIRST else 'MSB'} first, "
          f"flow-control bit {'set' if b1 & FLOW_CONTROL else 'clear'}")


def hexdump(raw):
    for off in range(0, len(raw), 16):
        print(f"  {off:02x}: {raw[off:off + 16].hex(' ')}")


def backup(eeprom, raw):
    serial = eeprom._config.get("serial") or "noserial"
    path = HERE / "backups" / f"{serial}-{time.strftime('%Y%m%d-%H%M%S')}.bin"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(raw)
    print(f"backup: {path.relative_to(HERE)} ({len(raw)} bytes)")


def read_state(eeprom):
    """Return the raw image, and say whether it is safe to edit in place."""
    raw = bytes(eeprom._eeprom)
    if eeprom.is_empty:
        print("EEPROM reads all 0xFF: blank, or no EEPROM fitted. Stop and check the part\n"
              "marking before writing (pyftdi cannot tell a blank 93C46 from a 93C56).")
        return raw, False
    if not eeprom._valid:
        print("EEPROM checksum is wrong, so the FT232H is ignoring it (UART defaults).")
        return raw, False
    return raw, True


def cmd_list(args):
    devices = Ftdi.list_devices()
    if not devices:
        print("no FTDI device found (is the FT232H plugged in?)")
    for desc, _ in devices:
        print(f"  {desc.vid:04x}:{desc.pid:04x} serial {desc.sn!r} {desc.description!r}")


def cmd_info(args):
    eeprom = open_eeprom(args.url)
    raw, ok = read_state(eeprom)
    print(f"chip: {eeprom._ftdi.ic_name}, EEPROM image {len(raw)} bytes, "
          f"mirrored (= 128-byte 93C46): {eeprom.is_mirroring_enabled}")
    hexdump(raw)
    if ok:
        describe(raw)
        eeprom.dump_config()
        backup(eeprom, raw)
    eeprom.close()


def cmd_probe(args):
    """Blank EEPROM only: write two test words, read them back, then erase them again."""
    eeprom = open_eeprom(args.url)
    ftdi = eeprom._ftdi
    if not eeprom.is_empty:
        sys.exit("EEPROM is not blank; probe would overwrite real contents")
    tests = {0x70: b"\x34\x12", 0xF0: b"\x5a\xa5"}
    for addr, word in tests.items():
        ftdi._write_eeprom_raw(addr, word, dry_run=False)
    time.sleep(0.05)
    got = {addr: bytes(ftdi.read_eeprom(addr, 2, 256)) for addr in tests}
    for addr in tests:
        ftdi._write_eeprom_raw(addr, b"\xff\xff", dry_run=False)
    time.sleep(0.05)
    blank_again = all(b == 0xFF for b in ftdi.read_eeprom(0, 256, 256))
    for addr, word in tests.items():
        print(f"  0x{addr:02x}: wrote {word.hex()}, read {got[addr].hex()}")
    if all(got[a] == w for a, w in tests.items()):
        print("both words held: a 256-byte (93x56/66) EEPROM is fitted and writable")
    elif got[0x70] == got[0xF0] != b"\xff\xff":
        print("the two addresses alias: 128-byte (93x46) EEPROM")
    else:
        print("writes did not stick: no EEPROM, or it is not responding")
    print(f"erased back to blank: {blank_again}")
    eeprom.close()


def commit(eeprom, old, write):
    new = eeprom.data  # regenerates the checksum
    if len(set(old)) == 1:
        hexdump(new)
    for off, (a, b) in enumerate(zip(old, new)):
        if a != b and len(set(old)) > 1:
            print(f"  0x{off:02x}: 0x{a:02x} -> 0x{b:02x}")
    if new == old:
        print("nothing to change")
        return
    print("after:")
    describe(new)
    if not write:
        print("dry run: nothing written. Add --write to program the EEPROM.")
        return
    eeprom.commit(dry_run=False)  # writes, reads back and compares
    print("written and verified. Unplug and replug the FT232H: it reads the EEPROM at reset.")


def fresh_image(eeprom, serial):
    """Build a complete FT232H image in memory for a blank 93x56 (pyftdi's initialize() leaves
    0xFF in the config bytes). Layout per libftdi's ftdi_eeprom_build(TYPE_232H), recalled from
    memory and cross-checked against pyftdi's decoder offsets."""
    image = bytearray(256)
    image[0x00] = 0x10              # port type UART for now, VCP driver bit (Windows only)
    image[0x02:0x08] = bytes.fromhex("0304" "1460" "0009")  # VID 0403, PID 6014, release 0900
    image[0x08] = 0x80              # bus powered, no remote wakeup
    image[0x09] = 100 // 2          # max power 100 mA
    image[0x0A] = 0x08              # use the serial number string
    # 0x0C/0x0D: ADBUS/ACBUS drive 4 mA, fast slew, no Schmitt. 0x18-0x1C: ACBUS functions, all
    # 0 = tristate (input with pull-up). FT1248 takes ACBUS0-2 over regardless of these.
    image[0x1E] = 0x56              # EEPROM type 93x56
    eeprom._eeprom = image
    eeprom._config.update(manufacturer="FTDI", product="FT232H bench", serial=serial)
    eeprom._generate_var_strings()
    eeprom._dirty.add("eeprom")


def poke(eeprom, offset, clear, set_):
    offsets = [offset]
    if eeprom.is_mirroring_enabled:
        offsets.append(eeprom.mirror_sector + offset)
    for off in offsets:
        eeprom._eeprom[off] = (eeprom._eeprom[off] & ~clear & 0xFF) | set_
    eeprom._dirty.add(f"byte_{offset:02x}")


def cmd_set(args):
    eeprom = open_eeprom(args.url)
    old, ok = read_state(eeprom)
    if ok:
        print("before:")
        describe(old)
        backup(eeprom, old)
    elif args.init_serial and eeprom.is_empty:
        print(f"building a fresh image, serial {args.init_serial!r} (run probe first)")
        fresh_image(eeprom, args.init_serial)
    else:
        sys.exit("refusing to edit; for a blank 256-byte EEPROM pass --init-serial NAME")
    if args.cmd == "set-uart":
        poke(eeprom, 0x00, 0x0F, 0x00)
    else:
        options = ((CPOL_HIGH if args.cpol == "high" else 0)
                   | (LSB_FIRST if args.lsb_first else 0)
                   | (0 if args.no_flow_control else FLOW_CONTROL))
        poke(eeprom, 0x00, 0x0F, 0x08)
        poke(eeprom, 0x01, CPOL_HIGH | LSB_FIRST | FLOW_CONTROL, options)
    commit(eeprom, old, args.write)
    eeprom.close()


def cmd_restore(args):
    image = Path(args.image).read_bytes()
    eeprom = open_eeprom(args.url)
    old = bytes(eeprom._eeprom)
    if len(image) != len(old):
        sys.exit(f"image is {len(image)} bytes but the EEPROM reads as {len(old)}")
    if not eeprom.is_empty and eeprom._valid:
        backup(eeprom, old)
    for off, (a, b) in enumerate(zip(old, image)):
        if a != b:
            print(f"  0x{off:02x}: 0x{a:02x} -> 0x{b:02x}")
    if not args.write:
        print("dry run: nothing written. Add --write to program the EEPROM.")
    elif image != old:
        eeprom._ftdi.overwrite_eeprom(image, dry_run=False)
        print("written. Unplug and replug the FT232H, then run info to check it.")
    eeprom.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--url", default="ftdi://ftdi:232h/1",
                        help="pyftdi URL (default: the first FT232H found)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("info").set_defaults(func=cmd_info)
    sub.add_parser("probe").set_defaults(func=cmd_probe)
    p = sub.add_parser("set-ft1248")
    p.add_argument("--cpol", choices=("low", "high"), default="low")
    p.add_argument("--lsb-first", action="store_true")
    p.add_argument("--no-flow-control", action="store_true")
    p.add_argument("--init-serial", metavar="NAME",
                   help="blank EEPROM: build a full image with this serial number")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_set)
    p = sub.add_parser("set-uart")
    p.set_defaults(init_serial=None)
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_set)
    p = sub.add_parser("restore")
    p.add_argument("image")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_restore)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
