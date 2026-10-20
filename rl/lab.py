"""The lab (notes/plan-lab.md): the metagame loop (rl/metagame.py) as one main line that keeps training, and short
branches from it, each decided by a sequential test against the main line at the same iteration.

The main line is the method itself: one pilot that plays only the decks the draft head drafts, and a draft head that
reads every deck through that pilot. A branch changes one part of it (the pilot's architecture or training, or the
drafting) and must use only what any card game's environment gives (cards as features and rules text, the legal
options, the result): each card states this under "generality".

Every cycle, with m the main line's finished iterations (a multiple of `seg`):
  1. running branches behind the main line run up to m, are evaluated against the main line at m, and decided
  2. up to `branches` queued cards start at m: each forks the main line's state at m (main/seg_XXXX.pt)
  3. the main line runs to m + seg
so the main line gets about 1 / (1 + branches) of the lab's time; the lab gets RL_GPU_SHARE of the card (one job at a
time, each paced to that share, rl/limits.py).

Cards (runs/lab/cards/*.json, taken in name order), written before their run, never edited after it starts:
  {"id", "kind": "pilot" | "meta" | "aa", "hypothesis", "generality", "args": {"--flag": value}, "segments": 1}
  pilot  the branch's pilot against the main line's on fixed deck pairs drawn from both populations (each pair:
         both pilots on both decks, both seat orders, the same deals), a sequential probability ratio test of
         H0 Elo <= elo0 against H1 Elo >= elo1. At an earlier segment of a longer card, only "clearly worse"
         (H0 Elo <= -elo1 accepted against H1 Elo >= 0) stops it. Gate: the same pilots on the 24 archived lists
         (evaluation only) must not be clearly worse. Passed and gated: adopted, the main line goes on from the branch.
         "test": "noninferior" (a change that saves time) tests H0 Elo <= -elo1 against H1 Elo >= 0 instead.
  meta   the answer key of both populations (rl/evaluate_agents.py: their best decks against the archived lists
         under the main line's pilot, the field staples they play, archetype overlap); the card's "rule"
         ({"metric": "archived_mean", "min_gain": x}) decides; the pilot test is a gate (not clearly worse)
  aa     no change (or only --reseed): every test at full length and no decision; the noise a branch sees, from
         which elo1 and the meta rules' thresholds are set
A pilot card with "decide": "s1" is decided instead on Stage 1's pilot competence (run_s1: the Trainer-value panel and
the win-this-turn puzzles, built from the archived lists, evaluation only), with the Elo test as a gate.
A card with "warm" forks from a pilot of its architecture first trained to play as the main line's (rl/warmstart.py),
so a change that cannot be grown as the identity does not start behind.
A card that ends undecided is closed as inconclusive, not extended. When a card is adopted, cards still running from an
earlier fork are closed as rebased and queued again (id + "-b") to start from the new main line. A card with
"hold": true that passes is marked passed-held and not adopted, so the cards running beside it keep their control.

Files under runs/lab: lab.json (settings, read every cycle), events.jsonl (one line per step), STOP (ends the lab, and
any running segment after its current iteration), main/ (the main line), branches/<card id>/.

Run (detached): RL_GPU_SHARE=0.333 RL_CPU_THREADS=10 .venv/Scripts/python -m rl.lab run
         or: .venv/Scripts/python -m rl.lab start   (the same, outside the shell's job, so it outlives the session)
         status: .venv/Scripts/python -m rl.lab status
"""
import argparse
import ctypes
import datetime
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / os.environ.get("RL_LAB_DIR", "runs/lab")         # another directory for smoke tests
MAIN, CARDS, BRANCHES = LAB / "main", LAB / "cards", LAB / "branches"
STOP, EVENTS, SETTINGS = LAB / "STOP", LAB / "events.jsonl", LAB / "lab.json"
PY = sys.executable
SOURCE = "runs/meta-99/checkpoint.pt"           # where the main line starts: meta-99 after its 150 iterations (#69)
DEFAULTS = {
    "seg": 10, "branches": 2, "elo0": 0.0, "elo1": 15.0, "alpha": 0.05, "beta": 0.05,
    "pairs_batch": 100, "pairs_cap": 1500, "early_cap": 500, "workers": 8, "milestone_every": 40, "meta_games": 16,
    "milestone_common": "runs/pilot-v2/model_it00349.pt", "min_free_ram_gb": 6.0, "min_free_gpu_gb": 5.0,
    "s1_games": 64, "s1_min_gain": 0.03,                 # Stage 1's pilot-competence measure (notes/plan-rediscovery.md)
    "shape_max_loss": 16.0,                             # a meta card's best decks may not move this much further from
                                                        # the human medians than the main line's (log #101, A/A 2 RMS)
    # meta-99's settings (runs/meta-99/config.json); micro-batch 512 is the same gradient in smaller chunks
    "main_args": {"--games": 2000, "--record": 500, "--ppo-transitions": 64000, "--lr": 1e-4, "--swaps": 3,
                  "--field-sample": 4, "--draft-lr": 1e-3, "--draft-ent": 0.01, "--draft-margin": 0.5,
                  "--shaping": 0.1, "--shaping-iters": 100, "--turnover-every": 10, "--turnover": 0.15,
                  "--seed": 1, "--save-every": 0, "--micro-batch": 512},
    "adopted": [],
}


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def event(what: str, **kw):
    line = json.dumps({"t": now(), "event": what, **kw})
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def settings() -> dict:
    s = {**DEFAULTS, **(json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {})}
    if not SETTINGS.exists():
        SETTINGS.write_text(json.dumps(s, indent=1))
    return s


