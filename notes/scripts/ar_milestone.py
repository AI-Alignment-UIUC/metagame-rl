"""The ar/ loop's milestone check (runs/probe/ar-milestone/record.md; evaluation only, nothing here enters training).

A commit of ar/train.py, trained longer than the loop's 5 minutes and scored on deals the loop never saw:
 1. checks the commit out into a temporary worktree of ar/ (git -C ar worktree add --detach; ar's own tree is untouched);
 2. runs that train.py as fixed.py would (as __main__, --seed), with the worktree's fixed module patched first:
    TIME_BUDGET = --minutes, ROOT and DATA = the repo's and ar/data (data/ is git-ignored, so the worktree lacks it);
    its rollouts and pilot.pt stay inside the worktree, and the pilot is copied to the run folder before removal;
 3. scores it with fixed.evaluate() on fresh deals (EVAL_SEED, GUARD_SEED overridden), and in the other direction:
    the 24 lists against 4 copies each with 6 random basic Energy turned into extra copies of the list's own Trainers
    (fixed RNG; each swap a random Trainer card of the list whose name is still under 4 copies);
 4. scores the start pilot on the same deals, both directions;
 5. writes <out>/result.json and <out>/summary.md (out: runs/probe/ar-milestone-<commit>).

It refuses to run unless ar/PAUSE exists (without it the loop may be using the GPU), no ar/ experiment is still
running (python ar/fixed.py or ar/train.py) and the GPU is free; it refuses a train.py that fails fixed.py's name rule.
Out: runs/probe/ar-milestone-<commit7>, or ...-<commit7>-<minutes>min for a budget other than 30.
Exit codes: 0 done, 1 crash, 2 bad arguments, 3 aborted (ar/PAUSE removed during training), 4 refused.

Run:  PYTHONPATH=. .venv/Scripts/python notes/scripts/ar_milestone.py [--commit REV] [--minutes 30]
      (runs/probe/ar-milestone/chain.sh)
Dry:  CUDA_VISIBLE_DEVICES= PYTHONPATH=. .venv/Scripts/python notes/scripts/ar_milestone.py --dry --out-dir <scratch>
      (the decks, the worktree checkout and removal, the budget patch; no GPU, no games, no ar/PAUSE needed)
"""
import argparse
import collections
import gc
import hashlib
import importlib.util
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from rl.decks import MAX_COPIES, Pool, archived_decks   # imported before fixed, whose sys.path insert is the temp dir

ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "ar"
DATA = AR / "data"
REV_SEED = 2026_10_25          # the reverse copies' RNG (fixed.build_eval_decks uses 2026_10_24 for the forward ones)
MUTANTS, SWAP = 4, 6           # as fixed.py's


def log(msg):
    print(msg, flush=True)


def git(*args, check=True) -> str:
    r = subprocess.run(["git", "-C", str(AR), *args], capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_source(path: Path) -> str:
    """fixed.evaluate's source text, read without importing (importing ar/fixed.py would write into ar/__pycache__)."""
    import ast
    text = path.read_text(encoding="utf-8")
    return next((ast.get_source_segment(text, n) for n in ast.parse(text).body
                 if isinstance(n, ast.FunctionDef) and n.name == "evaluate"), "")


def ar_running():
    """pids of python processes running ar/fixed.py or ar/train.py (an experiment under way; ar/PAUSE stops only the
    next one), or None if the processes can't be listed. The ar/ claude session itself is not counted: under ar/PAUSE
    its fixed.py calls return "paused" at once."""
    ps = 'Get-CimInstance Win32_Process | ForEach-Object { "$($_.ProcessId)`t$($_.Name)`t$($_.CommandLine)" }'
    try:
        text = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=90,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.decode("utf-8", "ignore")
    except Exception:
        return None
    import re
    rows = [l.split("\t", 2) for l in text.splitlines()]
    return [int(r[0]) for r in rows if len(r) == 3 and r[0].isdigit() and r[1].lower().startswith("python")
            and re.search(r"ar[\\/](fixed|train)\.py", r[2])]


def blocked() -> str:
    """Why the GPU run may not start ("" if it may)."""
    if not (AR / "PAUSE").exists():
        return ("ar/PAUSE is absent, so the autoresearch loop may be using the GPU. Create ar/PAUSE, let the loop's "
                "current experiment finish, then run this again")
    busy = ar_running()
    if busy is None:
        return "the running processes can't be listed (powershell), so a running ar/ experiment can't be ruled out"
    if busy:
        return f"an ar/ experiment is still running (python pid {busy}): wait for its row in ar/results.tsv"
    try:
        used = int(subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                  capture_output=True, text=True, timeout=30).stdout.split()[0])
    except Exception:
        return "nvidia-smi can't be read"
    if used > 4000:                                    # fixed.preflight's bar
        return f"the GPU is busy ({used} MiB in use): the loop's last experiment or another job is still running"
    return ""


