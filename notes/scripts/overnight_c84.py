"""C84 (log #271): tonight's decisions after the seed-1 arms, by 333-10's rule of 2026-10-26 17:05. Runs as one probe
through loop.py launch (runs/probe/C84-overnight/), after C81 and C83 have ended.

0. C87 (333-10, 19:20, after C83 p23 lost): card-token key 1 alone at 110 iterations, seed 1, with X1, trained here
   first; p23-key1 is not run. Then C88 (log #278: p23 with Q's target at the seat's next turn) the same way, then any
   arm in extra_arms.json here (C89 once Evan says yes to decision 1 and it is built). C88's (and C89's) record bands
   on the named-5 dG also give seed 2 ("fixes the direction", or "between" with dG > 0).
1. Each seed-1 arm (C81 chain + credit, chain; C83 p23; C87 key1) against C81 base s1: M - base on fresh deals, X1
   (U - G on search/disrupt/tempo) against base's, and the A1 replay's dG. An arm gained (333-10, 19:20: losses get no
   seed 2) if M - base >= +0.01, X1 - base's <= -0.01, or dG >= +0.009 and > 2 SE.
2. If any arm gained: base s2 and each such arm's s2 (ar_milestone, 110 iterations, the same deals), holding before each
   while free RAM < 2 GB or GPU memory > 80% (row 73). If none gained, no seed 2.
3. An arm cleared if its mean M - base over the 2 seeds is at least +0.02, above 0 at both, and its seed-1 X1 is at
   most -0.02 (the C81 / C83 records' R bands).
4. A metagame screen on K through loop.py launch (record and bands written first): R1 from the cleared arm's pilot if
   it needs no new architecture flags in rl.metagame, else from C49-sd 199 (the baseline), as tonight's ground truth.
Every decision goes to decisions.json and log.txt here.
Order since 333-10's call of 23:07 (#293, the ground truth first): step 4's screen runs right after step 1, from the
baseline pilot, beside C91's two seeds (queue_c90 launches them); steps 2-3 wait until those screens have ended.
"""
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import loop                                              # noqa: E402
import gpu_hold                                          # noqa: E402  row 73's hold (shared with queue_c90)

D = ROOT / "runs" / "probe" / "C84-overnight"
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
BASE = {"commit": "37d335a66593280804721244b745862c097264b2", "dir": "runs/probe/C81-chainlong", "arm": "base"}
ARMS = {
    "chaincredit": {"commit": "c0b346cee229e11d4f91c813eefa2abf57d57f25", "dir": "runs/probe/C81-chainlong", "new_arch": True},
    "chain": {"commit": "ed95a440f1173d11a69e98e5d32f9c7ac2ff79ed", "dir": "runs/probe/C81-chainlong", "new_arch": True},
    "p23": {"commit": "7c1fb59a4c204fc6a7c50d67ee86555661a0b07a", "dir": "runs/probe/C83-p23", "new_arch": False},
    "key1": {"commit": "68e60fe919837a723ee0561787e2b2b89893226f", "dir": "runs/probe/C87-key1", "new_arch": True},
    "c88": {"commit": "d822ed9be2e656886de334d32febb05017693a69", "dir": "runs/probe/C88-qtarget", "new_arch": False,
            "bands": "C88"},
}
QUEUE = D / "extra_arms.json"         # arms added after launch (C89 on Evan's yes): {name: {commit, dir, new_arch, bands}}
C91 = ("C91-round479k-s5", "C91-round479k-s6")   # round479 on K with the gate, launched beside C85 by queue_c90 (#293)
PAUSED = 5                            # ar_milestone's exit code for a run paused at an iteration boundary
REFUSED, TRIES = 4, 60                # ar_milestone's exit code for a refusal (blocked()); a resumed arm retries every 2 minutes
MOVE, CLEAR, X1_CLEAR = 0.01, 0.02, -0.02


