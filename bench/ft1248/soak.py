"""Unattended soak of the 4-bit FT1248 link. Cycles three verified transfers until the time is up:
    Pico -> Mac through Apple's serial node, Pico -> Mac through libusb, Mac -> Pico (serial node).
Every byte is checked (bytewise + CRC-32) by the same scripts as the one-off tests.
    caffeinate -is .venv/bin/python soak.py HOURS [SCLK_MHZ H L] [MB_PER_TRANSFER]
Appends one JSON line per transfer to soak-log.jsonl and rewrites soak-summary.txt each cycle.
After any failure it resets the FT232H, drains stale data and carries on; it stops early only
after 10 failures in a row."""
import ast, json, subprocess, sys, time

PY = sys.executable
hours = float(sys.argv[1])
sclk, H, L = (sys.argv[2:5] + ["30", "3", "2"][len(sys.argv[2:5]):])
mb = int(sys.argv[5]) if len(sys.argv) > 5 else 256
deadline = time.time() + hours * 3600
started = time.strftime("%Y-%m-%d %H:%M:%S")
totals = {k: {"runs": 0, "ok": 0, "bytes_ok": 0, "seconds_ok": 0.0, "failed": []}
          for k in ("tx_apple", "tx_libusb", "rx_apple")}


def call(args, timeout=600):
    try:
        out = subprocess.run([PY] + args, capture_output=True, text=True, timeout=timeout)
        return out.stdout + out.stderr
    except subprocess.TimeoutExpired as e:
        subprocess.run(["pkill", "-f", "mpremote"])
        return "TIMEOUT " + str(e.stdout or "")[-300:]


def recover():
    return call(["-c", "import sustained4_test as s; print(s.recover())"], 120).strip()[-200:]


def transfer(kind):
    n = mb * 1048576
    if kind == "tx_libusb":
        out = call(["libusb_rx_test.py", str(mb), sclk, H, L])
        ok = "bytewise identical: True" in out and "crc match: True" in out
        secs = float(out.split(" s = ")[0].split()[-1]) if ok else 0.0
        detail = out.strip()[-300:]
        if not ok:
            detail += " | recover: " + recover()
    else:
        out = call(["sustained4_test.py", kind[:2], str(mb), sclk, H, L])
        try:
            res = ast.literal_eval(out.strip().splitlines()[-1])
        except Exception:
            res = {"ok": False, "raw": out.strip()[-300:]}
            res["recover"] = recover()
        ok, secs, detail = bool(res.get("ok")), float(res.get("seconds") or 0), res
    t = totals[kind]
    t["runs"] += 1
    if ok:
        t["ok"] += 1; t["bytes_ok"] += n; t["seconds_ok"] += secs
    else:
        t["failed"].append(time.strftime("%H:%M:%S"))
    with open("soak-log.jsonl", "a") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, "ok": ok,
                            "MB": mb, "seconds": secs, "detail": detail}, default=str) + "\n")
    return ok


def summary(state):
    lines = ["FT1248 4-bit soak, SCLK %s MHz (H %s, L %s), %d MB per transfer" % (sclk, H, L, mb),
             "started %s, now %s, state: %s" % (started, time.strftime("%Y-%m-%d %H:%M:%S"), state)]
    for kind, t in totals.items():
        rate = t["bytes_ok"] / t["seconds_ok"] / 1e6 if t["seconds_ok"] else 0
        lines.append("%-9s: %d of %d transfers perfect, %.1f GB verified, mean %.2f MB/s, failures at %s"
                     % (kind, t["ok"], t["runs"], t["bytes_ok"] / 1e9, rate, t["failed"] or "none"))
    open("soak-summary.txt", "w").write("\n".join(lines) + "\n")
    return "\n".join(lines)


streak = 0
state = "running"
while time.time() < deadline and state == "running":
    for kind in ("tx_apple", "tx_libusb", "rx_apple"):
        if time.time() >= deadline:
            break
        streak = 0 if transfer(kind) else streak + 1
        if streak >= 10:
            state = "ABORTED after 10 failures in a row"
            break
    summary(state)
print(summary("finished" if state == "running" else state))
