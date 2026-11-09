"""C168's queue (runs/probe/C168-long-fresh-turnover/record.md, with Amendments 1 to 4): arms N (--turnover-mutant) and W (C127's recipe) at seeds 50 and 51, 130 iterations, through
loop.py launch, pausable (queue_c90.Screen: runs/GPU-PAUSE writes pause to STOP; the chain resumes when it lifts). W s50, W s51 and N s50 start together; N s51 takes the first free slot (Amendment 4).
A readout goes to stages.jsonl every 15 iterations (a 30-minute stage). Kills: errors over 2% of an iteration's games; g1_watch in the chain; the Pokemon slide (median Pokemon at least 6
above its value at iteration 5) and the Trainer slide (median Trainers at or under 18), each at 3 reads in a row, a read being every fifth iteration; at 60, N - W on E over -0.01 at both
seeds stops the test, R-not-pinned, provisional (Amendment 2; it covers the record's wrong-way rule); at 90, N - W on E over -0.02 at both seeds stops the test, R-not-pinned. Amendment 3: an arm with a wall-signature
share of 25% or more at 3 saved reads in a row, from iteration 5, stops; if both N seeds do, the test reads R-walls for N, and W continues alone to 130. Amendment 4: at 60, E not below -0.024 at both W seeds stops W,
"pinned near the generator", provisional; the wall kill applies to W too.
Taken by default (row 115): until N s51 reaches an iteration, the cross reads use N s50 against both W seeds there, since N s51 may start hours later. QSTOP here stops the arms.
  .venv/Scripts/python notes/scripts/queue_c168.py        (through loop.py launch --kind probe)
  .venv/Scripts/python notes/scripts/queue_c168.py --chains-only
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

D = ROOT / "runs" / "probe" / "C168-long-fresh-turnover"
Q.D = D                                                  # queue_c90.log writes to D / log.txt
RECORD = "runs/probe/C168-long-fresh-turnover/record.md"
ARMS = [("C168-W-s50", "W", 50), ("C168-W-s51", "W", 51), ("C168-N-s50", "N", 50), ("C168-N-s51", "N", 51)]   # the first 3 start together
ITERS = 130
CHAIN = """#!/bin/sh
# {name} (runs/probe/C168-long-fresh-turnover/record.md): C127's chain{note} at --seed {seed}, {iters} iterations, one --resume; the G1 watch beside it every 60 s, as C127.
export PATH="/usr/bin:/bin:/mingw64/bin:$PATH"
cd "$(dirname "$0")/../../.." || exit 1
run=runs/screens/{name}
echo "{name} start $(date '+%F %T') iters {iters}"
RL_GPU_SHARE=0.25 RL_CPU_THREADS=5 .venv/Scripts/python.exe -m rl.metagame --run "$run" --iters {iters} --workers 5 \\
  --stop-file "$run/STOP" --games 2000 --record 500 --ppo-transitions 64000 --lr 0.0002 --swaps 6 --field-sample 4 \\
  --draft-lr 0.0003 --draft-ent 0.01 --draft-margin 0 --shaping 0.1 --shaping-iters 100 \\
  --turnover 0.15 --seed {seed} --save-every 5 --micro-batch 256 --epochs 2 \\
  --init-from runs/pilot/C49-sd/model_it00199.pt --init-wide --select --select-paired --draft-h-in-floor 3.0 --draft-group-p 0.3 \\
  --practice-games 250 --turnover-wide --protect 20 --type-cap 0.5 --turnover-every 5 --candidates 1 \\
  --round-turns 20-45 --draft-base features --card-ledger{flag} --resume >> "$run/stdout.log" 2>&1 &
pid=$!
while kill -0 $pid 2>/dev/null; do
  [ -f "$run/log.jsonl" ] && PYTHONPATH=. .venv/Scripts/python.exe notes/scripts/g1_watch.py "$run" --stop > "$run/g1watch.log" 2>&1
  sleep 60
done
wait $pid
rc=$?
grep -qs pause "$run/STOP" && {{ echo "{name} paused $(date '+%F %T')"; exit 5; }}   # GPU-PAUSE: resumed later with --resume
grep -qs g1watch "$run/STOP" && {{ echo "{name} STOPPED by the G1 watch $(date '+%F %T'): $(cut -c1-80 "$run/g1watch.log")"; echo "{name} end $(date '+%F %T')"; exit 6; }}
echo "{name} train end $(date '+%F %T') exit $rc"
echo "{name} end $(date '+%F %T')"
"""


def make_screens():
    out = {}
    for name, arm, seed in ARMS:
        run = ROOT / "runs" / "screens" / name
        run.mkdir(parents=True, exist_ok=True)
        flag = " --turnover-mutant" if arm == "N" else ""
        note = " with --turnover-mutant" if arm == "N" else " unchanged"
        (run / "chain.sh").write_text(CHAIN.format(name=name, seed=seed, iters=ITERS, flag=flag, note=note), encoding="utf-8", newline="\n")
        out[name] = Q.Screen(name, "C168", RECORD, run, "prevention", "fresh", ["--components", "turnover-mutant"] if arm == "N" else [])
    return out


def own_kill(rows, trainer_line=18, pokemon_over=None):
    """One arm's rules: a reason or None. pokemon_over (C188 Amendment 7): the slide is median Pokemon above this
    absolute line at 3 reads, in place of iteration 5's median plus 6; None keeps the old rule."""
    if any(r.get("errors", 0) > 0.02 * max(r.get("games", 1), 1) for r in rows):
        return "errors over 2% of an iteration's games"
    reads = [r for r in rows if (r["iter"] + 1) % 5 == 0]
    start = next((r for r in rows if r["iter"] == 5), None)
    last3 = reads[-3:]
    if pokemon_over is not None:
        if len(last3) == 3 and all(r["shape_quartiles"]["pokemon"][1] > pokemon_over for r in last3):
            return f"Pokemon slide: median Pokemon above {pokemon_over} at 3 reads in a row (C188 Amendment 7)"
    elif start and len(last3) == 3:
        p0 = start["shape_quartiles"]["pokemon"][1]
        if all(r["shape_quartiles"]["pokemon"][1] >= p0 + 6 for r in last3):
            return f"Pokemon slide: median Pokemon at or above {p0 + 6} at 3 reads in a row"
    if len(last3) == 3 and all(r["shape_quartiles"]["trainer"][1] <= trainer_line for r in last3):
        return f"Trainer slide: median Trainers at or under {trainer_line} at 3 reads in a row"
    return None