def log(msg):
    D.mkdir(parents=True, exist_ok=True)
    with open(D / "log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    print(msg, flush=True)


def stopped() -> bool:
    return (D / "STOP").exists()


def alive(name) -> bool:
    e = json.load(open(ROOT / "runs" / "loop" / "registry.json")).get(name)
    return bool(e) and loop.alive(e["pid"], e.get("ctime"))


def hold() -> bool:
    """Row 73 (gpu_hold.hold): True once clear, False on STOP (checked on every pass); nvidia-smi unreadable holds too."""
    return gpu_hold.hold(log, stopped)


def result(folder):
    """result.json if the run trained and was scored, else None: ar_milestone also writes one on a crash (exit 1,
    "crash") or an abort (exit 3, "aborted"), without "trained"."""
    r = folder / "result.json"
    res = json.load(open(r)) if r.exists() else {}
    return res if "trained" in res and not res.get("crash") and not res.get("aborted") else None


def refusal() -> str:
    """ar_milestone's reason for exit 4: its last "refusing: ..." line in stdout.log (blocked(): ar/PAUSE absent, an
    ar/ experiment still running, powershell or nvidia-smi unreadable, or the GPU over 4000 MiB)."""
    f = D / "stdout.log"
    with open(f, "rb") as h:
        h.seek(max(0, f.stat().st_size - 8192))
        why = [l for l in h.read().decode("utf-8", "ignore").splitlines() if l.startswith("refusing: ")]
    return why[-1][len("refusing: "):] if why else "no reason in stdout.log"


def read(dirname, arm, seed):
    """(M on fresh deals, X1 three-group U - G or None) of one arm and seed, or None if it has no result."""
    res = result(ROOT / dirname / f"{arm}-s{seed}")
    if res is None:
        return None
    m = res["trained"]["forward"]["M"]
    x = ROOT / dirname / f"{arm}-s{seed}" / "x1.json"
    x1 = json.load(open(x))["readout"]["U-G"]["three"]["diff"] if x.exists() else None
    return m, x1


def replay(dirname, arm, seed):
    """The A1 replay's dG over all prompts (log #272): (dG, se, valid) or None if it can't run."""
    folder = ROOT / dirname / f"{arm}-s{seed}"
    if not (folder / "pilot.pt").exists():
        return None
    out = folder / "a1replay.json"
    subprocess.run([PY, "notes/scripts/a1_replay.py", "--pilot", str((folder / "pilot.pt").relative_to(ROOT)), "--out",
                    str(out)], cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT), "CUDA_VISIBLE_DEVICES": "-1"},
                   stdout=open(D / "stdout.log", "a"), stderr=subprocess.STDOUT)
    if not out.exists():
        return None
    r = json.load(open(out))
    if not r.get("valid"):
        return {"valid": False}
    g, n5 = r["prompts_all"], r["named5"]
    return {"valid": True, "dG": g["dG"], "se": g["se"], "call": g["call"], "n5": n5["dG"], "n5_se": n5["se"]}


def c88_band(dm, g):
    """The C88 / C89 record's seed-1 bands (runs/probe/C88-qtarget/record.md), on the named-5 dG: (call, seed 2?)."""
    if not (g and g.get("valid")):
        return "no replay", False
    n5, se = g["n5"], g["n5_se"]
    if n5 >= 0.009 and n5 > 2 * se:
        return "fixes the direction", True
    if n5 <= -0.009:
        return "same failure as p23", False
    if dm <= -0.025:                                     # research's amendment (23:29, #294): M alone is P2+P3's shared cost
        return "shared cost (M only; the verdict is the replay plus X1)", False
    if abs(n5) < 0.005 and dm >= -0.01:
        return "no harm, no gain", False
    return "between", n5 > 0


def milestone(commit, dirname, arm, seed):
    out = ROOT / dirname / f"{arm}-s{seed}"
    if (out / "result.json").exists():                   # a crash's or abort's too (a rerun would be refused: exit 2)
        if result(out) is None:
            log(f"{arm} s{seed}: result.json without a trained score (crash or abort): no result")
        return result(out) is not None
    refused = 0
    while True:                                          # a paused run (exit 5) waits, then continues from its checkpoint
        if not hold():
            return False
        ck = out / "ckpt.pt"
        resume = ["--resume-from", str(ck)] if ck.exists() else []
        log(f"{arm} s{seed}: training ({commit[:7]}){' from ' + ck.name if resume else ''}")
        r = subprocess.run([PY, "notes/scripts/ar_milestone.py", "--commit", commit, "--minutes", "150", "--seed", str(seed),
                            "--eval-seed", "1091", "--guard-seed", "1097", "--eval-games", "64", "--out-dir", str(out),
                            *resume], cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
                           stdout=open(D / "stdout.log", "a"), stderr=subprocess.STDOUT)
        log(f"{arm} s{seed}: exit {r.returncode}")
        if r.returncode == REFUSED:
            retry = bool(resume) and refused < TRIES     # a resumed arm keeps its ckpt.pt: retried; a fresh arm is dropped
            refused += 1                                 # at once, as before, so it can't hold up the C85 screen
            log(f"{arm} s{seed}: refused ({refusal()}){f'; retry {refused} of {TRIES} in 2 minutes' if retry else ''}")
            if retry:
                if stopped():
                    return False
                time.sleep(120)
                continue
        if r.returncode != PAUSED:
            if result(out) is None:
                log(f"{arm} s{seed}: no trained result{f' (refused {refused} times)' if r.returncode == REFUSED and refused > 1 else ''}")
            return result(out) is not None
        log(f"{arm} s{seed}: paused (GPU-PAUSE); waiting to resume")


