#!/usr/bin/env python3
"""Split a Howtek multi-module Intel-HEX firmware file into per-module binaries.

Howtek FLASH files (e.g. R535.HEX) are a text header followed by several Intel-HEX
modules, each ending with an EOF record. Each module targets a different processor
(MP, IOC, SSC, IEC, and the flash downloader), and their address ranges overlap,
so they must be split before loading into a disassembler.

Usage: ihex_split.py FIRMWARE.HEX OUT_PREFIX
Writes OUT_PREFIX_mod<N>_<loadaddr>.bin and prints a summary.
"""
import sys


def parse_modules(path):
    modules, records, preamble = [], [], []
    with open(path, "rb") as f:
        for raw in f.read().decode("latin-1").splitlines():
            line = raw.strip()
            if not line.startswith(":"):
                if line:
                    preamble.append(line)
                continue
            records.append(line)
            if line[7:9] == "01":  # EOF record ends a module
                modules.append((preamble, records))
                records, preamble = [], []
    return modules


def load(records):
    mem, base, start = {}, 0, None
    for rec in records:
        b = bytes.fromhex(rec[1:])
        n, addr, rtype, data = b[0], (b[1] << 8) | b[2], b[3], b[4:4 + b[0]]
        if sum(b) & 0xFF:
            # R535/R813 IEC module has 4 extended-address records off by exactly 2;
            # data records are all good, so warn rather than abort.
            print(f"warning: bad checksum (residue {sum(b) & 0xFF:#04x}): {rec}", file=sys.stderr)
        if rtype == 0x00:
            for i, x in enumerate(data):
                mem[base + addr + i] = x
        elif rtype == 0x02:  # extended segment address
            base = int.from_bytes(data, "big") * 16
        elif rtype == 0x04:  # extended linear address
            base = int.from_bytes(data, "big") << 16
        elif rtype in (0x03, 0x05):  # start segment (CS:IP) / start linear address
            start = (rtype, data.hex())
    return mem, start


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    path, prefix = sys.argv[1], sys.argv[2]
    for i, (preamble, records) in enumerate(parse_modules(path)):
        mem, start = load(records)
        if not mem:
            continue
        lo, hi = min(mem), max(mem)
        image = bytearray(b"\xff" * (hi - lo + 1))  # gaps filled as erased flash
        for addr, val in mem.items():
            image[addr - lo] = val
        out = f"{prefix}_mod{i}_{lo:06x}.bin"
        with open(out, "wb") as f:
            f.write(image)
        print(f"module {i}: {lo:06x}-{hi:06x} ({len(mem)} bytes) start={start} -> {out}")


if __name__ == "__main__":
    main()
