"""Pilot ablations (log #70, #75): the deck sets the variants train on, and their evaluation.

  decks  every distinct deck of runs/meta-99's population snapshots (it24-it149: random, evolved and
         mutant decks, all drafted without human input), split by lineage (population id % 5 == 0 held
         out); writes runs/abl/decks.json and runs/abl/matchups.json (random pairs of training decks for
         rl.train --matchups-file)
  mix    training pairs where each seat holds a rules-only random deck (rl.decks.random_deck) with
         probability --random-share and a deck of runs/abl/matchups.json otherwise: runs/abl/matchups_mix.json;
         and 200 fresh random decks for evaluation only: runs/abl/random_panel.json
  eval   evaluation only (the archived lists and SimpleBot never enter training), on a --panel of decks:
         heldout (decks.json's held-out decks), random (random_panel.json) or archived (the 24 lists).
         Pilots: run (its last snapshot up to --at), run@N (snapshot N), pilot-v2 / meta-99 (the anchors:
         pilot-v2 it349, runs/meta-99's final pilot), label=path:FILE or path:FILE (an rl.train snapshot or
         an rl.metagame checkpoint). Greedy; every game is a JSON line in runs/abl/rows.
         ladder     the anchors and --runs against each other: for every pair of pilots (a, b) and every
                    panel deck pair (x, y) (--fixed-pairs drawn once from --seed: a on x against b on y and a
                    on y against b on x; or --all-pairs, x == y included: only the first), 2 games, seats
                    alternating, with the same deals for every pair of pilots; Bradley-Terry ratings in Elo,
                    pilot-v2 = 0, with standard errors
         pairs      the same for each of --pairs A,B only: A's score with a 95% interval
         curve      every snapshot of every --runs run (from --curve-min-it) against pilot-v2
         simplebot  each --sb-runs pilot against SimpleBot (env/tools/evaluate.js) on the archived lists (seed
                    78 as log #49), the held-out decks (79) and the random panel (80); evaluate.js's per-game
                    JSON kept in runs/abl/sb_rows
         style      from each run's training log: entropy, game length and how games end, last 10 iterations

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/pilot_ablation.py decks
     PYTHONPATH=. .venv/Scripts/python notes/scripts/pilot_ablation.py mix --random-share 0.5
     PYTHONPATH=. .venv/Scripts/python notes/scripts/pilot_ablation.py eval --runs base@79 base-s2@79 ...
"""
import argparse
import glob
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from rl import limits
from rl.decks import Pool, archived_decks, deck_shape, random_deck
from rl.gpu_matrix import GpuMatrix
from rl.remote import RemotePool
from rl.train import build_model, export_policy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/abl"
ANCHORS = {"pilot-v2": "runs/pilot-v2/model_it00349.pt", "meta-99": "runs/meta-99/checkpoint.pt"}
ELO = 400 / np.log(10)
STAPLES = ["Professor Oak", "Bill", "Double Colorless Energy", "Energy Removal", "PlusPower", "Gust of Wind"]
SB_NOTE = ("every set is mirror piloting: both sides play deck floor(i/2) % n (env/tools/evaluate.js), so it is "
           "not all against all and seats follow deck parity")


def make_decks(args):
    pool = Pool()
    seen, train, held = set(), [], []
    for f in sorted(glob.glob(str(ROOT / "runs/meta-99/population_it*.pt"))):
        st = torch.load(f, map_location="cpu", weights_only=False)
        for a in st["population"]:
            key = tuple(sorted(a["deck"]))
            if key in seen:
                continue
            seen.add(key)
            d = {"name": f"m{a['id']}-it{st['iter']}", "cards": list(a["deck"])}
            assert pool.legal(pool.vector(d["cards"]))
            (held if a["id"] % 5 == 0 else train).append(d)
    rng = np.random.default_rng(args.seed)
    pairs = set()
    while len(pairs) < args.matchups:
        i, j = (int(x) for x in rng.choice(len(train), 2, replace=False))
        pairs.add((i, j))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "decks.json").write_text(json.dumps({"train": train, "heldout": held}))
    (OUT / "matchups.json").write_text(json.dumps([[train[i], train[j]] for i, j in sorted(pairs)]))
    shapes = {k: np.median([deck_shape(pool, pool.vector(d["cards"]))[k] for d in train + held])
              for k in ("pokemon", "trainer", "basic_energy", "special_energy")}
    print(f"{len(train)} training decks, {len(held)} held out, {len(pairs)} matchups; median shape {shapes}")