def run_x1(dirname, arm, seed):
    """X1 on one pilot, as C81's and C83's chains run it (U - G on Trainer prompts, 64 games a list)."""
    out = ROOT / dirname / f"{arm}-s{seed}"
    if (out / "x1.json").exists() or not (out / "pilot.pt").exists() or not hold():
        return
    rel = lambda p: str(p.relative_to(ROOT))
    r = subprocess.run([PY, "notes/scripts/probe_prompts_pace.py", "--pilot", rel(out / "pilot.pt"), "--arms", "G", "U",
                        "--groups", "draw", "search", "disrupt", "tempo", "--games", "64", "--workers", "6",
                        "--round-turns", "20-45", "--seed", "91", "--out", rel(out / "x1.json")],
                       cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT), "RL_GPU_SHARE": "0.5",
                                      "RL_CPU_THREADS": "8"},
                       stdout=open(D / "stdout.log", "a"), stderr=subprocess.STDOUT)
    log(f"{arm} s{seed} X1: exit {r.returncode}")


SCREEN_RECORD = """# {name} record: tonight's ground truth on the fixed engine (written before launch by C84, {now}; 333-10's rule, log #271)

    {cand} · screen (1 slot, about 2 h) · the first metagame reading on build K (#235's fixed engine) · pilot {pilot_label}
    · prevention start (fresh wide decks, fresh draft head) · R1 (Nf at 3 nats, the round rule) · human-free; the lists
    only score the result

**Design.** C63's control command (runs/screens/C63-ctl-R1-c49sds3199-s5/chain.sh) on K with `--init-from {pilot}`,
seed 1, 30 iterations, 6 workers, GPU share 0.5. Then the 12 best decks (judged score) of population_it0029 against the
24 lists under C49-sd 199, 8 games a pair, the round rule (`notes/scripts/probe_meta_premise.py`, as C78).

**Readout.** The best 12's and the population median's Pokémon / Trainers / Energy at iterations 9, 19, 29 against the
lists' 13.5 / 28 / 18 (L1 distance); the best 12's decisive share against the lists (C78: 0.12-0.21 on the old build).

**Bands** (at iteration 29 and the final probe):
- **Near the lists:** best-12 distance at most 7, median Trainers at least 25, and decisive share against the lists at
  least 0.30.
- **The old deviation:** median Trainers at most 22, or best-12 Energy at least 22, or decisive share at most 0.21.
- Between: reported as such.

**Kill.** Median Pokémon at least 35 at two iterations; game errors in two iterations (#232's rule); ends at 30.
"""

