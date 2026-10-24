"""C30's continuation of W2 (runs/pilot/C30/record-cont.md, log #158): looks and stop rules for an rl.train run resumed
past the warm-up. Evaluation and control only; training never reads any of it.

  every --poll seconds: deck-outs (mean of the last 3 iterations) at or above --stall write the stop file (stall learned)
  at each look (model_it000{39,59,79,99,119}.pt): JF1 (probe_matchups.py, 3 walls x 24 lists, 32 a pair, seed 11) and
             rl.lab h2h against pilot-v2 on the 24 lists (276 pairs) and on the 64 held-out wide decks (500 pairs)
  competent: lists Elo at or above --competent (-30) at a look writes the stop file (H5 / H1 read at that look)
  no transfer: lists Elo gain over --base-elo below --min-gain (100) at the --gain-look (79) writes the stop file
  The run's chain touches --done when training exits; the watcher then finishes any look left and exits.

  .venv/Scripts/python notes/scripts/c30_cont_watch.py runs/pilot/C30-h99-scratch-s2 --stop-file .../STOP-cont \
      --done .../TRAIN-DONE --out runs/pilot/C30/eval-cont
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = str(ROOT / ".venv/Scripts/python.exe")
V2 = "runs/pilot-v2/model_it00349.pt"


def run(cmd, log):
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"$ {' '.join(cmd)}\n"); f.flush()
        rc = subprocess.call(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                             env={**os.environ, "RL_GPU_SHARE": "0.15"})
    return rc


def look(ck: Path, it: int, out: Path, workers: int) -> dict:
    log = out / "looks.log"
    r = {"iteration": it}
    run([PY, "notes/scripts/probe_matchups.py", "--pilot", str(ck), "--a", "runs/probe/walls_resetcap499.json",
         "--b", "archived", "--games", "32", "--workers", str(workers), "--seed", "11",
         "--out", str(out / f"jf1_it{it}.json")], log)
    for panel, cap, tag in (("archived", 276, "lists"), ("runs/pilot/C30/heldout_decks.json", 500, "heldout")):
        run([PY, "-m", "rl.lab", "h2h", "--a", str(ck), "--b", V2, "--panel", panel, "--seed", "0", "--cap", str(cap),
             "--fixed", "--workers", str(workers), "--elo0", "-20", "--elo1", "20",
             "--out", str(out / f"h2h_{tag}_it{it}.json")], log)
    try:
        j = json.loads((ROOT / out / f"jf1_it{it}.json").read_text())
        r["jf1"] = j["mean"]; r["walls_endings"] = {k: v[0] for k, v in j.get("endings_by_winner", {}).items()}
        for tag in ("lists", "heldout"):
            h = json.loads((ROOT / out / f"h2h_{tag}_it{it}.json").read_text())
            r[tag] = {k: h[k] for k in ("score", "elo", "elo_lo", "elo_hi", "games", "errors")}
    except (OSError, KeyError, ValueError) as e:
        r["error"] = repr(e)
    return r


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--stop-file", required=True)
    ap.add_argument("--done", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--looks", default="39,59,79,99,119")
    ap.add_argument("--base-elo", type=float, default=-448.8)       # W2 it19 on the lists (log #157)
    ap.add_argument("--competent", type=float, default=-30.0)
    ap.add_argument("--min-gain", type=float, default=100.0)
    ap.add_argument("--gain-look", type=int, default=79)
    ap.add_argument("--stall", type=float, default=0.30)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--poll", type=float, default=60.0)
    a = ap.parse_args(argv)
    run_dir, stop, done, out = ROOT / a.run, Path(a.stop_file), Path(a.done), Path(a.out)
    (ROOT / out).mkdir(parents=True, exist_ok=True)
    todo = [int(x) for x in a.looks.split(",")]
    res = ROOT / out / "looks.jsonl"

    def say(msg):
        print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)

    def write_stop(why):
        if not stop.exists():
            stop.write_text(why + "\n"); say(f"STOP: {why}")

    while todo:
        rows = [json.loads(x) for x in (run_dir / "log.jsonl").read_text().splitlines() if x.strip()]
        rows = [r for r in rows if "endings" in r]
        if len(rows) >= 3:
            d = [r["endings"].get("deck-out", 0) / max(1, sum(r["endings"].values())) for r in rows[-3:]]
            if sum(d) / 3 >= a.stall:
                write_stop(f"stall: deck-outs {sum(d) / 3:.3f} over iterations {rows[-3]['iteration']}-{rows[-1]['iteration']}")
        ck = run_dir / f"model_it{todo[0]:05d}.pt"
        if ck.exists():
            time.sleep(5)                                    # let the save finish
            it = todo.pop(0)
            say(f"look at {it}")
            r = look(ck.relative_to(ROOT), it, out, a.workers)
            with open(res, "a", encoding="utf-8") as f:
                f.write(json.dumps(r) + "\n")
            say(json.dumps(r))
            elo = r.get("lists", {}).get("elo")
            if elo is not None and elo >= a.competent:
                write_stop(f"competent: lists Elo {elo} at {it}")
            if it == a.gain_look and elo is not None and elo - a.base_elo < a.min_gain:
                write_stop(f"no transfer: lists Elo {elo} at {it}, gain {elo - a.base_elo:.1f} < {a.min_gain}")
            continue
        if done.exists():
            say(f"training done; looks not reached: {todo}")
            break
        time.sleep(a.poll)


if __name__ == "__main__":
    main()