def make_mix(args):
    """matchups_mix.json: pair kinds PP / PR / RR (P = a side of matchups.json, R = a new random deck) with
    probabilities (1-s)^2, 2s(1-s), s^2; and random_panel.json (from --panel-seed, used nowhere in training).
    The archived lists enter only the printed statistics."""
    pool = Pool()
    rng = np.random.default_rng(args.mix_seed)
    abl = json.load(open(OUT / "matchups.json"))
    sides = [d for p in abl for d in p]
    assert not any(d["name"].startswith("rnd") for d in sides)
    s, n = args.random_share, args.mix_pairs
    p = np.array([(1 - s) ** 2, 2 * s * (1 - s), s ** 2])
    counts = np.round(n * p).astype(int)
    counts[np.argmax(p)] += n - counts.sum()
    assert counts[0] <= len(abl) and (counts >= 0).all()
    made = []

    def rnd():
        made.append({"name": f"rnd{len(made)}", "cards": pool.names(random_deck(pool, rng))})
        return made[-1]

    pp = [abl[int(i)] for i in rng.choice(len(abl), counts[0], replace=False)]
    pr = []
    for _ in range(counts[1]):
        pair = [sides[int(rng.integers(len(sides)))], rnd()]
        pr.append(pair if rng.random() < 0.5 else pair[::-1])
    rr = [[rnd(), rnd()] for _ in range(counts[2])]
    pairs = list(zip(["PP"] * len(pp) + ["PR"] * len(pr) + ["RR"] * len(rr), pp + pr + rr))
    pairs = [pairs[int(i)] for i in rng.permutation(len(pairs))]
    mix = [pair for _, pair in pairs]
    for d in (d for pair in mix for d in pair):
        assert pool.legal(pool.vector(d["cards"])), d["name"]
    (OUT / "matchups_mix.json").write_text(json.dumps(mix))
    prng = np.random.default_rng(args.panel_seed)
    panel = [{"name": f"rnd-eval{k}", "cards": pool.names(random_deck(pool, prng))} for k in range(200)]
    assert all(pool.legal(pool.vector(d["cards"])) for d in panel)
    (OUT / "random_panel.json").write_text(json.dumps(panel))

    def table(ds):
        X = np.array([pool.vector(d["cards"]) for d in ds])
        return X, [deck_shape(pool, v) for v in X]

    def median(sh):
        return {k: float(np.median([x[k] for x in sh])) for k in sh[0]}

    kinds = [k for k, pair in pairs for _ in pair]
    stats = {"abl": table(sides), "mix": table(d for pair in mix for d in pair)}
    print(f"{n} pairs, random share {s}: " + ", ".join(f"{k} {c}" for k, c in zip(["PP", "PR", "RR"], counts.tolist()))
          + f"; {len(made)} random training decks; random panel {len(panel)} decks (seed {args.panel_seed})")
    print("median shape: abl", median(stats["abl"][1]))
    for k in ["PP", "PR", "RR"]:
        print(f"  mix {k}", median([x for x, kind in zip(stats["mix"][1], kinds) if kind == k]))
    print("  random panel", median(table(panel)[1]))
    arch = np.array([v for _, v in archived_decks(pool)]).sum(0)        # archived copies per card (evaluation-side)
    for name, (X, sh) in stats.items():
        staples = {c: round(float((X[:, pool.name == c].sum(1) > 0).mean()), 3) for c in STAPLES}
        print(f"{name}: {len(X)} sides, >= 20 Trainers {np.mean([x['trainer'] >= 20 for x in sh]):.3f}, archived-card "
              f"presence (copy-weighted) {float((arch * (X > 0).mean(0)).sum() / arch.sum()):.3f}; per-side presence {staples}")


