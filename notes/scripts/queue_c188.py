"""C188's queue (runs/probe/C188-head-out-signal/record.md, Amendments 1-4): W's recipe with --draft-out-bonus none (W0, the discriminator), plus --draft-size-neutral (W0S, Amendment 4's strongest version), and kl (WK, the form to adopt), seeds 48 and 49, to iteration 44. One launch at a time in ARMS's order: W0 s48, W0S s48, W0 s49, W0S s49, then WK. edit_slots.jsonl is required: rl.metagame refuses these flags without it. queue_c171's supervisor; stops as the record's: errors, wall kill, Pokemon slide, median Trainers at or under 15 at 3 reads, h_out - h(s = 0) at or under -0.4 at 3 reads, G1 watch off. Gamma, T - E and T's ratio at each read go to gamma.jsonl. Holds on GPU-PAUSE and row 73 in Screen.launch. queue_c187 and queue_c184 wait on these arms.
  .venv/Scripts/python notes/scripts/queue_c188.py [--chains-only]
"""
import json
import os
import subprocess
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

D = ROOT / "runs" / "probe" / "C188-head-out-signal"
Q.D = D
QC.D = D
RECORD = "runs/probe/C188-head-out-signal/record.md"
FLAGS = {"W0": "--draft-out-bonus none", "W0S": "--draft-out-bonus none --draft-size-neutral", "WK": "--draft-out-bonus kl", "WS": "--draft-size-neutral"}
RELEASE = D / "RELEASE-WS"                               # WS, bonus on and size-neutral credit (A167, Amendment 6), runs if W0 calls for it or once this file exists
WS_LINE = 1.15
LOCK, STARTED = threading.Lock(), set()
ARMS = [("C188-W0-s48", "W0", 48), ("C188-W0S-s48", "W0S", 48), ("C188-W0-s49", "W0", 49), ("C188-W0S-s49", "W0S", 49), ("C188-WK-s48", "WK", 48), ("C188-WK-s49", "WK", 49), ("C188-WS-s48", "WS", 48), ("C188-WS-s49", "WS", 49)]
QC.ARMS = ARMS
ITERS = 45
H_GAP_LINE = -0.4                                        # Amendment 2: h_out - h(s = 0) on the same decks
H_OUT_LINE = 2.5                                         # its fallback, if a row has no h_s0


def make_screens():
    out = {}
    for name, arm, seed in ARMS:
        run = ROOT / "runs" / "screens" / name
        run.mkdir(parents=True, exist_ok=True)
        (run / "NO_G1_WATCH").write_text("C188's record: the G1 watch prints and doesn't stop this run\n", encoding="utf-8")
        chain = Q168.CHAIN.format(name=name, seed=seed, iters=ITERS, flag=" --save-first", note=f", W's recipe with {FLAGS[arm]}").replace("runs/probe/C168-long-fresh-turnover/record.md", RECORD)
        assert chain.count("--draft-lr 0.0003") == 1
        (run / "chain.sh").write_text(chain.replace("--draft-lr 0.0003", f"--draft-lr 0.0003 {FLAGS[arm]} --edit-slots"), encoding="utf-8", newline="\n")
        out[name] = Q.Screen(name, "C188", RECORD, run, "prevention", "fresh", ["--components", arm] + (["--replicate-of", f"C188-{arm}-s48"] if seed == 49 else []))
    return out


P_LINE = 18.5                                            # Amendment 7: the Pokemon slide is median P above 18.5, outside 13.5 +- 5


def kill(rows):
    why = Q168.own_kill(rows, trainer_line=15, pokemon_over=P_LINE)
    if why:
        return why
    reads = [r["draft"] for r in rows if (r["iter"] + 1) % 5 == 0 and (r.get("draft") or {}).get("h_out") is not None][-3:]
    if len(reads) == 3 and all(d["h_out"] - d["h_s0"] <= H_GAP_LINE if "h_s0" in d else d["h_out"] < H_OUT_LINE for d in reads):
        return f"out-choice collapse: h_out - h(s = 0) at or under {H_GAP_LINE} (or h_out under {H_OUT_LINE}) at 3 reads in a row"
    return None


