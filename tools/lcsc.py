#!/usr/bin/env python3
"""Look up LCSC *store* stock, MOQ and price breaks by C-number.

LCSC (loose parts) and JLCPCB (assembly library) share C-numbers but keep
separate inventories. Use the pcbparts MCP for JLC assembly stock and
basic/preferred/extended tier; use this for parts we buy loose from LCSC.

LCSC's search endpoint is bot-protected, so this only takes C-numbers.

    python3 tools/lcsc.py C23186 C14677
    python3 tools/lcsc.py C23186 --json
"""
import argparse
import json
import sys
import time
import urllib.request

URL = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode={}"


def fetch(code):
    req = urllib.request.Request(URL.format(code), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.load(r).get("result")
    if not d:
        return {"lcsc": code, "error": "not found"}
    return {
        "lcsc": d["productCode"],
        "mpn": d.get("productModel"),
        "manufacturer": d.get("brandNameEn"),
        "package": d.get("encapStandard"),
        "description": d.get("productIntroEn"),
        "stock": d.get("stockNumber"),
        "min_buy": d.get("minBuyNumber"),
        "multiple": d.get("split"),
        "reel_qty": d.get("minPacketNumber"),
        "prices": [(p["ladder"], p["usdPrice"]) for p in d.get("productPriceList") or []],
        "datasheet": d.get("pdfUrl"),
    }


def show(p):
    if "error" in p:
        print(f"{p['lcsc']}: {p['error']}\n")
        return
    print(f"{p['lcsc']}  {p['mpn']}  ({p['manufacturer']}, {p['package']})")
    print(f"  {p['description']}")
    print(f"  LCSC stock {p['stock']:,}   min buy {p['min_buy']}, multiples of {p['multiple']}")
    print("  price: " + "  ".join(f"{q}+ ${u}" for q, u in p["prices"]))
    print(f"  datasheet: {p['datasheet']}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("codes", nargs="+", help="LCSC C-numbers")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    out = []
    for i, code in enumerate(args.codes):
        if i:
            time.sleep(0.5)  # be polite to an undocumented API
        try:
            out.append(fetch(code.upper()))
        except Exception as e:
            out.append({"lcsc": code, "error": str(e)})
    if args.json:
        json.dump(out, sys.stdout, indent=2)
        print()
    else:
        for p in out:
            show(p)
    return 1 if any("error" in p for p in out) else 0


if __name__ == "__main__":
    sys.exit(main())