def build_reverse_decks(seed: int = REV_SEED) -> dict:
    """The lists and, for each, MUTANTS copies with SWAP random basic Energy turned into extra copies of the list's own
    Trainers (fixed RNG). Each swap takes a random Trainer card of the list, so by its copies, among those whose name
    is still under 4 copies; a list with fewer free slots gets fewer swaps (`swapped`). Layout as fixed's eval_decks."""
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    basic = lambda x: card[x]["superType"] == 3 and card[x]["energyType"] == 0   # noqa: E731
    rng = np.random.default_rng(seed)
    decks, pairs, swapped = [], [], []
    for name, v in archived_decks(pool):
        cards = pool.names(v)
        energy = [k for k, x in enumerate(cards) if basic(x)]
        trainers = [x for x in cards if card[x]["superType"] == 2]
        base = len(decks)
        decks.append({"name": name, "cards": cards})
        for m in range(MUTANTS):
            new = list(cards)
            copies = collections.Counter(card[x]["name"] for x in cards if not basic(x))
            n = 0
            for k in rng.choice(energy, min(SWAP, len(energy)), replace=False):
                ok = [x for x in trainers if copies[card[x]["name"]] < MAX_COPIES]
                if not ok:
                    break
                x = ok[int(rng.integers(len(ok)))]
                new[int(k)] = x
                copies[card[x]["name"]] += 1
                n += 1
            assert pool.legal(pool.vector(new)), (name, m)
            decks.append({"name": f"{name}-t{m}", "cards": new})
            pairs.append([base, len(decks) - 1])
            swapped.append(n)
    return {"decks": decks, "pairs": pairs, "swapped": swapped}


def load_fixed(wt: Path, minutes: float):
    """The worktree's fixed module, registered as `fixed` (train.py's import), patched for the longer run."""
    spec = importlib.util.spec_from_file_location("fixed", wt / "fixed.py")
    fixed = importlib.util.module_from_spec(spec)
    sys.modules["fixed"] = fixed
    spec.loader.exec_module(fixed)
    fixed.TIME_BUDGET = minutes * 60
    fixed.ROOT, fixed.DATA, fixed.START = ROOT, DATA, DATA / "start.pt"
    assert fixed.AR == wt and fixed.OUT.parent.parent == wt, (fixed.AR, fixed.OUT)   # rollouts and pilot in the worktree
    return fixed


class Tee:
    """stdout that also keeps a copy (train.py's summary block)."""

    def __init__(self, out):
        self.out, self.parts = out, []

    def write(self, s):
        self.parts.append(s)
        return self.out.write(s)

    def flush(self):
        self.out.flush()


