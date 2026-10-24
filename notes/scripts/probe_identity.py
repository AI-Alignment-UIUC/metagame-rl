"""X10: does the pilot read Trainer identity? (runs/probe/X10/record.md; evaluation only, nothing trains)

Copies of a pilot whose card-specific inputs (the learned per-card residual card_resid and the card_feats and text_emb
buffers; the ability rows too when the pilot has them) are permuted over a set of cards by a fixed derangement, so card
c reads as pi(c) wherever its id appears (board, hand, discards, decklists, options). Nothing else changes: the rules,
legal options, effects and prompts are the engine's.
  P_T  the pool's 42 Trainers, deranged within each structured-feature class (40, and Clefairy Doll / Mysterious Fossil,
       which carry HP), so card_feats stay as they were and only what is particular to a Trainer moves
  P_E  the 6 basic Energy types, full inputs (Fire reads as another type): the positive control
Then notes/scripts/trainer_value.py's cell (each list against its copy with a Trainer group turned into its commonest
basic Energy, one pilot on both seats, the same deals per list) for the original, P_T and P_E, and each permuted pilot
against the original on the lists' mirrors (both seats; P_T and P_E get the same deals per list).

Run (runs/probe/X10/chain.sh): PYTHONPATH=. .venv/Scripts/python notes/scripts/probe_identity.py \
    --pilot runs/pilot/C49-sd/model_it00199.pt --dir runs/probe/X10 --round-turns 20-45 --out runs/probe/X10/x10.json
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trainer_value as tv                                    # noqa: E402  (variants: the lists' Energy copies)
from rl import limits                                        # noqa: E402
from rl.decks import Pool, archived_decks                    # noqa: E402
from rl.gpu_matrix import GpuMatrix, load_policy             # noqa: E402
from rl.remote import RemotePool                             # noqa: E402
from rl.token_model import card_feature_matrix               # noqa: E402
from rl.train import round_turns                             # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CARD_ROWS = ("card_resid.weight", "card_feats", "text_emb")   # every input indexed by card id (rl/token_model.py card_emb)
BLIND, H2H_BLIND, READS, BITE = 0.02, 0.47, 0.04, 0.44          # the bands of record.md, written before launch
Z_READS = 2.0     # a move reads only if it is also this many of its SEs: at 32 games a pair a group's paired SE is about
                  # 0.025 (binomial estimate), so 0.04 alone is 1.6 SE and noise in one of 5 groups would often clear it


def derange(ids: list, rng) -> dict:
    """{c: pi(c)}, a permutation of ids with no fixed point."""
    assert len(ids) > 1, f"a class of one card cannot be deranged: {ids}"
    while True:
        p = [int(x) for x in rng.permutation(ids)]
        if all(a != b for a, b in zip(ids, p)):
            return dict(zip(ids, p))


def mappings(table: list, seed: int) -> dict:
    feats = card_feature_matrix(table)
    rng = np.random.default_rng(seed)
    classes = {}
    for c in table:
        if c["superType"] == 2:
            classes.setdefault(feats[c["id"]].tobytes(), []).append(c["id"])
    trainers = {}
    for ids in classes.values():
        trainers.update(derange(sorted(ids), rng))
    basics = sorted(c["id"] for c in table if c["superType"] == 3 and c["energyType"] == 0)
    return {"trainer": trainers, "energy": derange(basics, rng)}


def permuted(state: dict, perm: dict) -> dict:
    """The checkpoint with row c of every card-indexed input taken from row pi(c): card c reads as pi(c)."""
    sd = dict(state["model"])
    n = sd["card_resid.weight"].shape[0]
    src = torch.arange(n)
    for c, p in perm.items():
        src[c] = p
    for k in CARD_ROWS:
        if k in sd:
            sd[k] = sd[k][src].clone()
    if "ability_index" in sd:                                  # [n_cards * names], by card then name
        sd["ability_index"] = sd["ability_index"].view(n, -1)[src].reshape(-1).clone()
    return {"config": state["config"], "model": sd}, src


def make(pilot: str, out_dir: Path, seed: int, table: list) -> dict:
    """Writes permuted.pt (P_T) and permuted_energy.pt (P_E) and checks that each reads card c exactly as the original
    reads pi(c), and every other card as before."""
    state = torch.load(ROOT / pilot, map_location="cpu", weights_only=False)
    name = {c["id"]: c["fullName"] for c in table}
    out_dir.mkdir(parents=True, exist_ok=True)
    orig, _ = load_policy(pilot, "cpu")
    ids = torch.arange(state["model"]["card_resid.weight"].shape[0])
    info = {}
    for kind, perm in mappings(table, seed).items():
        path = out_dir / ("permuted.pt" if kind == "trainer" else "permuted_energy.pt")
        st, src = permuted(state, perm)
        st["probe"] = {"of": pilot, "kind": kind, "seed": seed, "map": {name[c]: name[p] for c, p in perm.items()}}
        torch.save(st, path)
        m, _ = load_policy(str(path), "cpu")                   # ROOT / an absolute path is that path
        with torch.no_grad():
            gap = float((m.card_emb(ids) - orig.card_emb(src)).abs().max())
        assert gap < 1e-5, (kind, gap)
        rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        info[kind] = {"path": rel, "moved": len(perm), "map": st["probe"]["map"], "card_emb_check": gap}
        print(f"{kind}: {len(perm)} cards permuted -> {info[kind]['path']} (card_emb(c) == original card_emb(pi(c)): "
              f"max gap {gap})", flush=True)
    return info


def mean_se(x) -> dict:
    x = np.asarray(x, dtype=float)
    se = float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.5
    return {"n": len(x), "mean": round(float(x.mean()), 4), "se": round(se, 4)}


def elo(p: float) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return round(400 * math.log10(p / (1 - p)), 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="runs/pilot/C49-sd/model_it00199.pt")
    ap.add_argument("--dir", default="runs/probe/X10", help="where the permuted checkpoints go")
    ap.add_argument("--perm-seed", type=int, default=10)
    ap.add_argument("--make-only", action="store_true")
    ap.add_argument("--lists", type=int, default=24, help="the first N archived lists (a smoke uses 2)")
    ap.add_argument("--groups", nargs="+", default=["all", "draw", "search", "disrupt", "tempo"])
    ap.add_argument("--games", type=int, default=32, help="trainer_value cell: games per list pair (both seats)")
    ap.add_argument("--h2h-games", type=int, default=64, help="permuted vs original: games per mirror (both seats)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--round-turns", default="20-45", help='the 2000 round rule in every game, "T" or "A-B"; "0" off')
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    pool = Pool()
    out_dir = Path(args.dir) if Path(args.dir).is_absolute() else ROOT / args.dir
    t0 = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    workers = limits.cap_workers(args.workers)
    limits.apply(device, workers)
    info = make(args.pilot, out_dir, args.perm_seed, pool.cards)
    if args.make_only:
        return
    pilots = {"original": args.pilot, "P_T": info["trainer"]["path"], "P_E": info["energy"]["path"]}
    models = {k: load_policy(v, device)[0] for k, v in pilots.items()}
    rounds = round_turns(args.round_turns)
    decks = [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)][:args.lists]
    alld, pairs = tv.variants(pool, decks, args.groups)
    res = {"pilot": args.pilot, "perm_seed": args.perm_seed, "permuted": info, "lists": len(decks), "games": args.games,
           "h2h_games": args.h2h_games, "round_turns": args.round_turns, "seed": args.seed, "pairs": pairs,
           "trainer_value": {}, "h2h": {}, "cells": {}}
    rp = RemotePool(workers)
    rp.pace = 0.25
    try:
        gm = GpuMatrix.attach(models["original"], rp, workers, device=device)
        rates = {}
        for k, m in models.items():                 # the trainer_value cell, one pilot on both seats, same deals
            W, G, _ = gm.play(alld, args.games, args.seed, pairs=[(p["base"], p["variant"]) for p in pairs],
                              pair_keys=[p["base"] for p in pairs], round_turns=rounds, models={0: m})
            res["cells"]["tv_" + k] = gm.last
            print("tv", k, gm.last, flush=True)
            rates[k] = [float(W[p["base"], p["variant"]] / max(G[p["base"], p["variant"]], 1)) for p in pairs]
            by = {g: mean_se([r for r, p in zip(rates[k], pairs) if p["group"] == g]) for g in args.groups}
            res["trainer_value"][k] = {"by_group": by, "per_pair": [round(r, 4) for r in rates[k]]}
            print("tv", k, json.dumps(by), flush=True)
        for k in ("P_T", "P_E"):                    # paired on deals: permuted minus original, per list, by group
            diff = [(a - b, p) for a, b, p in zip(rates[k], rates["original"], pairs)]
            mo = {g: mean_se([d for d, p in diff if p["group"] == g]) for g in args.groups}
            per_list = {}                           # and per list, the mean over its search, disrupt and tempo pairs
            for d, p in diff:
                if p["group"] in ("search", "disrupt", "tempo"):
                    per_list.setdefault(p["base"], []).append(d)
            if per_list:
                mo["sdt"] = mean_se([np.mean(v) for v in per_list.values()])
            res["trainer_value"][k]["minus_original"] = mo
        n = len(decks)                              # mirrors: deck k (original, slot 0) vs its copy under P_T or P_E
        hp = [(k, n + k) for k in range(n)] + [(k, 2 * n + k) for k in range(n)]
        W, G, _ = gm.play(decks * 3, args.h2h_games, args.seed + 1, pairs=hp, pair_keys=[i for i, _ in hp],
                          round_turns=rounds, slots=[0] * n + [1] * n + [2] * n,
                          models={0: models["original"], 1: models["P_T"], 2: models["P_E"]})
        res["cells"]["h2h"] = gm.last
        print("h2h", gm.last, flush=True)
        for s, k in ((1, "P_T"), (2, "P_E")):
            per = [float(W[s * n + i, i] / max(G[s * n + i, i], 1)) for i in range(n)]
            games = int(sum(G[s * n + i, i] for i in range(n)))
            ms = mean_se(per)
            res["h2h"][k] = {**ms, "games": games, "binomial_se": round(0.5 / math.sqrt(max(games, 1)), 4),
                             "elo": elo(ms["mean"]), "per_list": {d["name"]: round(x, 4) for d, x in zip(decks, per)}}
            print("h2h", k, "vs original:", json.dumps({q: v for q, v in res["h2h"][k].items() if q != "per_list"}),
                  flush=True)
    finally:
        rp.close()
    # The bands (record.md), read off the numbers: never a substitute for reading them.
    mo = res["trainer_value"]["P_T"]["minus_original"]
    moves = {g: mo[g]["mean"] for g in args.groups}
    z = {g: round(v["mean"] / v["se"], 2) if v["se"] > 0 else None for g, v in mo.items()}   # each move in its SEs
    h_t, h_e = res["h2h"]["P_T"]["mean"], res["h2h"]["P_E"]["mean"]
    h_se = res["h2h"]["P_T"]["binomial_se"]
    worst = max(abs(v) for v in moves.values())
    bites = h_e <= BITE
    reads = [g for g in args.groups if abs(mo[g]["mean"]) >= max(READS, Z_READS * mo[g]["se"])]
    if abs(h_t - 0.5) >= max(READS, Z_READS * h_se):
        reads.append("h2h")
    if reads:
        call = "identity-reading" + ("" if bites else " (the Energy control did not bite: check the copies)")
    elif worst <= BLIND and h_t >= H2H_BLIND:
        call = "identity-blind" if bites else "void: the Energy control did not bite"
    else:
        call = "between"
    errors = sum(c["errors"] for c in res["cells"].values())
    total = sum(c["games"] for c in res["cells"].values())
    res["readout"] = {"P_T_minus_original": moves, "sdt": mo.get("sdt"), "z": z, "h2h_P_T": h_t, "h2h_P_E": h_e,
                      "h2h_se": h_se, "control_bites": bites, "reads": reads,
                      "call": call, "errors": errors, "games": total, "error_share": round(errors / max(total, 1), 4),
                      "kill": errors > 0.01 * total, "seconds": round(time.time() - t0, 1)}
    print("readout", json.dumps(res["readout"]), flush=True)
    if args.out:
        o = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
        o.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