SCREEN_CHAIN = """#!/bin/sh
# {name} (record.md here, log #271): R1 on build K from {pilot}, 30 iterations, then its best 12 against the lists.
cd "$(dirname "$0")/../../.." || exit 1
run=runs/screens/{name}
echo "{name} start $(date '+%F %T')"
RL_GPU_SHARE=0.5 RL_CPU_THREADS=8 .venv/Scripts/python.exe -m rl.metagame --run "$run" --iters 30 --workers 6 \\
  --stop-file "$run/STOP" --games 2000 --record 500 --ppo-transitions 64000 --lr 0.0002 --swaps 6 --field-sample 4 \\
  --draft-lr 0.0003 --draft-ent 0.01 --draft-margin 0 --shaping 0.1 --shaping-iters 100 \\
  --turnover 0.15 --seed 1 --save-every 5 --micro-batch 256 --epochs 2 \\
  --init-from {pilot} --init-wide --select --draft-h-in-floor 3.0 --draft-group-p 0.3 \\
  --practice-games 250 --turnover-wide --protect 20 --type-cap 0.5 --turnover-every 5 --candidates 1 \\
  --round-turns 20-45 --draft-base features --resume >> "$run/stdout.log" 2>&1
rc=$?
grep -qs pause "$run/STOP" && {{ echo "{name} paused $(date '+%F %T')"; exit 5; }}   # GPU-PAUSE: resumed later with --resume
echo "{name} train end $(date '+%F %T') exit $rc"
last=$(ls "$run"/population_it*.pt 2>/dev/null | sort | tail -1)
[ -n "$last" ] && PYTHONPATH=. RL_GPU_SHARE=0.5 RL_CPU_THREADS=8 .venv/Scripts/python.exe notes/scripts/probe_meta_premise.py \\
  --pilot runs/pilot/C49-sd/model_it00199.pt --games 8 --workers 6 --seed 93 --pops "$last" --out "$run/vs_lists.json" \\
  >> "$run/stdout.log" 2>&1
echo "{name} end $(date '+%F %T')"
"""


def main():
    D.mkdir(parents=True, exist_ok=True)
    ev = ROOT / "runs" / "probe" / "C83-p23" / "evening.log"     # the evening sequence ends by starting C81 chain s1
    while not (ev.exists() and "C81 chain s1 started" in ev.read_text(encoding="utf-8")) or alive("C81-chainlong")             or alive("C83-p23"):
        if stopped():
            log("STOP before the decisions")
            return
        time.sleep(60)
    for arm in ("key1", "c88"):                              # step 0: C87 (key 1 alone), C88 (Q's turn target); seed 1, X1
        k = ARMS[arm]
        if stopped():
            log(f"STOP before {arm}")
            return
        if milestone(k["commit"], k["dir"], arm, 1):
            run_x1(k["dir"], arm, 1)
    extra = json.load(open(QUEUE)) if QUEUE.exists() else {}  # read now, so an arm queued during C87/C88 joins
    for arm, k in extra.items():
        if stopped():
            log(f"STOP before {arm}")
            return
        ARMS[arm] = k
        log(f"{arm}: queued arm ({k['commit'][:7]})")
        if milestone(k["commit"], k["dir"], arm, 1):
            run_x1(k["dir"], arm, 1)
    base1 = read(BASE["dir"], "base", 1)
    prev = json.load(open(D / "decisions.json")) if (D / "decisions.json").exists() else {}
    dec = {"base_s1": base1, "seed1": {}, "moved": [], "seed2": {}, "cleared": [], "screen": None}
    for arm, a in ARMS.items():
        r = read(a["dir"], arm, 1)
        if r is None:
            dec["seed1"][arm] = None
            log(f"{arm} s1: no result")
            continue
        dm = r[0] - base1[0]
        dx = None if r[1] is None or base1[1] is None else r[1] - base1[1]
        g = replay(a["dir"], arm, 1)                         # the third test (research round 1; C84 record)
        g_moved = bool(g and g.get("valid") and g["dG"] >= 0.009 and g["dG"] > 2 * g["se"])
        moved = dm >= MOVE or (dx is not None and dx <= -MOVE) or g_moved   # gains only (333-10, 19:20)
        band = c88_band(dm, g) if a.get("bands") else None
        moved = moved or bool(band and band[1])
        dec["seed1"][arm] = {"M": r[0], "dM": round(dm, 4), "X1": r[1], "dX1": None if dx is None else round(dx, 4),
                             "replay": g, "band": band and band[0], "moved": moved}
        log(f"{arm} s1: M {r[0]:.4f} (base {base1[0]:.4f}, {dm:+.4f}), X1 {r[1]} (dX1 {dx}), replay {g}"
            f"{', band ' + band[0] if band else ''}: {'gained: seed 2' if moved else 'no seed 2'}")
        if moved:
            dec["moved"].append(arm)
    if prev.get("screen"):                                 # a relaunch after the screen started keeps it
        dec["screen"] = prev["screen"]
    json.dump(dec, open(D / "decisions.json", "w"), indent=1)
    if stopped():
        log("STOP before the screen")
        return
    if not dec["screen"] and not screen(dec):
        return
    if dec["moved"]:
        if not wait_screens(dec["screen"]["name"]):
            log("STOP before the seed 2s")
            return
        if milestone(BASE["commit"], BASE["dir"], "base", 2):
            base2 = read(BASE["dir"], "base", 2)
            for arm in dec["moved"]:
                if stopped():
                    break
                a = ARMS[arm]
                if milestone(a["commit"], a["dir"], arm, 2):
                    r2 = read(a["dir"], arm, 2)
                    dm1, dm2 = dec["seed1"][arm]["dM"], r2[0] - base2[0]
                    x1 = dec["seed1"][arm]["X1"]
                    cleared = (dm1 + dm2) / 2 >= CLEAR and dm1 > 0 and dm2 > 0 and x1 is not None and x1 <= X1_CLEAR
                    dec["seed2"][arm] = {"M": r2[0], "base_M": base2[0], "dM": round(dm2, 4), "mean_dM": round((dm1 + dm2) / 2, 4),
                                         "cleared": cleared}
                    log(f"{arm} s2: dM {dm2:+.4f}, mean {(dm1 + dm2) / 2:+.4f}, seed-1 X1 {x1}: {'CLEARED' if cleared else 'not cleared'}")
                    if cleared:
                        dec["cleared"].append(arm)
                json.dump(dec, open(D / "decisions.json", "w"), indent=1)
        if dec["cleared"]:
            log(f"cleared on 2 seeds: {dec['cleared']}; C85 ran on the baseline pilot, so their own screen is the next step")
    else:
        log("no seed-1 arm moved beyond +-0.01: no seed 2 (333-10's rule 2)")