def train(fixed, wt: Path, seed: int) -> dict:
    """train.py --seed as __main__ in this process (fixed.py runs it as a script); its summary block."""
    import os
    import re
    os.environ.pop("AR_CONTROL", None)
    fixed.OUT.unlink(missing_ok=True)
    argv, out = sys.argv, sys.stdout
    sys.argv, sys.stdout = [str(wt / "train.py"), "--seed", str(seed)], Tee(out)
    t0 = time.time()
    try:
        runpy.run_path(str(wt / "train.py"), run_name="__main__")
    finally:
        text, sys.argv, sys.stdout = "".join(sys.stdout.parts), argv, out
    tail = text.split("\n---\n")[-1] if "\n---\n" in text else ""
    return {**dict(re.findall(r"^(\w+):\s*(\S+)\s*$", tail, re.M)), "wall_s": round(time.time() - t0)}


def score(fixed, path: Path, rev_dir: Path, eval_seed: int, guard_seed: int, games: int) -> dict:
    """fixed.evaluate() on fresh deals, the lists' copies both ways; fixed's settings restored after. The reverse pass
    reads its decks through fixed.DATA and takes the next guard seed, so its S is a second guard sample."""
    keep = fixed.EVAL_SEED, fixed.GUARD_SEED, fixed.EVAL_GAMES, fixed.DATA
    try:
        fixed.EVAL_SEED, fixed.GUARD_SEED, fixed.EVAL_GAMES = eval_seed, guard_seed, games
        fwd = fixed.evaluate(path)
        log(f"  forward: {fwd}")
        fixed.DATA, fixed.GUARD_SEED = rev_dir, guard_seed + 1
        rev = fixed.evaluate(path)
        log(f"  reverse: {rev}")
    finally:
        fixed.EVAL_SEED, fixed.GUARD_SEED, fixed.EVAL_GAMES, fixed.DATA = keep
    return {"forward": fwd, "reverse": rev}