def load(path, info, device):
    """A pilot from an rl.train snapshot ("model") or an rl.metagame checkpoint ("net")."""
    st = torch.load(ROOT / path, map_location=device, weights_only=False)
    cfg = st["config"]
    net = build_model(SimpleNamespace(model="tokens", d=cfg["d"], tok_layers=cfg["layers"], heads=cfg["heads"],
                                      count_features=cfg.get("count_features", False),
                                      cross_layers=cfg.get("cross_layers", 1), cand_self=cfg.get("cand_self", 0),
                                      card_inputs=cfg.get("card_inputs", "all"), deck_tokens=cfg.get("deck_tokens", True),
                                      slot_bind=cfg.get("slot_bind", False), ability_text=cfg.get("ability_text", False),
                                      deck_mode=cfg.get("deck_mode", "joint"), deck_layers=cfg.get("deck_layers", 1),
                                      history=cfg.get("history", 0), memory=cfg.get("memory", "none"),
                                      value_tower=cfg.get("value_tower", 0), value_query=cfg.get("value_query", 0),
                                      aux_heads=cfg.get("aux_heads", 0)),
                      info).to(device)
    net.load_state_dict(st["model"] if "model" in st else st["net"])
    return net.eval()


def snapshots(run, at=None):
    """A run's snapshots in order; with `at`, only those from iteration `at` or before (an equal budget)."""
    snaps = sorted(glob.glob(str(OUT / run / "model_it*.pt")))
    return [s for s in snaps if at is None or int(Path(s).stem[-5:]) <= at]


def slug(label):
    return re.sub(r"[^A-Za-z0-9@._-]", "_", label)


def resolve(spec, at=None):
    """A pilot spec -> (label, path under ROOT): an anchor; run (runs/abl/run's last snapshot up to `at`);
    run@N (its iteration-N snapshot); label=path:FILE or path:FILE (label: the path, slugified)."""
    label, _, file = spec.rpartition("=")
    if file.startswith("path:"):
        label, path = label or slug(file[5:]), file[5:]
    elif spec in ANCHORS:
        label, path = spec, ANCHORS[spec]
    elif "@" in spec:
        run, it = spec.split("@")
        label, path = spec, f"runs/abl/{run}/model_it{int(it):05d}.pt"
    else:
        snaps = snapshots(spec, at)
        if not snaps:
            raise SystemExit(f"pilot {spec}: no snapshots in runs/abl/{spec}")
        label, path = spec, Path(snaps[-1]).relative_to(ROOT).as_posix()
    if not (ROOT / path).exists():
        raise SystemExit(f"pilot {spec}: no file {path}")
    return label, path


def panel_decks(panel):
    """The evaluation decks [{name, cards}]: held-out population decks, fresh random decks, or the archived lists
    (in env/decks.js order)."""
    if panel == "heldout":
        return json.load(open(OUT / "decks.json"))["heldout"]
    if panel == "random":
        return json.load(open(OUT / "random_panel.json"))
    pool = Pool()
    return [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]


def fixed_pairs(H, n, seed):
    """n ordered deck pairs (x, y), x != y, drawn once: the same for every pair of pilots."""
    rng = np.random.default_rng(seed)
    return [tuple(int(v) for v in rng.choice(H, 2, replace=False)) for _ in range(n)]