def cross_rules(screens, done):
    """The cross-arm stops at iterations 59 and 89 (60 and 90 done): runs once each, when both W seeds and N s50 have the saved population. Returns the arms to stop and why."""
    import c168_read as R
    ready = lambda name, it: (ROOT / "runs/screens" / name / f"population_it{it:04d}.pt").exists()
    tv = lambda name, it: R.stage(ROOT / "runs/screens" / name, it)
    stop, why = [], ""
    for it in (59, 89):
        if it in done or not (ready("C168-W-s50", it) and ready("C168-W-s51", it) and ready("C168-N-s50", it)):
            continue
        done.add(it)
        w = [tv("C168-W-s50", it), tv("C168-W-s51", it)]
        n50 = tv("C168-N-s50", it)
        n51 = tv("C168-N-s51", it) if ready("C168-N-s51", it) else n50
        d = [n50["population"]["E"] - w[0]["population"]["E"], n51["population"]["E"] - w[1]["population"]["E"]]
        we = [x["population"]["E"] for x in w]
        Q.log(f"cross read at {it + 1}: W E {we}; N - W E {[round(x, 4) for x in d]}; N s51 {'read' if ready('C168-N-s51', it) else 'not there yet: N s50 stands in'}")
        if it == 59 and all(x >= -0.024 for x in we):
            stop, why = ["C168-W-s50", "C168-W-s51"], "W pinned near the generator at 60: E not below -0.024 at both W seeds; provisional"
        if it == 59 and all(x > -0.01 for x in d):
            stop, why = [a[0] for a in ARMS], "stop at 60: N - W on E over -0.01 at both seeds; reads R-not-pinned, provisional"
        elif it == 89 and all(x > -0.02 for x in d):
            stop, why = [a[0] for a in ARMS], "no progress at 90: N - W on E over -0.02 at both seeds; reads R-not-pinned"
        if stop:
            return stop, why
    return [], ""


def wall_kills(screens, cache, walled):
    """Amendment 3, read from every saved population at or after iteration 5 (saves come at 4, 9, 14, ...; iteration 4 is the fifth)."""
    import c168_read as R
    for n, s in screens.items():
        if n in walled or not s.run.exists():
            continue
        c = cache.setdefault(n, {})
        for i in R.saved(s.run):
            if i >= 4 and i not in c:
                c[i] = R.wall_share([x["deck"] for x in R.snapshot(s.run, i)])
        last = [c[i] for i in sorted(c)[-3:]]
        if len(last) == 3 and all(x >= 0.25 for x in last):
            walled.add(n)
            why = f"walls: wall-signature share {[round(x, 3) for x in last]} at 3 reads in a row"
            f = s.run / "STOP"
            if not f.exists():
                f.write_text(f"kill: {why}\n")
            Q.log(f"STOP {n}: {why}")
            if {"C168-N-s50", "C168-N-s51"} <= walled:
                Q.log("both N seeds walled: the test reads R-walls for N, and W continues alone to 130")


def supervise(screens):
    """Readouts every 15 iterations, the cross-arm stops, the wall kill, QSTOP."""
    import c168_read as R
    done, read, cache, walled = set(), {n: -1 for n in screens}, {}, set()
    while True:
        try:
            wall_kills(screens, cache, walled)
        except Exception as e:
            Q.log(f"wall read failed: {e!r}"[:200])
        for n, s in screens.items():
            have = [i for i in R.saved(s.run) if (i + 1) % 15 == 0 and i > read[n]] if s.run.exists() else []
            for i in have:
                try:
                    with open(D / "stages.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(R.stage(s.run, i)) + "\n")
                    Q.log(f"stage read: {n} at iteration {i}")
                except Exception as e:
                    Q.log(f"stage read failed: {n} {i}: {e!r}"[:200])
                read[n] = i
        try:
            stop, why = cross_rules(screens, done)
        except Exception as e:
            stop, why = [], ""
            Q.log(f"cross read failed: {e!r}"[:200])
        if (D / "QSTOP").exists():
            stop, why = [a[0] for a in ARMS], "QSTOP"
        for n in stop:
            f = screens[n].run / "STOP"
            if not f.exists():
                f.write_text(f"kill: {why}\n")
                Q.log(f"STOP {n}: {why}")
        if all(s.ended() for s in screens.values()):
            Q.log("all arms ended")
            return
        time.sleep(60)


def arm(s, kill):
    s.launch()
    s.watch(kill)


def main():
    screens = make_screens()
    if "--chains-only" in sys.argv:
        print("chains written:", list(screens))
        return
    Q.log("C168 queue start")
    ts = [threading.Thread(target=arm, args=(s, own_kill), daemon=True) for s in screens.values()]
    for t in ts[:3]:
        t.start()
        time.sleep(90)                                   # loading: a launch's GPU reading settles
    ts[3].start()                                        # Screen.launch retries while the slots are full
    supervise(screens)
    for t in ts:
        t.join(timeout=120)
    Q.log("C168 queue end")


if __name__ == "__main__":
    main()
