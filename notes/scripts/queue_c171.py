"""C171's queue (runs/probe/C171-table-drafting/record.md, with Amendment 1): B (the chosen table at kappa 3 on initial and turnover wide decks and the head's proposals) and W (C127's recipe, C168's W) at seeds 48 and 49, through loop.py launch, pausable (queue_c90.Screen). B s48, B s49 and W s48 start together; W s49 takes the first
free slot (with --arms, each arm's seeds in turn). B runs 60 iterations, W 130 (C168's long read). Each stage (15 iterations) writes a read to stages.jsonl; G3 probes at iterations 0, 14, 29, 59. Kills: errors over 2%; g1_watch in the chain; the Pokemon slide (median Pokemon at least 6 above its value at iteration 5, 3 reads in a row, a read being every fifth iteration); the wall signature at 25% or more,
3 saved reads in a row; no progress at 30 (B's G3 under W's + 0.04 at both seeds stops B); and W's own, from C168: the Trainer slide, and at 60, E not below -0.024 at both W seeds stops W. Taken by default (row 115): W s48 stands in for W s49 until it reaches an iteration. QSTOP stops the arms. A (proposals only) runs after B's read at 30, launched by hand.
  .venv/Scripts/python notes/scripts/queue_c171.py        (through loop.py launch --kind probe)
  .venv/Scripts/python notes/scripts/queue_c171.py --chains-only
--only NAME runs that one arm. --arms W runs only the control (W s48 and W s49 together), while B holds on the plain-or-concentrated rule; --arms B then runs B, reading W's G3 from its files, and a later --arms A is launched by hand.
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

D = ROOT / "runs" / "probe" / "C171-table-drafting"
Q.D = D
RECORD = "runs/probe/C171-table-drafting/record.md"
ARMS = [("C171-B-s48", "B", 48), ("C171-B-s49", "B", 49), ("C171-W-s48", "W", 48), ("C171-W-s49", "W", 49)]   # the first 3 start together
ITERS = {"B": 60, "W": 130}


def make_screens(which="BW"):
    chosen = json.loads((D / "chosen.json").read_text(encoding="utf-8")) if "B" in which else {}
    out = {}
    for name, arm, seed in ARMS:
        if arm not in which:
            continue
        run = ROOT / "runs" / "screens" / name
        run.mkdir(parents=True, exist_ok=True)
        flag = f" --table {chosen[str(seed)]} --table-kappa 3 --table-scope all --save-first" if arm == "B" else " --save-first"
        note = " with the chosen table at kappa 3, init, turnover and proposals" if arm == "B" else " unchanged, C168's W"
        (run / "chain.sh").write_text(Q168.CHAIN.format(name=name, seed=seed, iters=ITERS[arm], flag=flag, note=note).replace("runs/probe/C168-long-fresh-turnover/record.md", RECORD), encoding="utf-8", newline="\n")
        out[name] = Q.Screen(name, "C171", RECORD, run, "prevention", "fresh", (["--components", "table"] if arm == "B" else []) + (["--replicate-of", "C171-W-s48"] if name == "C171-W-s49" else []) + (["--replicate-of", "C171-B-s48"] if name == "C171-B-s49" else []))
    return out


def b_kill(rows):
    if any(r.get("errors", 0) > 0.02 * max(r.get("games", 1), 1) for r in rows):
        return "errors over 2% of an iteration's games"
    reads = [r for r in rows if (r["iter"] + 1) % 5 == 0]
    start = next((r for r in rows if r["iter"] == 5), None)
    last3 = reads[-3:]
    if start and len(last3) == 3:
        p0 = start["shape_quartiles"]["pokemon"][1]
        if all(r["shape_quartiles"]["pokemon"][1] >= p0 + 6 for r in last3):
            return f"Pokemon slide: median Pokemon at or above {p0 + 6} at 3 reads in a row"
    return None


def supervise(screens):
    """Stage reads every 15 iterations, the G3 probes, the wall kill, no progress at 30, W's stop at 60, QSTOP."""
    import c168_read as R
    import c171_read as C
    seed_of = {a[0]: a[2] for a in ARMS}
    read, g3_done, cache, walled, done = {n: -1 for n in screens}, set(), {}, set(), set()
    f0 = D / "stages.jsonl"                              # a restart doesn't repeat stage reads already written
    for x in (f0.read_text(encoding="utf-8").splitlines() if f0.exists() else []):
        if x.strip():
            r = json.loads(x)
            if r.get("run") in read:
                read[r["run"]] = max(read[r["run"]], r["iter"])
    g3m = {}
    run_of = lambda n: ROOT / "runs" / "screens" / n
    ready = lambda n, it: (run_of(n) / f"population_it{it:04d}.pt").exists()
    while True:
        try:
            Q168.wall_kills(screens, cache, walled)
        except Exception as e:
            Q.log(f"wall read failed: {e!r}"[:200])
        for n, s in screens.items():
            have = [i for i in R.saved(s.run) if (i + 1) % 15 == 0 and i > read[n]] if s.run.exists() else []
            for i in have:
                try:
                    with open(D / "stages.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(C.stage(s.run, i, seed_of[n])) + "\n")
                    Q.log(f"stage read: {n} at iteration {i}")
                except Exception as e:
                    Q.log(f"stage read failed: {n} {i}: {e!r}"[:200])
                read[n] = i
            for it in (0, 14, 29, 44, 59, 74, 89, 104, 119):      # research's #839: past 59 too, for W's G3 stop; 44 for C182's read
                if (n, it) not in g3_done and ready(n, it):
                    free, _ = Q.loop.ram_gb()                # a probe adds about 3 GB of RAM and 2.4 GB of GPU memory: wait for room (row 73), and try again next pass
                    g = Q.loop.gpu_mem()
                    if free < 4 or not g or g[0] + 2.4 > 0.8 * g[1] or Q.GPU_PAUSE.exists():
                        continue
                    g3_done.add((n, it))
                    try:
                        r = C.g3_reads(s.run, it, start=it == 0)
                        g3m.setdefault(n, {})[it] = r["C49"]["M"]
                        Q.log(f"G3 {n} at {it}: " + json.dumps({k: v for k, v in r.items() if k != 'top_name_left_out'}) + " top name out " + json.dumps(r["top_name_left_out"]))
                    except Exception as e:
                        Q.log(f"G3 failed: {n} {it}: {e!r}"[:200])
        stop, why = [], ""
        for n, m in g3m.items():                             # research's #839: G3 under C49-sd not above its previous read at 2 stages running, from 59 on
            v = [m[i] for i in sorted(m) if i >= 59]
            if n.startswith("C171-W") and len(v) >= 3 and v[-1] <= v[-2] <= v[-3]:
                stop, why = [n], f"G3 under C49-sd not above its previous read at 2 stages running: {v[-3:]}"
        # no progress at 30 (B against W at the same seed; W s48 stands in until W s49 is there)
        if "no30" not in done and "C171-B-s48" in screens and all((n, 29) in g3_done for n in ("C171-B-s48", "C171-B-s49")) and ready("C171-W-s48", 29):
            done.add("no30")
            try:
                g = {n: C.g3_reads(run_of(n), 29)["C49"]["M"] for n in ("C171-B-s48", "C171-B-s49", "C171-W-s48")}
                w49 = C.g3_reads(run_of("C171-W-s49"), 29)["C49"]["M"] if ready("C171-W-s49", 29) else g["C171-W-s48"]
                d = [g["C171-B-s48"] - g["C171-W-s48"], g["C171-B-s49"] - w49]
                Q.log(f"G3 B - W at 30: {[round(x, 4) for x in d]}; W s49 {'read' if ready('C171-W-s49', 29) else 'not there yet: W s48 stands in'}")
                if all(x < 0.04 for x in d):
                    stop, why = ["C171-B-s48", "C171-B-s49"], "no progress at 30: B's G3 under W's + 0.04 at both seeds"
            except Exception as e:
                Q.log(f"G3 at 30 failed: {e!r}"[:200])
        # W's stop at 60, from C168's Amendment 4
        if "w60" not in done and "C171-W-s48" in screens and ready("C171-W-s48", 59) and ready("C171-W-s49", 59):
            done.add("w60")
            we = [R.stage(screens[n].run, 59)["population"]["E"] for n in ("C171-W-s48", "C171-W-s49")]
            Q.log(f"W's E at 60: {we}")
            if all(x >= -0.024 for x in we):
                stop, why = ["C171-W-s48", "C171-W-s49"], "W pinned near the generator at 60: E not below -0.024 at both seeds; provisional"
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
    hold = D / f"HOLD-{s.name}"                          # research's #781: C172 goes ahead of W s49; the file's removal lets it launch
    while hold.exists():
        time.sleep(30)
    if not Q.alive(s.name):                              # a restarted queue picks up a run that's already going, and resumes one that's registered
        s.launch(resume=s.name in Q.reg())
    s.watch(kill)


def main():
    which = sys.argv[sys.argv.index("--arms") + 1] if "--arms" in sys.argv else "BW"
    screens = make_screens(which)
    if "--only" in sys.argv:                             # a single arm, since a run its own stop rule ended must not be relaunched (W s48, by the G1 watch)
        keep = sys.argv[sys.argv.index("--only") + 1]
        screens = {n: s for n, s in screens.items() if n == keep}
    if "--chains-only" in sys.argv:
        print("chains written:", list(screens))
        return
    Q.log("C171 queue start")
    kills = {"B": b_kill, "W": lambda rows: Q168.own_kill(rows, trainer_line=15)}   # research's #840: W is exploratory, its Trainer line 15
    ts = [threading.Thread(target=arm, args=(screens[n], kills[a]), daemon=True) for n, a, _ in ARMS if n in screens]
    for t in ts:                                         # Screen.launch retries while the slots are full
        t.start()
        time.sleep(90)
    supervise(screens)
    for t in ts:
        t.join(timeout=120)
    Q.log("C171 queue end")


if __name__ == "__main__":
    main()
