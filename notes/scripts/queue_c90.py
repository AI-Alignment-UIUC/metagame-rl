"""C90 queue (research's record runs/probe/C90-pairedselect/record.md; 333-10's guards of 2026-10-26 21:15), with C91
beside C85 since 333-10's call of 23:07 (#293, the ground truth first). Runs as one probe through loop.py launch.

1. Waits until C84 has launched C85 (decisions.json "screen"). If C84 ends without a screen, it stops.
2. The two-patch rl/metagame.py (metagame_c90_c91.py here: C90's --select-paired and C91's --select-z, both off by
   default and checked bit-identical off) is put in before C85 launches (#293); if the live file is still the one the
   patches were made from (BASE_SHA) this does it now, keeping the old file as metagame_pre_c90.py.
3. Launches C91's seeds 5 and 6 beside C85 (runs/screens/C91-round479k/record.md: C47's rl.metagame line on K with the
   gate restored), each after the row-73 hold, and watches them with the record's kill rule.
4. C90 (C85's chain.sh renamed, --select-paired after --select) takes the first screen slot that frees, after C84's
   seed 2s if any arm earned one (they wait for C85 and C91), and is watched with its record's kill rule (errors over
   1% of an iteration's games, or 0 moves for 10 counted iterations in a row).
Every screen is pausable: on runs/GPU-PAUSE its STOP says pause, and it is relaunched with --resume when the pause lifts.
Everything goes to log.txt here; queue STOP (runs/probe/C90-pairedselect/QSTOP) ends it before step 2.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import loop                                              # noqa: E402
from aa_window import dist                               # noqa: E402  the top-12 distance from the human medians (G1)

D = ROOT / "runs" / "probe" / "C90-pairedselect"
C84 = ROOT / "runs" / "probe" / "C84-overnight"
PATCH, PRE = D / "metagame_c90_c91.py", D / "metagame_pre_c90.py"
LIVE = ROOT / "rl" / "metagame.py"
BASE_SHA = (D / "metagame_base.sha256")                  # the sha256 of the rl/metagame.py the patch was made from
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
GPU_PAUSE = ROOT / "runs" / "GPU-PAUSE"                  # Evan's pause (333-10 creates and removes it; 22:25)
C91 = ROOT / "runs" / "screens" / "C91-round479k"
C91_FROM = "runs/screens/scr-resetcap/population_it0479.pt"
C91_CHAIN = """#!/bin/sh
# {name} (runs/screens/C91-round479k/record.md, log #292-#293): C47's rl.metagame line (runs/screens/C47-chain.sh) on K
# with --select-z restored, the first --turnover-every 10 dropped (argparse kept the later 5, as #183), --reseed {seed}.
cd "$(dirname "$0")/../../../.." || exit 1
run=runs/screens/C91-round479k/s{seed}
echo "{name} start $(date '+%F %T')"
RL_GPU_SHARE=0.22 RL_CPU_THREADS=4 .venv/Scripts/python.exe -m rl.metagame --run "$run" --iters 500 --workers 4 \\
  --stop-file "$run/STOP" --games 2000 --record 500 --ppo-transitions 64000 --lr 0.0002 --swaps 6 --field-sample 4 \\
  --draft-lr 0.0003 --draft-ent 0.01 --draft-margin 0 --shaping 0.1 --shaping-iters 100 \\
  --turnover 0.15 --seed 1 --save-every 5 --micro-batch 256 --epochs 2 \\
  --fork-from {frm} --select --draft-h-in-floor 3.0 --draft-group-p 0.3 \\
  --practice-games 250 --turnover-wide --protect 20 --type-cap 0.5 --turnover-every 5 --reseed {seed} --candidates 1 \\
  --select-z 1.0 --round-turns 20-45 --resume >> "$run/stdout.log" 2>&1