def remove_worktree(wt: Path, tmp: Path) -> bool:
    r = subprocess.run(["git", "-C", str(AR), "worktree", "remove", "--force", str(wt)], capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode:                                   # e.g. a file still locked: the folder is gone now, drop the entry
        git("worktree", "prune", check=False)
    return not tmp.exists() and str(wt.as_posix()).lower() not in git("worktree", "list").lower()


# ---- the readout (the bands of runs/probe/ar-milestone/record.md) ---------------------------------------------------

def se_binom(ev: dict, pairs: int, games: int) -> float:
    """M's deal noise, treating its decisive games as independent coin flips (pairs weigh about equally)."""
    return float(np.sqrt(ev["M"] * (1 - ev["M"]) / max(pairs * games - ev["draws"], 1)))


def readout(res: dict, st: dict) -> dict:
    n, g = res["pairs"], res["eval_games"]
    out = {}
    for d in ("forward", "reverse"):
        t, s = res["trained"][d], res["start"][d]
        se = max(float(np.hypot(se_binom(t, n, g), se_binom(s, n, g))), 1e-9)
        out[d] = {"D": t["M"] - s["M"], "se": se, "z": (t["M"] - s["M"]) / se}
    z = out["forward"]["z"]
    out["primary"] = "gain" if z >= 2 else "loss" if z <= -2 else "flat"

    def balance(p):
        f, r = res[p]["forward"]["M"] >= 0.5, res[p]["reverse"]["M"] >= 0.5
        return {(False, True): "energy-side", (True, True): "lists-optimal", (True, False): "trainer-side",
                (False, False): "both-copies-win"}[(f, r)]
    out["balance"] = {p: balance(p) for p in ("start", "trained")}
    S = (res["trained"]["forward"]["S"] + res["trained"]["reverse"]["S"]) / 2
    out["S"], out["guard_bar"] = S, st.get("guard_bar")
    out["guard"] = "fail" if out["guard_bar"] is not None and S < out["guard_bar"] else "pass"
    evs = [res[p][d] for p in ("start", "trained") for d in ("forward", "reverse")]
    out["errors"] = sum(e["errors"] for e in evs)
    out["valid"] = all(e["errors"] <= 0.01 * e["games"] for e in evs)
    loop = res["loop"]
    if loop.get("M") is not None and loop.get("start_M") is not None:
        out["D_loop"] = loop["M"] - loop["start_M"]
        if out["D_loop"] >= st.get("delta", 0.01):
            out["transfer"] = "holds" if out["primary"] == "gain" else "does not hold"
    return out


def summary(res: dict, r: dict) -> str:
    t, s = res["trained"], res["start"]
    row = lambda name, x: (f"| {name} | {x['forward']['M']:.4f} | {x['reverse']['M']:.4f} | "   # noqa: E731
                           f"{x['forward']['S']:.3f} / {x['reverse']['S']:.3f} | {x['forward']['draws']} / "
                           f"{x['reverse']['draws']} |")
    lines = [
        f"# ar milestone {res['commit'][:7]}: {res['subject'][:90]}",
        "",
        f"{res['ended']} · train.py --seed {res['seed']}, {res['minutes']:g} min budget (the loop's is 5) · "
        f"{res.get('train', {}).get('games', '?')} practice games, {res.get('train', {}).get('iterations', '?')} "
        f"iterations · fresh deals: eval seed {res['eval_seed']}, guard seeds {res['guard_seed']}/"
        f"{res['guard_seed'] + 1}, {res['eval_games']} games a pair, {res['pairs']} pairs a direction",
        "",
        "| pilot | M forward (lists vs Trainers->Energy) | M reverse (lists vs Energy->Trainers) | S fwd / rev | "
        "draws fwd / rev |",
        "|---|---|---|---|---|",
        row("start (C49-sd 199)", s),
        row(f"trained {res['commit'][:7]}", t),
        "",
        f"- Primary, D forward = {r['forward']['D']:+.4f} (SE {r['forward']['se']:.4f}, z {r['forward']['z']:+.1f}): "
        f"**{r['primary']}**. D reverse = {r['reverse']['D']:+.4f} (SE {r['reverse']['se']:.4f}).",
        f"- Balance: start {r['balance']['start']}, trained {r['balance']['trained']} (lists-optimal = both M at "
        f"least 0.5, the goal on this axis).",
        f"- Guard: S {r['S']:.3f} vs bar {r['guard_bar'] or 0:.3f}: {r['guard']}. Game errors {r['errors']}"
        f"{'' if r['valid'] else ' (over 1%: INVALID)'}.",
    ]
    if "D_loop" in r:
        lines.append(f"- The loop's own reading (5 min, its fixed deals): D {r['D_loop']:+.4f}"
                     + (f"; transfer to {res['minutes']:g} min on fresh deals: **{r['transfer']}**"
                        if "transfer" in r else "") + ".")
    lines.append(f"- SE: binomial over decisive games, the two pilots' games taken as independent (record.md).")
    return "\n".join(lines) + "\n"


# ---- main -----------------------------------------------------------------------------------------------------------

def run_commit(a, wt: Path, out: Path, rev_dir: Path, pilot, res: dict, st: dict) -> int:
    """Steps 2-4 inside the checked-out worktree; the exit code (0 done, 3 aborted)."""
    from rl import limits
    fixed = load_fixed(wt, a.minutes)
    res["fixed_py_same_as_ar"] = sha(wt / "fixed.py") == sha(AR / "fixed.py")
    res["evaluate_same_as_ar"] = evaluate_source(wt / "fixed.py") == evaluate_source(AR / "fixed.py") != ""
    res["limits"] = {"gpu_share": limits.GPU_SHARE, "cpu_threads": limits.CPU_THREADS, "max_workers": limits.MAX_WORKERS}
    log(f"fixed: TIME_BUDGET {fixed.TIME_BUDGET:g} s, OUT {fixed.OUT}, START {fixed.START}, DATA {fixed.DATA}; "
        f"fixed.py same as ar/'s: {res['fixed_py_same_as_ar']} (evaluate(): {res['evaluate_same_as_ar']}); "
        f"limits {res['limits']}")
    # the loop's own rule (fixed.preflight): train.py reads no human lists, card kinds or names. Commits the loop ran
    # passed it; this covers any other commit before it trains here.
    text = (wt / "train.py").read_text(encoding="utf-8")
    hits = [w for w in tuple(getattr(fixed, "FORBIDDEN", ())) + tuple(c["fullName"] for c in Pool().cards) if w in text]
    log(f"train.py forbidden names: {hits[:5] or 'none'}")
    if hits:
        raise RuntimeError(f"train.py names something it may not read: {hits[:5]}")
    if a.dry:
        spec = importlib.util.spec_from_file_location("ar_train", wt / "train.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)                       # imports only; main() is not run
        w = getattr(mod, "WORKERS", None)
        log(f"train.py imported: sees fixed.TIME_BUDGET {mod.fixed.TIME_BUDGET:g} s (the patched module: "
            f"{mod.fixed is fixed}); WORKERS {w}" + (f" -> capped to {limits.MAX_WORKERS} by limits"
                                                      if w and w > limits.MAX_WORKERS else ""))
        return 0
    if pilot is None:
        log(f"training {a.minutes:g} min ...")
        res["train"] = train(fixed, wt, a.seed)
        log(f"train: {res['train']}")
        if not fixed.OUT.exists():
            raise RuntimeError("train.py saved no pilot")
        pilot = out / "pilot.pt"
        shutil.copyfile(fixed.OUT, pilot)
    res["pilot"] = pilot.relative_to(ROOT).as_posix()
    gc.collect()
    import torch
    torch.cuda.empty_cache()
    if not (AR / "PAUSE").exists():
        res["aborted"] = "ar/PAUSE was removed during training: not evaluated (rerun with --pilot)"
        log(res["aborted"])
        return 3
    log("scoring the trained pilot ...")
    res["trained"] = score(fixed, pilot, rev_dir, a.eval_seed, a.guard_seed, a.eval_games)
    log("scoring the start pilot ...")
    res["start"] = score(fixed, fixed.START, rev_dir, a.eval_seed, a.guard_seed, a.eval_games)
    res["readout"] = readout(res, st)
    return 0


def main():
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--commit", help="a commit of the ar/ repo (default: ar/state.json's kept)")
    ap.add_argument("--minutes", type=float, default=30.0, help="train.py's budget, minutes on its own clock "
                    "(the loop's is 5)")
    ap.add_argument("--seed", type=int, default=1, help="train.py --seed (the loop's first seed)")
    ap.add_argument("--eval-seed", type=int, default=1091, help="fresh deals for M (the loop's seed is 91)")
    ap.add_argument("--guard-seed", type=int, default=1097, help="fresh deals for the guard S (the loop's is 97); "
                    "the reverse pass takes the next seed")
    ap.add_argument("--eval-games", type=int, default=64, help="games a pair (the loop's are 32; 64 halves the "
                    "variance of the trained-minus-start difference)")
    ap.add_argument("--pilot", help="skip training and score this saved pilot (inside the repo), e.g. the pilot.pt "
                    "of a run that died during evaluation")
    ap.add_argument("--out-dir", help="default runs/probe/ar-milestone-<commit>")
    ap.add_argument("--dry", action="store_true", help="no GPU, no games: build the reverse decks, check the "
                    "worktree out, patch the budget, import train.py, remove the worktree")
    a = ap.parse_args()
    if a.minutes <= 0 or a.eval_games < 2 or a.eval_games % 2:
        ap.error("--minutes must be positive and --eval-games even (seats alternate)")
    st = json.loads((AR / "state.json").read_text(encoding="utf-8"))
    rev = a.commit or st["kept"]
    commit = git("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}", check=False)
    if not commit:
        ap.error(f"--commit {rev}: not a commit of the ar/ repo")
    tag = "" if a.minutes == 30 else f"-{a.minutes:g}min"         # so `chain.sh <commit> 5` gets its own folder
    out = Path(a.out_dir).resolve() if a.out_dir else ROOT / "runs" / "probe" / f"ar-milestone-{commit[:7]}{tag}"
    pilot = Path(a.pilot).resolve() if a.pilot else None
    if not a.dry:
        for p, what in ((out, "--out-dir"), (pilot, "--pilot")):
            if p is not None and not p.is_relative_to(ROOT):
                ap.error(f"{what} must be inside {ROOT} (fixed.evaluate loads pilots by repo-relative path)")
        if pilot is not None and not pilot.exists():
            ap.error(f"--pilot {pilot}: no such file")
        if (out / "result.json").exists():
            ap.error(f"{out / 'result.json'} exists: pass another --out-dir")
        why = blocked()
        if why:
            log(f"refusing: {why}.")
            sys.exit(4)
    log(f"ar milestone: commit {commit[:7]} ({git('log', '-1', '--format=%s', commit)[:80]}), {a.minutes:g} min, "
        f"seed {a.seed}, out {out}{' (dry)' if a.dry else ''}")

    out.mkdir(parents=True, exist_ok=True)
    rv = build_reverse_decks()
    fwd = json.loads((DATA / "eval_decks.json").read_text(encoding="utf-8"))
    rv["guard"] = fwd["guard"]
    rev_dir = out / "reverse"
    rev_dir.mkdir(exist_ok=True)
    (rev_dir / "eval_decks.json").write_text(json.dumps(rv, indent=1), encoding="utf-8")
    log(f"reverse copies: {len(rv['pairs'])} pairs (forward {len(fwd['pairs'])}); basic Energy turned into Trainers "
        f"per copy: {dict(sorted(collections.Counter(rv['swapped']).items()))}")

    res = {"commit": commit, "subject": git("log", "-1", "--format=%s", commit), "minutes": a.minutes,
           "seed": a.seed, "eval_seed": a.eval_seed, "guard_seed": a.guard_seed, "eval_games": a.eval_games,
           "pairs": len(rv["pairs"]), "rev_seed": REV_SEED, "rev_swapped": rv["swapped"],
           "started": f"{datetime.now():%Y-%m-%d %H:%M}", "loop": {"start_M": st.get("start", {}).get("M")}}
    rows = [l.split("\t") for l in (AR / "results.tsv").read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
    # the commit's own rows (crashes and the quarantined movability control left out); a kept commit without rows (a
    # re-setup baseline) falls back to state.json's best. Rows first: a "simpler" keep leaves best at an older commit's M.
    mine = [float(r[1]) for r in rows if len(r) >= 7 and commit.startswith(r[0])
            and r[3] in ("keep", "confirm", "discard", "setup") and float(r[1]) > 0 and "movability control" not in r[6]]
    res["loop"]["rows_M"] = mine
    res["loop"]["M"] = (float(np.mean(mine)) if mine else
                        st["best"] if commit == st.get("kept") and "best" in st else None)

    status_before = git("status", "--porcelain")
    tmp = Path(tempfile.mkdtemp(prefix=f"ar-milestone-{commit[:7]}-")).resolve()
    wt = tmp / "ar"
    git("worktree", "add", "--detach", str(wt), commit)
    log(f"worktree: {wt}")
    code = 1
    try:
        code = run_commit(a, wt, out, rev_dir, pilot, res, st)
    except BaseException as e:
        res["crash"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        sys.modules.pop("fixed", None)
        gone = remove_worktree(wt, tmp)
        log(f"worktree removed: {gone}; ar/ git status as before: {git('status', '--porcelain') == status_before}; "
            f"worktrees now: {git('worktree', 'list').splitlines()}")
        if not a.dry:
            res["ended"] = f"{datetime.now():%Y-%m-%d %H:%M}"
            (out / "result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
            if "readout" in res:
                (out / "summary.md").write_text(summary(res, res["readout"]), encoding="utf-8")
                log(summary(res, res["readout"]))
            log(f"wrote {out / 'result.json'}")
    sys.exit(code)


if __name__ == "__main__":
    main()
