"""C93 (runs/screens/C93-gate-fresh-s34/record.md, log #310-#311): C85's and C90's chains with --seed 3, then --seed 4,
each --replicate-of its seed-1 name; nothing else changes. After C92 s2 ends, as side-by-side pairs (C85-s3 with
C90-s3, then C85-s4 with C90-s4), each launch retried while loop.py refuses, watched pausable through queue_c90's Screen
with the record's kill rule. Nothing first starts after 08:30 (it waits for Evan's go). Logs to C90-pairedselect/log.txt.
"""
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
from queue_c90 import Screen, log                      # noqa: E402

S = ROOT / "runs" / "screens"
ARMS = ("C85-R1-K-base", "C90-R1-K-base-paired")
RECORD = "runs/screens/C93-gate-fresh-s34/record.md"
DEADLINE = datetime.now().replace(hour=8, minute=30, second=0, microsecond=0).timestamp()


def kill(rows):
    """The record: errors over 2% of an iteration's games; the move rate at 0 for 10 counted iterations in a row."""
    if any(r.get("errors", 0) > 0.02 * max(r.get("games", 1), 1) for r in rows):
        return "errors over 2%"
    moved = [(r.get("select") or {}).get("moved") for r in rows if r.get("counted") and "moved" in (r.get("select") or {})]
    if len(moved) >= 10 and not any(moved[-10:]):
        return "0 moves for 10 counted iterations"


def screen(name, seed) -> Screen:
    new = f"{name}-s{seed}"
    run = S / new
    run.mkdir(parents=True, exist_ok=True)
    text = (S / name / "chain.sh").read_text(encoding="utf-8")
    assert text.count("--seed 1 ") == 1, f"{name}'s chain should hold one --seed 1"
    (run / "chain.sh").write_text(text.replace(name, new).replace("--seed 1 ", f"--seed {seed} "), encoding="utf-8",
                                  newline="\n")
    return Screen(new, "C93", RECORD, run, "prevention", "fresh", ["--evan-row", "78", "--replicate-of", name])


def go(x: Screen):
    if (x.run / "launch.log").exists() or x.launch(deadline=DEADLINE):
        x.watch(kill)


def main():
    c92 = Screen("C92-p479fresh-s2", "C92", "", S / "C92-p479fresh" / "s2", "prevention", "fresh")
    log("C93 waiting for C92 s2")
    while not c92.ended():
        time.sleep(120)
    for seed in (3, 4):
        pair = [screen(n, seed) for n in ARMS]
        threads = [threading.Thread(target=go, args=(x,)) for x in pair]
        for t in threads:
            t.start()
            time.sleep(5)
        for t in threads:
            t.join()
    log("C93 done")


if __name__ == "__main__":
    main()