rc=$?
grep -qs pause "$run/STOP" && {{ echo "{name} paused $(date '+%F %T')"; exit 5; }}   # GPU-PAUSE: resumed later with --resume
echo "{name} train end $(date '+%F %T') exit $rc"
"""


def log(msg):
    with open(D / "log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    print(msg, flush=True)


def reg() -> dict:
    return json.load(open(ROOT / "runs" / "loop" / "registry.json"))


def alive(name) -> bool:
    e = reg().get(name)
    return bool(e) and loop.alive(e["pid"], e.get("ctime"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def hold():
    """Row 73: wait while runs/GPU-PAUSE exists, free RAM < 2 GB or GPU memory > 80%."""
    while True:
        free, _ = loop.ram_gb()
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True).stdout.split(",")
        u, t = int(out[0]), int(out[1])
        if not GPU_PAUSE.exists() and free >= 2 and u <= 0.8 * t:
            return
        log(f"holding: {'GPU-PAUSE, ' if GPU_PAUSE.exists() else ''}free RAM {free:.1f} GB, GPU {u} of {t} MiB")
        time.sleep(120)


class Screen:
    def __init__(self, name, cand, record, run, start, frm, extra=()):
        self.name, self.cand, self.record, self.run, self.start, self.frm, self.extra = (
            name, cand, record, run, start, frm, list(extra))

    def launch(self, resume=False, deadline=None) -> bool:
        """Through loop.py launch after the row-73 hold; a refusal (slots, RAM, GPU) is retried every 2 minutes. Past
        `deadline` (a time.time()) a first launch gives up and returns False."""
        while True:
            hold()
            if deadline and not resume and time.time() > deadline:
                log(f"{self.name}: not started by the deadline; waits for Evan's go"); return False
            r = subprocess.run([PY, "notes/scripts/loop.py", "launch", self.name, "--candidate", self.cand, "--record",
                                self.record, "--run", self.run.relative_to(ROOT).as_posix(), "--kind", "screen",
                                "--start", self.start, "--from", self.frm, *self.extra,
                                *(["--resume"] if resume else []), "--", "sh", f"{self.run.relative_to(ROOT).as_posix()}/chain.sh"],
                               cwd=ROOT, capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip()
            log(f"launch {self.name}{' (resume)' if resume else ''}: {out[-300:]}")
            if "refused" not in out:
                time.sleep(60)
                return True
            time.sleep(120)

    def ended(self) -> bool:
        """Ended for good: not running and not paused."""
        stop = (self.run / "STOP").read_text(encoding="utf-8") if (self.run / "STOP").exists() else ""
        return (self.run / "launch.log").exists() and not alive(self.name) and not stop.startswith("pause")

    def rows(self) -> list:
        f = self.run / "log.jsonl"
        out = {}
        for l in (f.read_text(encoding="utf-8").splitlines() if f.exists() else []):
            if l.strip():
                r = json.loads(l)
                out[r["iter"]] = r                       # a resumed run's later row for an iteration wins
        return [out[k] for k in sorted(out)]

    def watch(self, kill=None):
        """To its end. On GPU-PAUSE its STOP says pause, so rl.metagame ends after the iteration it checkpointed and the
        chain exits; once the pause lifts (and row 73 clears) it is relaunched with --resume. kill(rows) -> a reason or
        None: the record's kill rule, a STOP that is not a pause."""
        while True:
            while alive(self.name):
                trained = "train end" in ((self.run / "launch.log").read_text(encoding="utf-8", errors="ignore")
                                          if (self.run / "launch.log").exists() else "")
                if GPU_PAUSE.exists() and not (self.run / "STOP").exists() and not trained:
                    (self.run / "STOP").write_text("pause (GPU-PAUSE)\n"); log(f"{self.name}: GPU-PAUSE, STOP written (pause)")
                why = kill(self.rows()) if kill and not (self.run / "STOP").exists() else None
                if why:
                    (self.run / "STOP").write_text(f"kill: {why}\n"); log(f"KILL {self.name}: {why}")
                time.sleep(60)
            stop = (self.run / "STOP").read_text(encoding="utf-8") if (self.run / "STOP").exists() else ""
            if not stop.startswith("pause"):
                log(f"{self.name} ended"); return
            log(f"{self.name} paused; waiting for the pause to lift")
            hold()
            (self.run / "STOP").unlink()
            self.launch(resume=True)


def c90_kill(rows):
    """C90's record: errors over 1% of an iteration's games, or 0 moves for 10 counted iterations in a row."""
    if any(r.get("errors", 0) > 0.01 * max(r.get("games", 1), 1) for r in rows):
        return "errors over 1%"
    moved = [(r.get("select") or {}).get("moved") for r in rows if r.get("counted") and "moved" in (r.get("select") or {})]
    if len(moved) >= 10 and not any(moved[-10:]):
        return "0 moves for 10 counted iterations (the paired bar too strict)"