def wait_screens(name) -> bool:
    """The seed 2s wait for the night's screens (333-10, 23:07): C85 and C91's two seeds, which queue_c90 launches beside
    it. A paused screen (STOP says pause) still counts; so does a C91 seed not yet launched while the queue runs."""
    while True:
        runs = {name: ROOT / "runs" / "screens" / name, **{n: ROOT / "runs" / "screens" / "C91-round479k" / n[-2:]
                                                           for n in C91}}
        busy = [n for n, r in runs.items() if alive(n) or (r / "STOP").exists()
                and (r / "STOP").read_text(encoding="utf-8").startswith("pause")]
        busy += [n for n in C91 if alive("C90-queue") and not (runs[n] / "launch.log").exists()]
        if not busy:
            return True
        if stopped():
            return False
        time.sleep(120)


def screen(dec) -> bool:
    """C85 on the baseline pilot (333-10, 23:07: the screens before any seed 2, so no arm has cleared yet). Through
    loop.py launch after the row-73 hold; a refusal (or a crash before the spawn) is retried every 2 minutes.
    dec["screen"] is recorded once the launch is accepted; False on STOP."""
    pilot, label = "runs/pilot/C49-sd/model_it00199.pt", "C49-sd 199 (baseline)"
    name = "C85-R1-K-base"
    run = ROOT / "runs" / "screens" / name
    if not (run / "launch.log").exists():                # launch.log: launched before a restart (a relaunch is refused)
        run.mkdir(parents=True, exist_ok=True)
        (run / "record.md").write_text(SCREEN_RECORD.format(name=name, cand="C85", now=f"{datetime.now():%Y-%m-%d %H:%M}",
                                                            pilot=pilot, pilot_label=label), encoding="utf-8")
        (run / "chain.sh").write_text(SCREEN_CHAIN.format(name=name, pilot=pilot), encoding="utf-8", newline="\n")
        while True:
            if not hold():
                log(f"STOP before the screen {name} launched")
                return False
            r = subprocess.run([PY, "notes/scripts/loop.py", "launch", name, "--candidate", "C85", "--record",
                                f"runs/screens/{name}/record.md", "--run", f"runs/screens/{name}", "--kind", "screen",
                                "--start", "prevention", "--from", "fresh", "--evan-row", "78", "--", "sh",
                                f"runs/screens/{name}/chain.sh"], cwd=ROOT, capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip()
            log(f"screen {name} from {label}: {out[-300:]}")
            if r.returncode == 0 or (run / "launch.log").exists():   # accepted: spawned (launch.log is opened just
                break                                    # before the spawn); a refusal (exit 2) or a crash before it retries
            if stopped():                                # hold() checks STOP again after the sleep
                log(f"STOP before the screen {name} launched")
                return False
            time.sleep(120)
    dec["screen"] = {"name": name, "pilot": pilot}
    json.dump(dec, open(D / "decisions.json", "w"), indent=1)
    return True


if __name__ == "__main__":
    main()
