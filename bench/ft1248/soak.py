"""Unattended soak of the 4-bit FT1248 link, with a live status line.
Cycles three verified transfers until the time is up:
    Pico -> Mac through Apple's serial node, Pico -> Mac through libusb, Mac -> Pico (serial node).
Every byte is checked (bytewise + CRC-32) at the end of each transfer.

    caffeinate -is .venv/bin/python soak.py HOURS [SCLK_MHZ H L] [MB_PER_TRANSFER]

Once a second it prints: bytes transferred so far, the rate over the last 60 s (wall clock, so
it includes the pauses while a finished transfer is verified), bytes verified, and the error
count. In a terminal the line updates in place; when output is redirected it prints one line
per second, and the same lines always go to soak-live.log (watch with `tail -f soak-live.log`).
One JSON record per transfer is appended to soak-log.jsonl; soak-summary.txt is rewritten after
each transfer. After any failure it resets the FT232H, drains stale data and carries on; it
stops early only after 10 failures in a row."""
import collections, json, sys, threading, time
import sustained4_test as t

hours = float(sys.argv[1])
sclk, H, L = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0, int(sys.argv[3]) if len(sys.argv) > 3 else 3, int(sys.argv[4]) if len(sys.argv) > 4 else 2
mb = int(sys.argv[5]) if len(sys.argv) > 5 else 256
t0 = time.time()
deadline = t0 + hours * 3600
started = time.strftime("%Y-%m-%d %H:%M:%S")
KINDS = {"tx_apple": lambda: t.run("tx", mb, sclk, H, L),
         "tx_libusb": lambda: t.run_tx_libusb(mb, sclk, H, L),
         "rx_apple": lambda: t.run("rx", mb, sclk, H, L)}
totals = {k: {"runs": 0, "ok": 0, "bytes_ok": 0, "seconds_ok": 0.0, "failed": []} for k in KINDS}
state = {"now": "starting", "verified": 0, "failed": 0, "wrong_bytes": 0, "bad_blocks": 0, "done": False}
live = open("soak-live.log", "a", buffering=1)


def status_line():
    return ("%s  transferred %9.3f GB | last 60 s: %6.2f MB/s | verified %8.2f GB | "
            "errors: %d failed transfers (%d wrong bytes, %d bad 64 KB blocks) | %s")


def ticker():
    samples = collections.deque(maxlen=61)   # one per second: the rate window is 60 s
    tty = sys.stdout.isatty()
    while not state["done"]:
        now, moved = time.time(), t.progress["bytes"]
        samples.append((now, moved))
        span = now - samples[0][0]
        rate = (moved - samples[0][1]) / span / 1e6 if span > 0 else 0.0
        el = int(now - t0)
        line = status_line() % ("%02d:%02d:%02d" % (el // 3600, el % 3600 // 60, el % 60), moved / 1e9, rate,
                                state["verified"] / 1e9, state["failed"], state["wrong_bytes"],
                                state["bad_blocks"], state["now"])
        live.write(line + "\n")
        sys.stdout.write(("\r" + line + "\033[K") if tty else (line + "\n"))
        sys.stdout.flush()
        time.sleep(max(0.0, 1.0 - (time.time() - now)))


def summary(text):
    lines = ["FT1248 4-bit soak, SCLK %g MHz (H %d, L %d), %d MB per transfer" % (sclk, H, L, mb),
             "started %s, now %s, state: %s" % (started, time.strftime("%Y-%m-%d %H:%M:%S"), text)]
    for kind, tot in totals.items():
        rate = tot["bytes_ok"] / tot["seconds_ok"] / 1e6 if tot["seconds_ok"] else 0
        lines.append("%-9s: %d of %d transfers perfect, %.1f GB verified, mean %.2f MB/s while transferring, failures at %s"
                     % (kind, tot["ok"], tot["runs"], tot["bytes_ok"] / 1e9, rate, tot["failed"] or "none"))
    lines.append("total verified %.1f GB; failed transfers %d (wrong bytes %d, bad 64 KB blocks %d)"
                 % (state["verified"] / 1e9, state["failed"], state["wrong_bytes"], state["bad_blocks"]))
    open("soak-summary.txt", "w").write("\n".join(lines) + "\n")
    return "\n".join(lines)


def transfer(kind):
    state["now"] = kind
    before = t.progress["bytes"]
    try:
        res = KINDS[kind]()
    except Exception as exc:                   # a crashed transfer counts as a failure
        res = {"ok": False, "exception": repr(exc)}
    ok = bool(res.get("ok"))
    tot = totals[kind]
    tot["runs"] += 1
    if ok:
        n = int(res["MB"] * 1048576)
        tot["ok"] += 1; tot["bytes_ok"] += n; tot["seconds_ok"] += res["seconds"]
        state["verified"] += n
    else:
        tot["failed"].append(time.strftime("%H:%M:%S"))
        state["failed"] += 1
        state["wrong_bytes"] += int(res.get("wrong_bytes") or 0)
        state["bad_blocks"] += int(res.get("bad_blocks") or 0)
        t.progress["bytes"] = before           # do not count a failed transfer as transferred
        state["now"] = "recovering after a failed " + kind
        try:
            res["recovered_drained"] = t.recover()
        except Exception as exc:
            res["recover_exception"] = repr(exc)
    with open("soak-log.jsonl", "a") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, **res}, default=str) + "\n")
    return ok


threading.Thread(target=ticker, daemon=True).start()
streak, verdict = 0, "running"
while time.time() < deadline and verdict == "running":
    for kind in KINDS:
        if time.time() >= deadline:
            break
        streak = 0 if transfer(kind) else streak + 1
        summary(verdict)
        if streak >= 10:
            verdict = "ABORTED after 10 failures in a row"
            break
state["done"] = True
time.sleep(1.2)
print("\n" + summary("finished" if verdict == "running" else verdict))