def c91_kill(seeds):
    """C91's record, per seed (errors over 2%) and over both (the restore isn't the gate; no descent): a reason or None."""
    def rule(rows):
        if any(r.get("errors", 0) > 0.02 * max(r.get("games", 1), 1) for r in rows):
            return "errors over 2%"
        byit = [{r["iter"]: r for r in s.rows()} for s in seeds]
        early = [[b[i] for i in (480, 481, 482) if i in b] for b in byit]
        if all(len(e) == 3 for e in early):
            off = [not (5 <= sum((r.get("select") or {}).get("moved", 0) for r in e) / 3 <= 25)
                   or sum((r.get("select") or {}).get("held_back", 0) for r in e) / 3 < 15 for e in early]
            if all(off):
                return "the restore isn't the gate (480-482 moves outside 5-25 or held_back under 15, both seeds)"
        late = [[dist(b[i]) for i in range(490, 495) if i in b] for b in byit]
        if all(len(x) == 5 for x in late) and sum(sum(x) / 5 for x in late) / len(late) >= 10.0:
            return "no descent: two-seed mean distance over 490-494 at 10.0 or more (R-drift)"
    return rule


def ensure_patch() -> bool:
    if sha(LIVE) == sha(PATCH):
        log(f"rl/metagame.py already holds the two patches ({sha(LIVE)[:12]})"); return True
    if sha(LIVE) != BASE_SHA.read_text().strip():
        log("rl/metagame.py is neither the base nor the two-patch file: no C90, no C91 (re-check the patches)"); return False
    shutil.copyfile(LIVE, PRE)
    shutil.copyfile(PATCH, LIVE)
    log(f"rl/metagame.py patched ({sha(LIVE)[:12]}; the old file kept as {PRE.name})")
    return True


def main():
    log("waiting for C85")
    down = None                                          # when C84 was first seen down (a restart takes minutes)
    while True:                                          # 1. C85 launched (by C84)
        if (D / "QSTOP").exists():
            log("QSTOP before C90"); return
        dec = json.load(open(C84 / "decisions.json")) if (C84 / "decisions.json").exists() else {}
        scr = dec.get("screen")
        if bool(scr) and (ROOT / "runs" / "screens" / scr["name"] / "launch.log").exists():
            break
        if not alive("C84-overnight"):
            down = down or time.time()
            if time.time() - down > 900:
                log("C84 down 15 minutes without launching a screen: no C90"); return
        else:
            down = None
        time.sleep(120)
    name = scr["name"]
    c85 = Screen(name, "C85", f"runs/screens/{name}/record.md", ROOT / "runs" / "screens" / name, "prevention", "fresh",
                 ["--evan-row", "78"])
    if not ensure_patch():                               # 2.
        c85.watch(); return
    seeds = []
    for s in (5, 6):                                     # 3. C91 beside C85
        n = f"C91-round479k-s{s}"
        run = C91 / f"s{s}"
        run.mkdir(parents=True, exist_ok=True)
        (run / "chain.sh").write_text(C91_CHAIN.format(name=n, seed=s, frm=C91_FROM), encoding="utf-8", newline="\n")
        seeds.append(Screen(n, "C91", "runs/screens/C91-round479k/record.md", run, "escape", C91_FROM,
                            ["--components", "select-z,round-turns"]
                            + (["--replicate-of", "C91-round479k-s5"] if s == 6 else [])))
    kill = c91_kill(seeds)

    def seed(x):                                         # its own thread, so a refused launch (retried) blocks no watcher
        if not (x.run / "launch.log").exists():
            x.launch(resume=x.name in reg())
        x.watch(kill)
    threads = [threading.Thread(target=c85.watch)] + [threading.Thread(target=seed, args=(x,)) for x in seeds]
    for t in threads:
        t.start()
    while not any(x.ended() for x in (c85, *seeds)):     # 4. C90 in the first slot that frees
        time.sleep(120)
    dec = json.load(open(C84 / "decisions.json"))
    if dec.get("moved"):                                 # C84's seed 2s go first; they wait for C85 and C91
        log(f"seed 2s due for {dec['moved']}: C90 waits for C84")
        while alive("C84-overnight"):
            time.sleep(120)
    c90 = "C90-" + name.split("-", 1)[1] + "-paired"     # C85's chain, renamed, with --select-paired
    run = ROOT / "runs" / "screens" / c90
    run.mkdir(parents=True, exist_ok=True)
    text = (ROOT / "runs" / "screens" / name / "chain.sh").read_text(encoding="utf-8")
    assert text.count("--select ") == 1, "C85's chain should hold one --select"
    (run / "chain.sh").write_text(text.replace(name, c90).replace("--select ", "--select --select-paired "),
                                  encoding="utf-8", newline="\n")
    s90 = Screen(c90, "C90", "runs/probe/C90-pairedselect/record.md", run, "prevention", "fresh", ["--evan-row", "78"])
    if not (run / "launch.log").exists():
        s90.launch(resume=c90 in reg())
    s90.watch(c90_kill)
    for t in threads:
        t.join()
    log("queue done")


if __name__ == "__main__":
    main()
