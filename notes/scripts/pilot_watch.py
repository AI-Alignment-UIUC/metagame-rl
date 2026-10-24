"""Looks and stop rules for a pilot fork (C45, runs/pilot/C45/record.md, log #161; from notes/scripts/c30_cont_watch.py,
log #158). Evaluation and control only; training never reads any of it.

  every --poll seconds: deck-outs (mean of the last 3 iterations) at or above --stall write the stop file (stall learned)
  at each look (model_it000{39,59,79,99,119}.pt): JF1 (probe_matchups.py, 3 walls x 24 lists, 32 a pair, seed 11) and
             rl.lab h2h against pilot-v2 on the 24 lists (276 pairs) and on the 64 held-out wide decks (500 pairs)
  competent: lists Elo at or above --competent (-30) at a look writes the stop file (H5 / H1 read at that look)
  no transfer: lists Elo gain over --base-elo below --min-gain (100) at the --gain-look (79) writes the stop file
  with --rule R: also JF1 and the lists h2h under the 2000 round rule (R "T" or "A-B"; log #160), JF1's "sts" the walls'
             share of the event points
  pair kill: with --pair-looks (the other fork's looks.jsonl), at --pair-look this run's lists Elo minus the other's
             at or below --pair-kill writes the stop file
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


def look(ck: Path, it: int, out: Path, workers: int, rule: str = "") -> dict:
    log = out / "looks.log"
    r = {"iteration": it}
    if rule:
        run([PY, "notes/scripts/probe_matchups.py", "--pilot", str(ck), "--a", "runs/probe/walls_resetcap499.json",
             "--b", "archived", "--games", "32", "--workers", str(workers), "--seed", "11", "--round-turns", rule,
             "--out", str(out / f"jf1r_it{it}.json")], log)
        run([PY, "-m", "rl.lab", "h2h", "--a", str(ck), "--b", V2, "--panel", "archived", "--seed", "0", "--cap", "276",
             "--fixed", "--workers", str(workers), "--elo0", "-20", "--elo1", "20", "--round-turns", rule,
             "--out", str(out / f"h2h_listsr_it{it}.json")], log)
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
        if rule:
            j = json.loads((ROOT / out / f"jf1r_it{it}.json").read_text())
            r["jf1_rule"] = {"plain": j["mean"], "sts": j.get("sts"), "endings": j.get("endings")}
            h = json.loads((ROOT / out / f"h2h_listsr_it{it}.json").read_text())
            r["lists_rule"] = {k: h[k] for k in ("score", "elo", "elo_lo", "elo_hi", "games", "errors")}
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
    ap.add_argument("--looks", default="139,159,179,199")
    ap.add_argument("--competent", type=float, default=-30.0)
    ap.add_argument("--rule", default="")
    ap.add_argument("--pair-looks", default="")
    ap.add_argument("--pair-look", type=int, default=159)
    ap.add_argument("--pair-kill", type=float, default=-80.0)
    ap.add_argument("--lock", default="", help="a lock file shared by the forks' watchers")
    ap.add_argument("--entropy-ref", default="", help="the control's log.jsonl: entropy at least --entropy-kill above it "
                                                       "(mean of the last 5 shared iterations) writes the stop file")
    ap.add_argument("--entropy-kill", type=float, default=0.15)
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
        lj = run_dir / "log.jsonl"                       # written from the fork's first iteration on
        rows = [json.loads(x) for x in lj.read_text().splitlines() if x.strip()] if lj.exists() else []
        rows = [r for r in rows if "endings" in r]
        if len(rows) >= 3:
            d = [r["endings"].get("deck-out", 0) / max(1, sum(r["endings"].values())) for r in rows[-3:]]
            if sum(d) / 3 >= a.stall:
                write_stop(f"stall: deck-outs {sum(d) / 3:.3f} over iterations {rows[-3]['iteration']}-{rows[-1]['iteration']}")
        if a.entropy_ref and len(rows) >= 5 and (ROOT / a.entropy_ref).exists():
            ref = {r["iteration"]: r["entropy"] for r in (json.loads(x) for x in (ROOT / a.entropy_ref).read_text().splitlines()
                                                          if x.strip()) if "entropy" in r}
            both = [r for r in rows if r["iteration"] in ref][-5:]
            if len(both) == 5:
                d = sum(r["entropy"] - ref[r["iteration"]] for r in both) / 5
                if d >= a.entropy_kill:
                    write_stop(f"entropy {d:+.3f} above the control over iterations {both[0]['iteration']}-{both[-1]['iteration']}")
        ck = run_dir / f"model_it{todo[0]:05d}.pt"
        if ck.exists():
            time.sleep(5)                                    # let the save finish
            it = todo.pop(0)
            lock = ROOT / a.lock if a.lock else None      # one look at a time across forks (the GPU and CPU caps)
            while lock is not None:
                try:
                    os.close(os.open(lock, os.O_CREAT | os.O_EXCL)); break
                except FileExistsError:
                    time.sleep(30)
            say(f"look at {it}")
            try:
                r = look(ck.relative_to(ROOT), it, out, a.workers, a.rule)
            finally:
                if lock is not None:
                    lock.unlink(missing_ok=True)
            with open(res, "a", encoding="utf-8") as f:
                f.write(json.dumps(r) + "\n")
            say(json.dumps(r))
            elo = r.get("lists", {}).get("elo")
            if elo is not None and elo >= a.competent:
                write_stop(f"competent: lists Elo {elo} at {it}")
            if a.pair_looks and it == a.pair_look and elo is not None:
                pair = ROOT / a.pair_looks
                for _ in range(240):                         # the other fork's look at the same iteration (up to 4 h)
                    rows = [json.loads(x) for x in pair.read_text().splitlines() if x.strip()] if pair.exists() else []
                    other = [x for x in rows if x.get("iteration") == it and "lists" in x]
                    if other:
                        d = elo - other[0]["lists"]["elo"]
                        say(f"pair: lists Elo {elo} vs {other[0]['lists']['elo']}, difference {d:.1f}")
                        if d <= a.pair_kill:
                            write_stop(f"pair kill: lists Elo {d:.1f} below the other fork at {it}")
                        break
                    time.sleep(60)
            continue
        if done.exists():
            say(f"training done; looks not reached: {todo}")
            break
        time.sleep(a.poll)


if __name__ == "__main__":
    main()