def gamma_reads(screens):
    """Amendment 2: gamma, T - E and T's whole-population ratio at each read, in a CPU subprocess so the GPU hiding stays out of this process."""
    f0 = D / "gamma.jsonl"                               # a restart doesn't repeat reads already written
    done = {(r["run"], r["iter"]) for r in (json.loads(x) for x in f0.read_text(encoding="utf-8").splitlines() if x.strip())} if f0.exists() else set()
    while True:
        for n, s in screens.items():
            for f in sorted(s.run.glob("population_it*.pt")):
                it = int(f.stem[-4:])
                if (n, it) not in done and ((it + 1) % 5 == 0 or it == 0):
                    done.add((n, it))
                    r = subprocess.run([Q.PY, "notes/scripts/c188_stage0.py", "--at", str(it), "--runs", n, "--jsonl", str(D / "gamma.jsonl")], cwd=ROOT, capture_output=True, text=True,
                                       env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": f".{os.pathsep}notes/scripts"})
                    Q.log(f"gamma read {n} at {it}: " + ((r.stdout.strip().splitlines() or [""])[-1] if r.returncode == 0 else f"failed {r.stderr[-200:]}"))
                    row = next((x for x in s.rows() if x["iter"] == it and x.get("head_mass")), None)      # A166: incoming Energy mass, W0S against W0, at every read
                    if row:
                        with open(D / "mass.jsonl", "a", encoding="utf-8") as f:
                            f.write(json.dumps({"run": n, "iter": it, **row["head_mass"]}) + "\n")
        time.sleep(60)


def start(screens, n):
    with LOCK:                                           # WS has two routes in; each arm launches once
        if n in STARTED:
            return
        STARTED.add(n)
    s = screens[n]
    if s.ended():                                        # a restart doesn't relaunch an arm that finished or was killed
        Q.log(f"{n}: ended before this queue start, not relaunched")
        return
    if not Q.alive(n):
        s.launch(resume=n in Q.reg())
    threading.Thread(target=s.watch, args=(kill,), daemon=True).start()


def resume_w0_s49(screens):
    """Amendment 7: W0 s49's stop at 40 stands as it happened; once W0S s49 has ended, it resumes from its checkpoint to 44
    under the new line, ahead of WK. Once only: a marker records the resume."""
    n, mark = "C188-W0-s49", D / "A7-W0-s49-resumed"
    s = screens[n]
    if mark.exists() or (s.run / "population_it0044.pt").exists():
        return
    while not screens["C188-W0S-s49"].ended():
        time.sleep(60)
    stop = s.run / "STOP"
    if stop.exists() and stop.read_text(encoding="utf-8").startswith("kill: Pokemon slide"):
        stop.rename(s.run / "STOP.amendment7-old")       # the queue's own kill STOP, kept beside
    mark.write_text(time.strftime("%Y-%m-%d %H:%M:%S") + " resumed from its checkpoint, Amendment 7\n", encoding="utf-8")
    Q.log(f"Amendment 7: {n} resumes from its checkpoint to 44 under the new Pokemon line")
    s.launch(resume=True)
    threading.Thread(target=s.watch, args=(kill,), daemon=True).start()


def ws_first(screens, path=None, wait=60, grace=10):
    """Amendment 6: True if W0's whole-population T ratio at 44 is at or under WS_LINE at both seeds; False if either is above it, or an arm ended with no read at 44."""
    path = path or D / "gamma.jsonl"
    names = [n for n, arm, _ in ARMS if arm == "W0"]
    passes = 0
    while True:
        rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.exists() else []
        read = {r["run"]: r["T_ratio"] for r in rows if r["run"] in names and r["iter"] == 44}
        if len(read) == len(names):
            return all(v <= WS_LINE for v in read.values())
        if all(screens[n].ended() for n in names):       # gamma_reads gets a few passes to catch up
            passes += 1
            if passes > grace:
                return False
        time.sleep(wait)


def in_order(screens):
    """One launch at a time: W0 and W0S in ARMS's order, WS next if W0 calls for it, then WK."""
    for n, arm, _ in ARMS:
        if arm in ("W0", "W0S"):
            start(screens, n)
    if ws_first(screens):
        Q.log(f"Amendment 6: W0's T ratio at or under {WS_LINE} at both seeds, WS goes ahead of WK")
        for n, arm, _ in ARMS:
            if arm == "WS":
                start(screens, n)
    resume_w0_s49(screens)                               # Amendment 7: W0 s49 takes W0S s49's slot, then WK
    for n, arm, _ in ARMS:
        if arm == "WK":
            start(screens, n)


def on_release(screens):
    """RELEASE-WS, an agent's: WS if W0S moves something (Amendment 6's other route), whatever W0 read."""
    while not RELEASE.exists():
        time.sleep(60)
    for n, arm, _ in ARMS:
        if arm == "WS":
            start(screens, n)


def main():
    screens = make_screens()
    if "--chains-only" in sys.argv:
        print("chains written:", list(screens))
        return
    Q.log("C188 queue start")
    threading.Thread(target=in_order, args=(screens,), daemon=True).start()
    threading.Thread(target=on_release, args=(screens,), daemon=True).start()
    threading.Thread(target=gamma_reads, args=(screens,), daemon=True).start()
    QC.supervise(screens)
    Q.log("C188 queue end")


if __name__ == "__main__":
    main()
