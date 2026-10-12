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


def commit(eeprom, old, write):
    new = eeprom.data  # regenerates the checksum
    for off, (a, b) in enumerate(zip(old, new)):
        if a != b:
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
    if not ok:
        sys.exit(1)
    print("before:")
    describe(old)
    backup(eeprom, old)
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
    p = sub.add_parser("set-ft1248")
    p.add_argument("--cpol", choices=("low", "high"), default="low")
    p.add_argument("--lsb-first", action="store_true")
    p.add_argument("--no-flow-control", action="store_true")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_set)
    p = sub.add_parser("set-uart")
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