def save_settings(s: dict):
    tmp = SETTINGS.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1))
    os.replace(tmp, SETTINGS)


def cli(args: dict) -> list:
    out = []
    for k, v in args.items():
        if v is True:
            out.append(k)
        elif v is not False and v is not None:
            out += [k, json.dumps(v) if isinstance(v, (dict, list)) else str(v)]
    return out


def done(run: Path) -> int:
    """Finished iterations of a metagame run (0 if it has no checkpoint)."""
    import torch
    ck = run / "checkpoint.pt"
    return torch.load(ck, map_location="cpu", weights_only=False)["iter"] + 1 if ck.exists() else 0


def seg_path(m: int) -> Path:
    return MAIN / f"seg_{m:04d}.pt"


def load_card(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def save_card(c: dict):
    p = CARDS / f"{c['id']}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(c, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def cards(status=None) -> list:
    out = [load_card(p) for p in sorted(CARDS.glob("*.json"))]
    return [c for c in out if status is None or c.get("status", "queued") in status]


def requeue(c: dict, suffix: str, **why):
    """A fresh copy of card c, queued right after it in name order (a retest, or a restart from a new main line)."""
    re = {k: c[k] for k in ("kind", "hypothesis", "generality", "args", "segments", "rule", "test") if k in c}
    save_card({**re, "id": c["id"] + suffix, "status": "queued", **why})


# ---------------------------------------------------------------- resources

class _MemStatus(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_ram_gb() -> float:
    if os.name != "nt":
        return float("inf")
    m = _MemStatus()
    m.dwLength = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 2 ** 30


def free_gpu_gb() -> float:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        total, used = (float(x) for x in out.split("\n")[0].split(","))
        return (total - used) / 1024
    except (OSError, ValueError, subprocess.SubprocessError):
        return float("inf")


def keep_awake():
    """No idle sleep while the lab runs (ES_CONTINUOUS | ES_SYSTEM_REQUIRED); a deliberate sleep still happens."""
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)


def wait_resources(s: dict) -> bool:
    """Waits until there is room for the next job; False if STOP appeared meanwhile."""
    told = False
    while True:
        if STOP.exists():
            return False
        ram, gpu = free_ram_gb(), free_gpu_gb()
        if ram >= s["min_free_ram_gb"] and gpu >= s["min_free_gpu_gb"]:
            if told:
                event("resumed", free_ram_gb=round(ram, 1), free_gpu_gb=round(gpu, 1))
            return True
        if not told:
            event("waiting", free_ram_gb=round(ram, 1), free_gpu_gb=round(gpu, 1))
            told = True
        time.sleep(60)


# ---------------------------------------------------------------- jobs

def run_metagame(run: Path, args: list, until: int, s: dict) -> bool:
    run.mkdir(parents=True, exist_ok=True)
    cmd = [PY, "-m", "rl.metagame", "--run", str(run.relative_to(ROOT).as_posix()), "--resume", "--iters", str(until),
           "--workers", str(s["workers"]), "--stop-file", str(STOP)] + args
    t0 = time.time()
    with open(run / "stdout.log", "a", encoding="utf-8") as f:
        f.write(f"\n# {now()} {' '.join(cmd)}\n")
        f.flush()
        rc = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    event("segment", run=run.name, until=until, ok=rc == 0, minutes=round((time.time() - t0) / 60, 1))
    return rc == 0


def run_warm(c: dict, base: int, s: dict) -> Path:
    """A card with "warm" ({"pilot-opts": {...}, "games", "epochs"}; log #98): its pilot architecture is first trained
    to play as the main line's pilot at base (rl/warmstart.py), and the branch forks from that; None if it failed."""
    w, out = c["warm"], BRANCHES / c["id"] / "warm.pt"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        cmd = [PY, "-m", "rl.warmstart", "--teacher", str(seg_path(base).relative_to(ROOT).as_posix()),
               "--pilot-opts", json.dumps(w.get("pilot-opts", {})), "--out", str(out.relative_to(ROOT).as_posix()),
               "--games", str(w.get("games", 2000)), "--epochs", str(w.get("epochs", 3)), "--workers", str(s["workers"])]
        with open(BRANCHES / c["id"] / "stdout.log", "a", encoding="utf-8") as f:
            f.write(f"\n# {now()} {' '.join(cmd)}\n")
            f.flush()
            rc = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
        if rc != 0 or not out.exists():
            return None
        import torch
        event("warm", card=c["id"], at=base, **torch.load(out, map_location="cpu", weights_only=False)["warm"]["after"])
    return out


def run_h2h(a: Path, b: Path, panel: str, seed: int, s: dict, elo0: float, elo1: float, cap: int,
            sequential: bool) -> dict:
    out = LAB / "tmp" / f"h2h_{os.getpid()}_{int(time.time())}.json"
    out.parent.mkdir(exist_ok=True)
    cmd = [PY, "-m", "rl.lab", "h2h", "--a", str(a), "--b", str(b), "--panel", panel, "--seed", str(seed),
           "--elo0", str(elo0), "--elo1", str(elo1), "--cap", str(cap), "--batch", str(s["pairs_batch"]),
           "--alpha", str(s["alpha"]), "--beta", str(s["beta"]), "--workers", str(s["workers"]), "--out", str(out)]
    if not sequential:
        cmd.append("--fixed")
    with open(LAB / "h2h.log", "a", encoding="utf-8") as f:
        rc = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    if rc != 0 or not out.exists():
        return {"error": f"h2h exited {rc}"}
    r = json.loads(out.read_text())
    out.unlink()
    return r


def run_meta_eval(ckpt: Path, common: Path, out: Path, s: dict, simplebot: bool = False) -> dict:
    if out.exists():                            # the same checkpoints already evaluated (the main line at m, a restart)
        return meta_metrics(json.loads(out.read_text()))
    cmd = [PY, "-m", "rl.evaluate_agents", "--checkpoint", str(ckpt.relative_to(ROOT).as_posix()),
           "--common", str(common.relative_to(ROOT).as_posix() if common.is_absolute() else common),
           "--workers", str(s["workers"]), "--games", str(s["meta_games"]), "--out", str(out.relative_to(ROOT).as_posix())]
    if not simplebot:
        cmd += ["--skip", "simplebot", "meta", "sb_archived"]
    with open(LAB / "eval.log", "a", encoding="utf-8") as f:
        rc = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    if rc != 0 or not out.exists():
        return {"error": f"evaluate_agents exited {rc}"}
    return meta_metrics(json.loads(out.read_text()))


HUMAN_SHAPE = np.array([13.5, 28.0, 18.0])            # the 24 archived lists' median Pokémon / Trainers / Energy (#94)


def meta_metrics(ev: dict) -> dict:
    """The answer-key numbers of an rl/evaluate_agents.py result; shape_dist is the L1 distance of the best decks' mean
    Pokémon / Trainers / Energy from the human lists' medians, in cards (log #101)."""
    ag = ev.get("agents", [])
    near = {a["nearest"] for a in ag if a["overlap"] >= 0.5}
    shape = (np.array([[a["pokemon"], a["trainer"], a["basic_energy"] + a["special_energy"]] for a in ag]).mean(0)
             if ag else None)
    return {"archived_mean": ev.get("archived", {}).get("mean"),
            "archived_best": max(ev.get("archived", {}).get("vs_field", [None]) or [None]),
            "staples": round(float(np.mean([len(a["staples"]) for a in ag])), 3) if ag else None,
            "overlap_best": max((a["overlap"] for a in ag), default=None),
            "archetypes_at_half": sorted(near),
            "simplebot": (round(float(np.mean([x["win"] for x in ev["simplebot"]])), 4) if ev.get("simplebot") else None),
            "sb_archived_mean": ev.get("sb_archived", {}).get("mean"),
            "shape": None if shape is None else [round(float(x), 1) for x in shape],
            "shape_dist": None if shape is None else round(float(np.abs(shape - HUMAN_SHAPE).sum()), 2)}


PUZZLES = ROOT / "notes/data/puzzles/lethal.json"


def puzzle_rates(rows: list) -> dict:
    """Solve rates on the win-this-turn puzzles (env/tools/puzzles.js, log #92) by what the winning first move must be."""
    verb = lambda k: k.split("|")[0]
    P = json.loads(PUZZLES.read_text())["puzzles"]
    tf = [i for i, p in enumerate(P) if not any(verb(k) == "attack" for k in p["wins"]) and any(verb(k) == "trainer" for k in p["wins"])]
    pp = [i for i in tf if {k.split("|")[1] for k in P[i]["wins"] if verb(k) == "trainer"} == {"PlusPower BS"}]
    at = [i for i, p in enumerate(P) if any(verb(k) == "attack" for k in p["wins"])]
    rate = lambda ix: round(sum(rows[i]["solved"] for i in ix) / max(len(ix), 1), 4)
    return {"attack_won": rate(at), "trainer_first": rate(tf), "pluspower": rate(pp)}


def run_s1(ckpt: Path, tag: str, s: dict) -> dict:
    """Stage 1's pilot competence (notes/plan-rediscovery.md; evaluation only): the Trainer-value panel on the archived
    lists (each group of Trainers against a copy with that group replaced by basic Energy, notes/scripts/trainer_value.py)
    and the win-this-turn puzzles, greedy; "s1" is the mean of search, disrupt, tempo, Trainer-first and PlusPower."""
    out = LAB / "tmp" / f"s1_{tag}.json"
    if out.exists():
        return json.loads(out.read_text())
    rel = lambda p: str(Path(p).resolve().relative_to(ROOT).as_posix())
    tv, onnx, pz = LAB / "tmp" / f"tv_{tag}.json", LAB / "tmp" / f"s1_{tag}.onnx", LAB / "tmp" / f"pz_{tag}.json"
    env = {**os.environ, "PYTHONPATH": "."}
    with open(LAB / "eval.log", "a", encoding="utf-8") as f:
        rc1 = subprocess.run([PY, "notes/scripts/trainer_value.py", "--decks", "archived", "--players", rel(ckpt),
                              "--groups", "search", "disrupt", "tempo", "--games", str(s["s1_games"]),
                              "--workers", str(s["workers"]), "--out", rel(tv)], cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
        rc2 = subprocess.run([PY, "-c", "import sys; from rl.gpu_matrix import load_policy; from rl.train import export_policy; "
                              "m, e = load_policy(sys.argv[1], 'cpu'); m.max_tok, m.max_cand, m.action_size = 256, 128, 128; "
                              "export_policy(m, sys.argv[2], e)", rel(ckpt), str(onnx)], cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
        rc3 = subprocess.run(["node", "env/tools/puzzles.js", "score", "--agent", f"onnxtok:{onnx}", "--json", str(pz)],
                             cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode if rc2 == 0 else 1
    if rc1 or rc2 or rc3 or not tv.exists() or not pz.exists():
        return {"error": f"s1 exited {rc1}/{rc2}/{rc3}"}
    groups = next(iter(json.loads((ROOT / rel(tv)).read_text())["players"].values()))["by_group"]
    r = {**{g: groups[g]["score"] for g in ("search", "disrupt", "tempo")}, **puzzle_rates(json.loads(pz.read_text())["rows"])}
    r["s1"] = round(float(np.mean([r["search"], r["disrupt"], r["tempo"], r["trainer_first"], r["pluspower"]])), 4)
    out.write_text(json.dumps(r))
    onnx.unlink(missing_ok=True)
    return r


# ---------------------------------------------------------------- statistics

def expected_score(elo: float) -> float:
    return 1.0 / (1.0 + 10 ** (-elo / 400.0))


def elo_of(score: float) -> float:
    score = min(max(score, 1e-4), 1 - 1e-4)
    return -400.0 * math.log10(1.0 / score - 1.0)


def llr(scores, elo0: float, elo1: float) -> float:
    """Log-likelihood ratio of H1 (Elo = elo1) over H0 (Elo = elo0) for paired scores in [0, 1], normal approximation
    with the sample variance (the generalised SPRT of chess engine testing)."""
    x = np.asarray(scores, dtype=np.float64)
    n = len(x)
    if n < 2:
        return 0.0
    var = max(float(x.var(ddof=1)), 1e-4)
    s0, s1 = expected_score(elo0), expected_score(elo1)
    return float((s1 - s0) * (2.0 * x.sum() - n * (s0 + s1)) / (2.0 * var))


def bounds(alpha: float, beta: float) -> tuple:
    return math.log(beta / (1 - alpha)), math.log((1 - beta) / alpha)


def summary(scores) -> dict:
    x = np.asarray(scores, dtype=np.float64)
    m, se = float(x.mean()), float(x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else 0.5
    return {"pairs": len(x), "score": round(m, 4), "elo": round(elo_of(m), 1),
            "elo_lo": round(elo_of(m - 1.96 * se), 1), "elo_hi": round(elo_of(m + 1.96 * se), 1)}


def pair_scores(W: np.ndarray, G: np.ndarray, chunk: list, n: int) -> list:
    """A's score per unordered deck pair (x, y) over its 4 games: A on x against B on y (W[x, n + y] of 2), and A on y
    against B on x (the games of cell (n + x, y) that B lost)."""
    return [float(W[x, n + y] + G[n + x, y] - W[n + x, y]) / 4.0 for x, y in chunk]


def h2h_main(args):
    """Pilot A (a branch) against pilot B (the main line) on fixed deck pairs; writes the result to --out."""
    import torch
    from rl import limits
    from rl.decks import Pool, archived_decks
    from rl.gpu_matrix import GpuMatrix
    from rl.remote import RemotePool
    from rl.train import token_net
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(args.workers)
    limits.apply(device, workers)
    sa = torch.load(ROOT / args.a, map_location="cpu", weights_only=False)
    sb = torch.load(ROOT / args.b, map_location="cpu", weights_only=False)
    if args.panel == "archived":
        pool = Pool()
        decks = [{"name": nm, "cards": pool.names(v)} for nm, v in archived_decks(pool)]
    else:                                       # both populations, so neither pilot plays only its own decks
        decks = ([{"name": f"a{x['id']}", "cards": x["deck"]} for x in sa["population"]]
                 + [{"name": f"b{x['id']}", "cards": x["deck"]} for x in sb["population"]])
    n = len(decks)
    rng = np.random.default_rng(args.seed)
    allp = [(x, y) for x in range(n) for y in range(x + 1, n)]
    pairs = [allp[k] for k in rng.permutation(len(allp))[:args.cap]]
    rp = RemotePool(workers)
    try:
        info = rp.ask_all([{"cmd": "info"}] * workers)[0]
        nets = []
        for st in (sa, sb):
            net = token_net(st["config"], info).to(device)
            net.load_state_dict(st["net"] if "net" in st else st["model"])
            nets.append(net.eval())
        models = {0: nets[0], 1: nets[1]}
        gm = GpuMatrix.attach(nets[0], rp, workers, device=device)
        lo, hi = bounds(args.alpha, args.beta)
        scores, errors, verdict, t0 = [], 0, None, time.time()
        for k in range(0, len(pairs), args.batch):
            chunk = pairs[k:k + args.batch]
            ps = [(x, n + y) for x, y in chunk] + [(n + x, y) for x, y in chunk]
            keys = list(range(k, k + len(chunk))) * 2              # both halves of a deck pair get the same deals
            W, G, _ = gm.play(decks + decks, 2, args.seed, pairs=ps, slots=[0] * n + [1] * n, models=models,
                              pair_keys=keys)
            errors += gm.last["errors"]
            scores += pair_scores(W, G, chunk, n)
            r = llr(scores, args.elo0, args.elo1)
            if not args.fixed and (r <= lo or r >= hi):
                verdict = "H0" if r <= lo else "H1"
                break
        r = llr(scores, args.elo0, args.elo1)
        if verdict is None:
            verdict = "H0" if r <= lo else "H1" if r >= hi else "none"
        out = {"a": args.a, "b": args.b, "panel": args.panel, "decks": n, "elo0": args.elo0, "elo1": args.elo1,
               "llr": round(r, 3), "bounds": [round(lo, 3), round(hi, 3)], "verdict": verdict, "games": 4 * len(scores),
               "errors": errors, "seconds": round(time.time() - t0, 1), **summary(scores)}
    finally:
        rp.close()
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out))


# ---------------------------------------------------------------- decisions

def decide(c: dict, m: int, s: dict) -> dict:
    """Evaluates card c's branch against the main line at m; returns the rung's record (with "status" if it ends)."""
    br, ref = BRANCHES / c["id"] / "checkpoint.pt", seg_path(m)
    rung = {"at": m, "t": now()}
    final = m >= c["base"] + s["seg"] * c.get("segments", 1)
    e1 = s["elo1"]
    if c["kind"] == "aa":
        rung["pilot"] = run_h2h(br, ref, "drafted", m, s, s["elo0"], e1, s["pairs_cap"], False)
        rung["archived"] = run_h2h(br, ref, "archived", m + 1, s, -e1, 0.0, 276, False)
        rung["meta_main"] = run_meta_eval(ref, ref, LAB / "tmp" / f"meta_main_{m:04d}.json", s)
        rung["meta_branch"] = run_meta_eval(br, ref, LAB / "tmp" / f"meta_{c['id']}_{m:04d}.json", s)
        rung["status"] = "measured"
        return rung
    if c["kind"] == "pilot":
        if not final:                                            # only "clearly worse" stops a longer card early
            rung["pilot"] = p = run_h2h(br, ref, "drafted", m, s, -e1, 0.0, s["early_cap"], True)
            if p.get("verdict") == "H0":
                rung["status"] = "failed-early"
            return rung
        if c.get("decide") == "s1":                             # Stage 1 cards: pilot competence, Elo only as a gate
            rung["s1_main"] = sm = run_s1(ref, f"main_{m:04d}", s)
            rung["s1_branch"] = sb = run_s1(br, f"{c['id']}_{m:04d}", s)
            rung["pilot"] = p = run_h2h(br, ref, "drafted", m, s, -e1, 0.0, s["early_cap"], False)
            if sm.get("error") or sb.get("error") or p.get("error"):
                rung["status"] = "error"
                return rung
            rung["gain"] = round(sb["s1"] - sm["s1"], 4)
            rung["status"] = "passed" if rung["gain"] >= s["s1_min_gain"] and p["verdict"] != "H0" else "failed"
            return rung
        lo1, hi1 = (-e1, 0.0) if c.get("test") == "noninferior" else (s["elo0"], e1)   # a speed-up need only not lose
        rung["pilot"] = p = run_h2h(br, ref, "drafted", m, s, lo1, hi1, s["pairs_cap"], True)
        if p.get("error"):
            rung["status"] = "error"
        elif p["verdict"] == "H1":
            rung["archived"] = g = run_h2h(br, ref, "archived", m + 1, s, -e1, 0.0, 276, False)
            rung["status"] = "passed" if g.get("verdict") != "H0" and not g.get("error") else "failed-gate"
        else:
            rung["status"] = "failed" if p["verdict"] == "H0" else "inconclusive"
        return rung
    if c["kind"] == "meta":
        if not final:
            return rung
        rule = c.get("rule", {"metric": "archived_mean", "min_gain": 0.03})
        rung["meta_main"] = mm = run_meta_eval(ref, ref, LAB / "tmp" / f"meta_main_{m:04d}.json", s)
        rung["meta_branch"] = mb = run_meta_eval(br, ref, LAB / "tmp" / f"meta_{c['id']}_{m:04d}.json", s)
        rung["pilot"] = p = run_h2h(br, ref, "drafted", m, s, -e1, 0.0, s["early_cap"], False)
        if mm.get("error") or mb.get("error") or p.get("error"):
            rung["status"] = "error"
            return rung
        gain = (mb[rule["metric"]] or 0) - (mm[rule["metric"]] or 0)
        rung["gain"] = round(gain, 4)
        # the plan reads drafting cards on deck shape too: the best decks may not move clearly away from the human shape
        rung["shape_loss"] = sl = round((mb.get("shape_dist") or 0) - (mm.get("shape_dist") or 0), 2)
        rung["status"] = ("passed" if gain >= rule["min_gain"] and p["verdict"] != "H0" and sl <= s["shape_max_loss"]
                          else "failed")
        return rung
    rung["status"] = "error"
    rung["error"] = f"unknown kind {c['kind']}"
    return rung


def adopt(c: dict, m: int, s: dict):
    """The main line goes on from card c's branch at m."""
    br = BRANCHES / c["id"] / "checkpoint.pt"
    shutil.copy2(seg_path(m), MAIN / f"seg_{m:04d}.before-{c['id']}.pt")
    shutil.copy2(br, MAIN / "checkpoint.pt")
    shutil.copy2(br, seg_path(m))
    s.update(settings())                    # from disk: an edit made since this cycle read them is kept (log #104)
    s["main_args"] ={**s["main_args"], **{k: v for k, v in c.get("args", {}).items()
                                           if k not in ("--pilot-opts", "--reseed", "--fork-from")}}
    s["adopted"] = s.get("adopted", []) + [{"card": c["id"], "at": m, "t": now()}]
    save_settings(s)
    with open(MAIN / "lineage.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": now(), "at": m, "adopted": c["id"], "args": c.get("args", {})}) + "\n")
    event("adopted", card=c["id"], at=m)


def milestone(k: int, s: dict):
    """The answer key of the main line at k (both archived panels, SimpleBot); a failure is retried, twice at most."""
    out, failed = MAIN / f"eval_it{k:04d}.json", MAIN / f"eval_it{k:04d}.failed"
    tries = int(failed.read_text()) if failed.exists() else 0
    if out.exists() or tries >= 2 or not seg_path(k).exists():
        return
    mm = run_meta_eval(seg_path(k), Path(s["milestone_common"]), out, s, simplebot=True)
    if mm.get("error"):
        failed.write_text(str(tries + 1))
    s1 = run_s1(seg_path(k), f"main_{k:04d}", s)                 # the plan's pilot-competence row
    event("milestone", at=k, **mm, s1=s1)


def prune(m: int, s: dict):
    """Keeps the main line's last two segment states and every milestone's."""
    for p in MAIN.glob("seg_*.pt"):
        if ".before-" in p.name:
            continue
        k = int(p.stem.split("_")[1])
        if k < m - s["seg"] and k % s["milestone_every"]:
            p.unlink()


# ---------------------------------------------------------------- the loop

def lab_main():
    for d in (LAB, CARDS, BRANCHES, MAIN, LAB / "tmp"):
        d.mkdir(parents=True, exist_ok=True)
    keep_awake()
    s = settings()
    if not (MAIN / "checkpoint.pt").exists():                     # the main line starts from meta-99's last state
        shutil.copy2(ROOT / SOURCE, MAIN / "checkpoint.pt")
        shutil.copy2(ROOT / Path(SOURCE).parent / "config.json", MAIN / "config.json")
        event("main-start", source=SOURCE)
    event("lab-start", pid=os.getpid(), gpu_share=os.environ.get("RL_GPU_SHARE"), cpu_threads=os.environ.get("RL_CPU_THREADS"))
    main_fail = 0
    while not STOP.exists():
        s = settings()
        if not wait_resources(s):
            break
        m = done(MAIN)
        if m % s["seg"]:                                          # a segment cut short: finish it
            ok = run_metagame(MAIN, cli(s["main_args"]), m + s["seg"] - m % s["seg"], s)
            main_fail = 0 if ok else main_fail + 1
            if main_fail >= 2:
                event("lab-error", what="main line failed twice")
                return 1
            if not ok:
                time.sleep(60)
            continue
        if not seg_path(m).exists():
            shutil.copy2(MAIN / "checkpoint.pt", seg_path(m))
        for k in range(s["milestone_every"], m + 1, s["milestone_every"]):    # any milestone not yet evaluated
            milestone(k, s)
        # 1. branches started before m and not yet decided at m: run them to m, then decide (a restart can fall between)
        running = cards({"running"})
        due = [c for c in running if c["base"] < m and all(r["at"] != m for r in c.get("rungs", []))]
        behind = [c for c in due if done(BRANCHES / c["id"]) < m]
        if due:
            for c in behind:
                if STOP.exists():
                    break
                bdir = BRANCHES / c["id"]
                extra = [] if (bdir / "checkpoint.pt").exists() else ["--fork-from", str(seg_path(c["base"]).relative_to(ROOT).as_posix())]
                if extra and c.get("warm"):                      # fork from the warm-started pilot instead
                    warm = run_warm(c, c["base"], s)
                    extra = ["--fork-from", str(warm.relative_to(ROOT).as_posix())] if warm else None
                if extra is None or not run_metagame(bdir, cli({**s["main_args"], **c.get("args", {})}) + extra, m, s):
                    c["status"] = "error"
                    save_card(c)
                    event("card-error", card=c["id"])
            if STOP.exists():
                break
            due = [load_card(CARDS / f"{c['id']}.json") for c in due]   # an edit made during the runs is kept (#104)
            passed = []
            for c in due:
                if c.get("status") != "running" or done(BRANCHES / c["id"]) < m:
                    continue
                rung = decide(c, m, s)
                c.setdefault("rungs", []).append(rung)
                if "status" in rung:
                    c["status"], c["ended"] = rung["status"], now()
                save_card(c)
                event("rung", card=c["id"], at=m, status=c["status"],
                      **{k: {q: v.get(q) for q in ("elo", "elo_lo", "elo_hi", "verdict", "games")}
                         for k, v in rung.items() if k in ("pilot", "archived") and isinstance(v, dict)})
                if c["status"] == "passed" and c.get("hold"):   # passed, not adopted, so cards running beside it keep
                    c["status"] = "passed-held"                  # their control; adopted later by a retest (#94)
                    save_card(c)
                elif c["status"] == "passed":
                    passed.append((rung.get("pilot", {}).get("elo", 0.0) if c["kind"] == "pilot" and "gain" not in rung
                                   else rung.get("gain", 0.0), c))
            if passed:
                passed.sort(key=lambda t: -t[0])
                best = passed[0][1]
                adopt(best, m, s)
                best["status"] = "adopted"
                save_card(best)
                for _, c in passed[1:]:                          # passed but not adopted: retest on the new main line
                    c["status"] = "passed-not-adopted"
                    save_card(c)
                    requeue(c, "-r", retest_of=c["id"])
                for c in cards({"running"}):                     # forked before the adoption: its control is gone, and
                    if c["base"] < m:                            # its next segment would take the adopted arguments too
                        c["status"], c["ended"] = "rebased", now()
                        save_card(c)
                        requeue(c, "-b", rebase_of=c["id"])
                        event("rebased", card=c["id"], at=m)
            continue
        # 2. start queued cards at m
        free = s["branches"] - len(running)
        for c in cards({"queued"})[:max(0, free)]:
            c.update(status="running", base=m, started=now())
            save_card(c)
            event("card-start", card=c["id"], base=m, kind=c["kind"])
        # 3. the main line runs one segment
        ok = run_metagame(MAIN, cli(s["main_args"]), m + s["seg"], s)
        main_fail = 0 if ok else main_fail + 1
        if main_fail >= 2:
            event("lab-error", what="main line failed twice")
            return 1
        if not ok:
            time.sleep(60)
            continue
        m2 = done(MAIN)
        if m2 % s["seg"] == 0 and m2 > m:
            shutil.copy2(MAIN / "checkpoint.pt", seg_path(m2))
            prune(m2, s)
            if m2 % s["milestone_every"] == 0:
                milestone(m2, s)
    event("lab-stop", reason="STOP file" if STOP.exists() else "end")
    return 0


def status_main():
    s = settings()
    print(f"main line: {done(MAIN)} iterations; adopted: {[a['card'] for a in s.get('adopted', [])]}")
    for c in cards():
        bdir = BRANCHES / c["id"]
        last = (c.get("rungs") or [{}])[-1]
        print(f"  {c['id']:32s} {c.get('status', 'queued'):20s} base {c.get('base', '-')!s:>5} "
              f"at {done(bdir) if bdir.exists() else '-'!s:>5}  "
              + (f"elo {last['pilot'].get('elo')} [{last['pilot'].get('elo_lo')}, {last['pilot'].get('elo_hi')}] "
                 f"{last['pilot'].get('verdict')}" if isinstance(last.get("pilot"), dict) else ""))
    if EVENTS.exists():
        print("last events:")
        for line in EVENTS.read_text(encoding="utf-8").splitlines()[-5:]:
            print("  " + line)


def start_main():
    """Starts `rl.lab run` in the background, outside the starting shell's job object: a lab started from a session's
    shell died with that session at 21:44 on 2026-10-19 (log #104)."""
    env = {"RL_GPU_SHARE": "0.333", "RL_CPU_THREADS": "10", **os.environ}
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_BREAKAWAY_FROM_JOB
    LAB.mkdir(parents=True, exist_ok=True)
    with open(LAB / "lab.stdout.log", "a") as out, open(LAB / "lab.stderr.log", "a") as err:
        p = subprocess.Popen([PY, "-m", "rl.lab", "run"], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                             stdout=out, stderr=err, creationflags=flags)
    print(f"lab started: pid {p.pid}, RL_GPU_SHARE {env['RL_GPU_SHARE']}, RL_CPU_THREADS {env['RL_CPU_THREADS']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "start", "status", "h2h"], nargs="?", default="run")
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--panel", choices=["drafted", "archived"], default="drafted")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--elo0", type=float, default=0.0)
    ap.add_argument("--elo1", type=float, default=15.0)
    ap.add_argument("--cap", type=int, default=1500, help="deck pairs at most (4 games each)")
    ap.add_argument("--batch", type=int, default=100, help="deck pairs between looks at the test")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--beta", type=float, default=0.05)
    ap.add_argument("--fixed", action="store_true", help="play every pair, no early stop")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.cmd == "h2h":
        return h2h_main(args)
    if args.cmd == "status":
        return status_main()
    if args.cmd == "start":
        return start_main()
    return lab_main()


if __name__ == "__main__":
    sys.exit(main() or 0)
