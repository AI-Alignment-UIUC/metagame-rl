"""Seed 2 of C90 and its control C85 (C90's record: "between" with G3 up, so seed 2; log #299). Their chains with
--seed 2 and an -s2 name, launched each in its own thread through loop.py launch (retried while the slots are full)
and watched pausable through queue_c90's Screen; C90-s2 keeps its record's kill rule. Logs to C90-pairedselect/log.txt.
"""
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
from queue_c90 import Screen, c90_kill, log            # noqa: E402

ARMS = [("C90-R1-K-base-paired", "C90", "runs/probe/C90-pairedselect/record.md", c90_kill),
        ("C85-R1-K-base", "C85", "runs/screens/C85-R1-K-base/record.md", None)]


def seed2(name, cand, record, kill):
    new = f"{name}-s2"
    run = ROOT / "runs" / "screens" / new
    run.mkdir(parents=True, exist_ok=True)
    text = (ROOT / "runs" / "screens" / name / "chain.sh").read_text(encoding="utf-8")
    assert text.count("--seed 1 ") == 1, f"{name}'s chain should hold one --seed 1"
    (run / "chain.sh").write_text(text.replace(name, new).replace("--seed 1 ", "--seed 2 "), encoding="utf-8", newline="\n")
    x = Screen(new, cand, record, run, "prevention", "fresh", ["--evan-row", "78", "--replicate-of", name])
    if not (run / "launch.log").exists():
        x.launch()
    x.watch(kill)


def main():
    threads = []
    for arm in ARMS:                                     # C90-s2 asks for the free slot first; C85-s2 retries until one frees
        threads.append(threading.Thread(target=seed2, args=arm))
        threads[-1].start()
        threading.Event().wait(5)
    for t in threads:
        t.join()
    log("seed 2s done")


if __name__ == "__main__":
    main()
