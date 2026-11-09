"""C191's queue (runs/probe/C191-energy-start-bracket/record.md): WL, W's recipe (C171-W's command, out bonus and credit as W)
plus --init-e-range 10-14 --edit-slots, seeds 52 and 53, to iteration 44; wide decks at init and turnover rejection-sampled
to 10-14 basic plus special Energy. Launches once C188's W0 s49 and W0S s49 are both up (alive, or finished at 44), s52 then
s53, beside C184's WR s50, s51. queue_c171's supervisor (stage reads at 14, 29, 44, the G3 probes, the wall kill). Kills, as
the record's: errors over 2% of an iteration's games; the wall signature; row 73's holds and GPU-PAUSE in Screen.launch.
Stop at 29: WL's summed edit drift through 29, sum of select.moved x select.acc[E] / D, within +-0.5 copies at both seeds.
  .venv/Scripts/python notes/scripts/queue_c191.py [--chains-only]
"""
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import queue_c90 as Q                                    # noqa: E402
import queue_c168 as Q168                                # noqa: E402
import queue_c171 as QC                                  # noqa: E402

D = ROOT / "runs" / "probe" / "C191-energy-start-bracket"
Q.D = D
QC.D = D
RECORD = "runs/probe/C191-energy-start-bracket/record.md"
ARMS = [("C191-WL-s52", "WL", 52), ("C191-WL-s53", "WL", 53)]
QC.ARMS = ARMS
ITERS = 45
AFTER = ("C188-W0-s49", "C188-W0S-s49")
FLAGS = " --init-e-range 10-14 --edit-slots"


def make_screens():
    out = {}
    for name, _, seed in ARMS:
        run = ROOT / "runs" / "screens" / name
        run.mkdir(parents=True, exist_ok=True)
        (run / "NO_G1_WATCH").write_text("C191's record: the G1 watch prints and doesn't stop this run\n", encoding="utf-8")
        chain = Q168.CHAIN.format(name=name, seed=seed, iters=ITERS, flag=" --save-first", note=", W's recipe with --init-e-range 10-14").replace("runs/probe/C168-long-fresh-turnover/record.md", RECORD)
        assert chain.count("--draft-lr 0.0003") == 1
        (run / "chain.sh").write_text(chain.replace("--draft-lr 0.0003", "--draft-lr 0.0003" + FLAGS), encoding="utf-8", newline="\n")
        out[name] = Q.Screen(name, "C191", RECORD, run, "prevention", "fresh", ["--components", "init-e-range"] + (["--replicate-of", "C191-WL-s52"] if seed == 53 else []))
    return out


def kill(rows):
    if any(r.get("errors", 0) > 0.02 * max(r.get("games", 1), 1) for r in rows):
        return "errors over 2% of an iteration's games"
    return None


def drift(name, upto):
    """Sum over iterations 0..upto of select.moved x select.acc[E] / D, or None if the log hasn't reached upto."""
    f = ROOT / "runs" / "screens" / name / "log.jsonl"
    rows = {}
    for l in (f.read_text(encoding="utf-8").splitlines() if f.exists() else []):
        if l.strip():
            r = json.loads(l)
            rows[r["iter"]] = r
    if upto not in rows:
        return None
    tot = 0.0
    for i in range(upto + 1):
        s = rows[i].get("select") or {}
        if s.get("acc"):
            tot += s["moved"] * s["acc"][2] / 99
    return tot


def stop_at_29(screens):
    """The record's stop: both seeds' drift through 29 within +-0.5, read once both have reached 29."""
    while True:
        d = {n: drift(n, 29) for n, _, _ in ARMS}
        if all(v is not None for v in d.values()):
            Q.log(f"C191 drift through 29: {json.dumps({k: round(v, 3) for k, v in d.items()})}")
            if all(abs(v) <= 0.5 for v in d.values()):
                for n in d:
                    (ROOT / "runs" / "screens" / n / "STOP").write_text("C191 stop at 29: summed drift within +-0.5 at both seeds (R-flat early)\n", encoding="utf-8")
                Q.log("C191 stop at 29: R-flat early, both arms stopped")
            return
        if all(screens[n].ended() for n, _, _ in ARMS):
            return
        time.sleep(60)


C193_FIRST = "C193-s1-gate"                              # C193 Amendment 2: WL holds until C193's stage 1 has launched (registered)


def in_order(screens):
    while not all(Q.alive(a) or (ROOT / f"runs/screens/{a}/population_it0044.pt").exists() for a in AFTER):
        time.sleep(60)
    while C193_FIRST not in Q.reg():
        time.sleep(60)
    Q.log(f"C193 Amendment 2: {C193_FIRST} is registered, WL may launch")
    for n, _, _ in ARMS:
        s = screens[n]
        if not Q.alive(n):
            s.launch(resume=n in Q.reg())
        threading.Thread(target=s.watch, args=(kill,), daemon=True).start()
    stop_at_29(screens)


def main():
    screens = make_screens()
    if "--chains-only" in sys.argv:
        print("chains written:", list(screens))
        return
    Q.log("C191 queue start")
    threading.Thread(target=in_order, args=(screens,), daemon=True).start()
    QC.supervise(screens)
    Q.log("C191 queue end")


if __name__ == "__main__":
    main()