def fixed_h2h(gm, nets, labels, decks, todo, idx_pairs, games, seed, swap=True, reps=1, panel=None):
    """Wins and games [n, n] between pilots, the run stats, and the games as rows {(a, b): [row]}. Panel = each
    pilot's copy of the H decks; for each pilot pair (a, b) of todo, each rep r and each entry q = (x, y) of
    idx_pairs: a on x against b on y and, with swap, a on y against b on x, `games` games each, seats alternating.
    Entry (r, q, direction) has the same deals for every pilot pair (pair_keys), all in one gm.play."""
    n, H, Q, D = len(nets), len(decks), len(idx_pairs), 2 if swap else 1
    pan = [{"name": f"p{m}d{h}", "cards": decks[h]["cards"]} for m in range(n) for h in range(H)]
    pairs, keys = [], []
    for a, b in todo:
        for r in range(reps):
            for q, (x, y) in enumerate(idx_pairs):
                pairs.append((a * H + x, b * H + y))
                keys.append((r * Q + q) * D)
                if swap:
                    pairs.append((a * H + y, b * H + x))
                    keys.append((r * Q + q) * D + 1)
    W, G, _ = gm.play(pan, games, seed, pairs=pairs, slots=[m for m in range(n) for _ in range(H)],
                      models=dict(enumerate(nets)), pair_keys=keys)
    np.fill_diagonal(W, 0)
    np.fill_diagonal(G, 0)
    w = W.reshape(n, H, n, H).sum((1, 3))
    g = G.reshape(n, H, n, H).sum((1, 3))
    rows = {}
    for x in sorted(gm.results, key=lambda x: (x["i"] // H, x["j"] // H, x["seed"])):
        a, b, key = x["i"] // H, x["j"] // H, (x["seed"] - seed * 1000003) // games
        rows.setdefault((a, b), []).append(
            {"a": labels[a], "b": labels[b], "panel": panel, "seed": x["seed"], "entry": key // D % Q, "rep": key // D // Q,
             "deck_a": decks[x["i"] % H]["name"], "deck_b": decks[x["j"] % H]["name"], "seat_a": x["iSeat"],
             "score_a": 1.0 if x["winner"] == x["iSeat"] else 0.0 if x["winner"] in (1, 2) else 0.5,
             "ending": x.get("ending"), "steps": x["steps"], "error": bool(x.get("error"))})
    return w, g, dict(gm.last), rows


def save_rows(stem, part, labels, rows):
    """Each pilot pair's games, one JSON line each: runs/abl/rows/<stem>__<part>__<a>__<b>.jsonl -> {(a, b): path}."""
    (OUT / "rows").mkdir(exist_ok=True)
    files = {}
    for (a, b), rs in rows.items():
        f = OUT / "rows" / f"{stem}__{part}__{slug(labels[a])}__{slug(labels[b])}.jsonl"
        f.write_text("".join(json.dumps(r) + "\n" for r in rs))
        files[a, b] = f.relative_to(ROOT).as_posix()
    return files


def bradley_terry(w, g, anchor):
    """Ratings r (natural units) maximizing sum w_ab log s(r_a - r_b), r[anchor] = 0, and their standard errors."""
    n = len(w)
    r = np.zeros(n)
    free = [i for i in range(n) if i != anchor]

    def hessian(r):
        p = 1 / (1 + np.exp(-(r[:, None] - r[None, :])))
        h = g * p * (1 - p)
        h[np.diag_indices(n)] = -h.sum(1)
        return p, h

    for _ in range(100):
        p, h = hessian(r)
        grad = (w - g * p).sum(1)
        step = np.linalg.solve(h[np.ix_(free, free)], -grad[free])
        r[free] += step
        if np.abs(step).max() < 1e-10:
            break
    _, h = hessian(r)
    se = np.zeros(n)
    se[free] = np.sqrt(np.diag(np.linalg.inv(-h[np.ix_(free, free)])))
    return r, se


def simplebot(spec, decks_file, games, seed, workers, rows, history=0):
    """SimpleBot against the pilot `spec`; evaluate.js's JSON (per-game rows with their deal seeds) kept at `rows`.
    history: the pilot's action-history window (its config), which the workers must encode."""
    rows.parent.mkdir(exist_ok=True)
    cmd = ["node", str(ROOT / "env/tools/evaluate.js"), "--x", spec, "--y", "simplebot", "--d1", "all", "--d2", "all",
           "--games", str(games), "--workers", str(workers), "--concurrency", "8", "--seed", str(seed), "--json", str(rows),
           "--history", str(history)]
    if decks_file:
        cmd += ["--decks-file", str(decks_file)]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    r = json.load(open(rows))
    return {"win": round(r["all"]["xWinRate"], 4), "ci95": round(r["all"]["ci95"], 4), "games": r["all"]["n"],
            "seed": seed, "rows": rows.relative_to(ROOT).as_posix()}


def simplebot_gpu(net, decks, games, seed, workers, device):
    """SimpleBot against `net` through the inference server (a pilot with memory has no ONNX export; log #76),
    as evaluate.js: game g has both sides on deck floor(g / 2) % n, the pilot's seat alternating, greedy; a draw or
    cut game scores 0.5. The deals differ from evaluate.js's, so the numbers compare in distribution only."""
    n = len(decks)
    jobs = [{"i": (g // 2) % n, "j": n + (g // 2) % n, "iSeat": 1 + g % 2, "seed": seed * 1000003 + g, "bot": "simplebot"}
            for g in range(games)]
    pool = RemotePool(limits.cap_workers(workers))
    try:
        W = len(pool.procs)
        msgs = [{"cmd": "games", "encoding": "tokens", "decks": decks + decks, "jobs": jobs[w::W], "greedy": True,
                 "concurrency": 16, "history": int(net.cfg.get("history", 0) or 0)} for w in range(W)]
        res = [r for rep in pool.collect(msgs, {0: net}, device) for r in rep["results"]]
    finally:
        pool.close()
    x = [1.0 if r["winner"] == r["iSeat"] else 0.0 if r["winner"] in (1, 2) else 0.5 for r in res]
    p = float(np.mean(x))
    return {"win": round(p, 4), "ci95": round(1.96 * float(np.sqrt(p * (1 - p) / len(x))), 4), "games": len(x), "seed": seed,
            "path": "gpu", "errors": sum(1 for r in res if r.get("error"))}


def style(run, at=None):
    run, _, it = run.partition("@")                     # run@N: up to snapshot N
    at = int(it) if it else at
    rows = {}
    for line in open(OUT / run / "log.jsonl"):           # a resumed run may repeat an iteration: keep the last
        if '"transitions"' in line:
            r = json.loads(line)
            if at is None or r["iteration"] <= at:
                rows[r["iteration"]] = r
    rows = [rows[k] for k in sorted(rows)]
    last = rows[-10:]
    ends = Counter()
    for r in last:
        ends.update(r["endings"])
    tot = sum(ends.values())
    return {"iterations": len(rows), "entropy": round(float(np.mean([r["entropy"] for r in last])), 3),
            "v_loss": round(float(np.mean([r["v_loss"] for r in last])), 4),
            "steps_per_game": round(float(np.mean([r["steps_per_game"] for r in last])), 1),
            "endings": {k: round(v / tot, 3) for k, v in ends.most_common()},
            "seconds_per_iter": round(float(np.mean([r["collect_s"] + r["train_s"] for r in rows])), 1)}


def evaluate(args):
    gpu = [p for p in ("ladder", "pairs", "curve") if p in args.parts]
    device = "cuda" if gpu and torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    held = json.load(open(OUT / "decks.json"))["heldout"]
    (OUT / "heldout.json").write_text(json.dumps(held))
    out_file, stem = OUT / args.out, Path(args.out).stem
    out = json.loads(out_file.read_text()) if out_file.exists() else {}
    paths = {}

    def pilot(spec):
        label, path = resolve(spec, args.at)
        assert paths.setdefault(label, path) == path, f"two pilots labelled {label}"
        return label

    def save():
        out_file.write_text(json.dumps(out, indent=1))

    rp = RemotePool(args.workers if gpu else 1)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * len(rp.procs))[0]
    try:
        if gpu:
            decks = panel_decks(args.panel)
            H, cache = len(decks), {}
            if args.all_pairs:
                idx, swap, mode = [(x, y) for x in range(H) for y in range(H)], False, {"all_pairs": True, "reps": args.reps}
            else:
                idx, swap, mode = fixed_pairs(H, args.fixed_pairs, args.seed), True, {"fixed_pairs": args.fixed_pairs, "reps": args.reps}
            gm = GpuMatrix.attach(None, rp, args.workers, device=device)

            def nets(labels):
                for k in labels:
                    if k not in cache:
                        cache[k] = load(paths[k], info, device)
                return [cache[k] for k in labels]

        if "ladder" in args.parts:
            names = list(dict.fromkeys(pilot(s) for s in list(ANCHORS) + args.runs))
            n = len(names)
            w, g, last, rows = fixed_h2h(gm, nets(names), names, decks, [(a, b) for a in range(n) for b in range(a + 1, n)],
                                         idx, 2, args.seed, swap, args.reps, args.panel)
            save_rows(stem, "ladder", names, rows)
            r, se = bradley_terry(w, g, 0)
            out["ladder"] = {"pilots": names, "paths": [paths[k] for k in names], "matrix": {"wins": w.tolist(), "games": g.tolist()},
                             "elo": dict(zip(names, np.round(r * ELO, 1).tolist())),
                             "elo_se": dict(zip(names, np.round(se * ELO, 1).tolist())),
                             "score": dict(zip(names, np.round(w.sum(1) / g.sum(1), 4).tolist())), "run": last,
                             "panel": args.panel, "seed": args.seed, **mode}
            print("ladder", json.dumps({k: (out["ladder"]["elo"][k], out["ladder"]["elo_se"][k]) for k in names}), json.dumps(last), flush=True)
            save()
        if "pairs" in args.parts:
            duels = [tuple(pilot(s) for s in p.split(",")) for p in args.pairs]
            names = list(dict.fromkeys(k for d in duels for k in d))
            todo = [(names.index(a), names.index(b)) for a, b in duels]
            assert all(a != b for a, b in todo) and len(set(todo)) == len(todo), "pairs: two distinct pilots, each pair once"
            _, _, last, rows = fixed_h2h(gm, nets(names), names, decks, todo, idx, 2, args.seed, swap, args.reps, args.panel)
            files = save_rows(stem, "pairs", names, rows)
            out.setdefault("pairs", {})
            for a, b in todo:
                won, m = sum(x["score_a"] for x in rows[a, b]), len(rows[a, b])
                p = won / m
                out["pairs"][f"{names[a]} vs {names[b]}"] = {"a": names[a], "b": names[b], "panel": args.panel, "seed": args.seed,
                                                             "wins_a": won, "games": m, "score_a": round(p, 4),
                                                             "ci95": round(1.96 * float(np.sqrt(p * (1 - p) / m)), 4),
                                                             "rows": files[a, b], **mode}
                print("pairs", f"{names[a]} vs {names[b]}", round(p, 4), m, flush=True)
            print("pairs", json.dumps(last), flush=True)
            save()
        if "curve" in args.parts:
            out.setdefault("curve", {})
            anchor = pilot("pilot-v2")
            cidx = fixed_pairs(H, args.curve_pairs, args.seed + 1)
            for run in args.runs:
                snaps = [s for s in snapshots(run, args.at) if int(Path(s).stem[-5:]) >= args.curve_min_it]
                labels = [anchor] + [f"{run}@{int(Path(s).stem[-5:])}" for s in snaps]
                cn = nets([anchor]) + [load(Path(s).relative_to(ROOT), info, device) for s in snaps]
                w, g, _, rows = fixed_h2h(gm, cn, labels, decks, [(k, 0) for k in range(1, len(cn))], cidx, 2,
                                          args.seed + 1, True, 1, args.panel)
                save_rows(stem, "curve", labels, rows)
                out["curve"][run] = {Path(s).stem[-5:]: round(float(w[k + 1, 0] / g[k + 1, 0]), 4) for k, s in enumerate(snaps)}
                print("curve", run, out["curve"][run], flush=True)
                save()
    finally:
        rp.close()
    if "simplebot" in args.parts:                         # CPU, after the GPU pool is closed
        out.setdefault("simplebot", {})
        out["simplebot_note"] = SB_NOTE
        sets = [("archived", args.sb_archived_games, args.sb_archived_seed, None),
                ("heldout", args.sb_heldout_games, 79, OUT / "heldout.json"),
                ("random", args.sb_random_games, 80, OUT / "random_panel.json")]
        for k in [pilot(s) for s in (args.sb_runs or list(ANCHORS) + args.runs)]:
            todo = [s for s in sets if s[1] and (args.redo or s[0] not in out["simplebot"].get(k, {}))]
            if not todo:
                continue
            onnx = OUT / f"_{slug(k)}.onnx"
            net = load(paths[k], info, "cpu")
            if net.cfg.get("memory", "none") != "none":
                device = "cuda" if torch.cuda.is_available() else "cpu"
                net = net.to(device)
                for name, games, seed, decks_file in todo:
                    decks = panel_decks("archived") if decks_file is None else json.load(open(decks_file))
                    out["simplebot"].setdefault(k, {})[name] = simplebot_gpu(net, decks, games, seed, args.workers, device)
                    print("simplebot", k, name, out["simplebot"][k][name], flush=True)
                    save()
                continue
            spec = export_policy(net, onnx, "tokens")
            try:
                for name, games, seed, decks_file in todo:
                    out["simplebot"].setdefault(k, {})[name] = simplebot(spec, decks_file, games, seed, args.workers,
                                                                         OUT / "sb_rows" / f"{stem}__{slug(k)}__{name}.json",
                                                                         history=net.cfg.get("history", 0))
                    print("simplebot", k, name, out["simplebot"][k][name], flush=True)
                    save()
            finally:
                onnx.unlink(missing_ok=True)
    if "style" in args.parts:
        out["style"] = {run: style(run, args.at) for run in args.runs}
        for run in args.runs:
            print("style", run, out["style"][run])
    save()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["decks", "mix", "eval"])
    ap.add_argument("--matchups", type=int, default=2048)
    ap.add_argument("--random-share", type=float, default=0.5, help="mix: chance that a seat holds a random deck")
    ap.add_argument("--mix-seed", type=int, default=12)
    ap.add_argument("--panel-seed", type=int, default=13, help="mix: the random evaluation panel")
    ap.add_argument("--mix-pairs", type=int, default=4096)
    ap.add_argument("--runs", nargs="*", default=[])
    ap.add_argument("--parts", nargs="*", default=["ladder", "curve", "simplebot", "style"])
    ap.add_argument("--panel", choices=["heldout", "random", "archived"], default="heldout")
    ap.add_argument("--fixed-pairs", type=int, default=400, help="ladder/pairs: panel deck pairs (4 games each)")
    ap.add_argument("--all-pairs", action="store_true", help="ladder/pairs: every ordered deck pair instead (2 games each)")
    ap.add_argument("--reps", type=int, default=1, help="ladder/pairs: repeat the deck pairs with new deals")
    ap.add_argument("--pairs", nargs="*", default=[], help="pairs: A,B pilot specs")
    ap.add_argument("--curve-pairs", type=int, default=200, help="curve: panel deck pairs per snapshot (4 games each)")
    ap.add_argument("--curve-min-it", type=int, default=0)
    ap.add_argument("--sb-runs", nargs="*", default=[], help="simplebot: pilot specs (default: anchors + --runs)")
    ap.add_argument("--sb-archived-games", type=int, default=672)
    ap.add_argument("--sb-archived-seed", type=int, default=78)
    ap.add_argument("--sb-heldout-games", type=int, default=468)
    ap.add_argument("--sb-random-games", type=int, default=400)
    ap.add_argument("--redo", action="store_true", help="simplebot: redo pilots already in the output")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=70)
    ap.add_argument("--out", default="eval.json", help="under runs/abl")
    ap.add_argument("--at", type=int, default=None, help="use each run's snapshots up to this iteration (equal budget)")
    args = ap.parse_args(argv)
    if args.cmd == "decks":
        make_decks(args)
    elif args.cmd == "mix":
        make_mix(args)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
