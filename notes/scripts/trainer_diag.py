"""Does the pilot play Trainers well? Two diagnostics on a population checkpoint (rl/metagame.py), log #68.
Evaluation only: the hand-built deck variants and SimpleBot never enter training.

  usage  games among the population's best decks, every decision recorded (greedy play). At each decision
         where a Trainer can be played: the probability the pilot gives to playing one, what it chooses
         instead (verb), and per Trainer card how often it is played when it can be
  swap   each of the best decks with 6 basic Energy replaced by draw Trainers (Bill up to 4, then
         Professor Oak up to 3, then Computer Search up to 4, under the copy limit), against the other best decks, under two pilots:
         the population's pilot (greedy, GPU) and SimpleBot on both sides (env/tools/evaluate.js). If the
         swap helps SimpleBot but not the pilot, the pilot is what holds Trainers back

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/trainer_diag.py --checkpoint runs/meta-99/checkpoint.pt \
        --out notes/data/eval/trainer_diag.json
"""
import argparse
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from rl import limits
from rl.decks import Pool, deck_shape
from rl.gpu_matrix import GpuMatrix
from rl.remote import RemotePool
from rl.rollouts import concat, read_rollout
from rl.train import TOKEN_FIELDS, build_model

ROOT = Path(__file__).resolve().parents[2]
VERBS = {1: "pass", 2: "attach", 3: "basic", 4: "evolve", 5: "trainer", 6: "retreat", 7: "attack", 8: "power", 9: "stadium"}
TRAINER = 5
DRAW = (("Bill BS", 4), ("Professor Oak BS", 3), ("Computer Search BS", 4))


def best_decks(st, pool, k):
    pop = st["population"]
    score = [a["sum"] / a["n"] if a.get("n") else a.get("last", 0.0) for a in pop]
    order = sorted(range(len(pop)), key=lambda i: -score[i])[:k]
    return [(pop[i]["id"], pool.vector(pop[i]["deck"]), round(score[i], 4)) for i in order]


def variant(pool, v, n=6):
    """v with up to n basic Energy (the most common kinds first) replaced by draw Trainers."""
    w = v.copy()
    added = 0
    for name, cap in DRAW:
        c = pool.id[name]
        same = [i for i in range(1, pool.n) if pool.name[i] == pool.name[c]]
        while added < n and w[same].sum() < cap:
            w[c] += 1
            added += 1
    for _ in range(added):
        e = [i for i in np.nonzero(w)[0] if pool.basic_energy[i]]
        w[max(e, key=lambda i: w[i])] -= 1
    assert pool.legal(w)
    return w, added


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--top", type=int, default=12, help="best decks for the usage games")
    ap.add_argument("--swap-decks", type=int, default=6, help="best decks given the Energy -> Trainer swap")
    ap.add_argument("--usage-games", type=int, default=600)
    ap.add_argument("--swap-games", type=int, default=64, help="pilot games per pair in the swap test")
    ap.add_argument("--simplebot-games", type=int, default=200, help="SimpleBot games per deck in the swap test")
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    pool = Pool()
    st = torch.load(ROOT / args.checkpoint, map_location=device, weights_only=False)
    best = best_decks(st, pool, args.top)
    out = {"checkpoint": args.checkpoint, "iter": st.get("iter"), "decks": [{"id": i, "score": s, **deck_shape(pool, v)} for i, v, s in best]}

    rp = RemotePool(args.workers)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]
    cfg = st["config"]
    net = build_model(SimpleNamespace(model="tokens", d=cfg["d"], tok_layers=cfg["layers"], heads=cfg["heads"],
                                      count_features=cfg.get("count_features", False), cross_layers=cfg.get("cross_layers", 1),
                                      cand_self=cfg.get("cand_self", 0)), info).to(device)
    net.load_state_dict(st["net"])
    net.eval()
    try:
        # 1. usage: random pairs of the best decks, every decision recorded, greedy
        rng = np.random.default_rng(args.seed)
        decks = [{"name": f"d{i}", "cards": pool.names(v)} for i, v, _ in best]
        jobs = []
        for g in range(args.usage_games):
            i, j = rng.choice(len(decks), 2, replace=False)
            jobs.append({"i": int(i), "j": int(j), "iSeat": 1 + g % 2, "seed": args.seed * 1_000_003 + g})
        with tempfile.TemporaryDirectory() as tmp:
            msgs = [{"cmd": "games", "encoding": "tokens", "greedy": True, "concurrency": 32, "decks": decks,
                     "jobs": jobs[w::args.workers], "out": str(Path(tmp) / f"u{w}.bin")} for w in range(args.workers)]
            replies = rp.collect(msgs, {0: net}, device)
            b = concat([read_rollout(r["out"]) for r in replies])
        T = len(b["action"])
        cand = b["obs.cand"].reshape(T, -1, 6)
        n_cand = b["obs.nCand"]
        verb, card = cand[..., 0], cand[..., 1]
        live = np.arange(cand.shape[1])[None, :] < n_cand[:, None]
        has_tr = ((verb == TRAINER) & live).any(1)
        idx = np.nonzero(has_tr)[0]
        probs = []
        with torch.no_grad():                                       # the pilot's probability of playing a Trainer
            for s in range(0, len(idx), 2048):
                ii = idx[s:s + 2048]
                x = [torch.from_numpy(np.ascontiguousarray(b[k].reshape(T, -1)[ii] if k != "obs.nCand" else b[k][ii])).to(device)
                     for k in TOKEN_FIELDS]
                logits, _ = net(*x)
                p = torch.softmax(logits.float(), -1).cpu().numpy()
                probs.append((p * (verb[ii] == TRAINER)).sum(1))
        p_tr = np.concatenate(probs) if probs else np.zeros(0)
        chosen = verb[np.arange(T), b["action"]]
        chosen_card = card[np.arange(T), b["action"]]
        main_phase = (verb == 1).any(1)                              # 'pass' is on offer only in the main phase
        sel = idx[main_phase[idx]]
        instead = Counter(VERBS.get(int(v), str(v)) for v in chosen[sel] if v != TRAINER)
        per_card = {}
        ends = (chosen == 1) | (chosen == 7)                         # pass or attack: the turn ends
        for t in sel:
            for c in set(card[t][(verb[t] == TRAINER) & live[t]].tolist()):
                r = per_card.setdefault(c, [0, 0, 0])
                r[0] += 1
                r[1] += int(chosen[t] == TRAINER and chosen_card[t] == c)
                r[2] += int(ends[t])
        draw_ids = {pool.id[n] for n, _ in DRAW}
        turn_ends = [t for t in np.nonzero(ends)[0]]
        holding = [t for t in turn_ends if draw_ids & set(card[t][(verb[t] == TRAINER) & live[t]].tolist())]
        games = [r for rep in replies for r in rep["results"]]
        out["usage"] = {
            "games": len(games), "decisions": int(T), "with_trainer_playable": int(len(idx)),
            "main_phase_with_trainer": int(len(sel)),
            "trainer_chosen_share": round(float((chosen[sel] == TRAINER).mean()), 4) if len(sel) else None,
            "mean_prob_on_trainers": round(float(p_tr[main_phase[idx]].mean()), 4) if len(p_tr) else None,
            "chosen_instead": dict(instead.most_common()),
            "turn_ends": len(turn_ends),
            "turn_ends_holding_playable_draw_trainer": len(holding),
            "per_card": sorted([{"card": pool.full_name[int(c)], "playable": n, "played": k, "rate": round(k / n, 3),
                                 "turn_ended_while_playable": e}
                                for c, (n, k, e) in per_card.items() if n >= 20], key=lambda r: -r["playable"]),
        }
        if args.out:
            Path(ROOT / args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(ROOT / args.out).write_text(json.dumps(out, indent=1))
        print(json.dumps({k: v for k, v in out["usage"].items() if k != "per_card"}))
        for r in out["usage"]["per_card"][:15]:
            print("  ", r)

        # 2. swap: originals and variants against the other originals, under the pilot
        K = args.swap_decks
        var = [variant(pool, v) for _, v, _ in best[:K]]
        out["swap_added"] = [a for _, a in var]
        panel = [{"name": f"o{i}", "cards": pool.names(v)} for i, (_, v, _) in enumerate(best[:K])] + \
                [{"name": f"v{i}", "cards": pool.names(w)} for i, (w, _) in enumerate(var)]
        pairs = [(i, j) for i in range(K) for j in range(K) if i != j] + [(K + i, j) for i in range(K) for j in range(K) if i != j]
        gm = GpuMatrix.attach(net, rp, args.workers, device=device)
        W, G, _ = gm.play(panel, args.swap_games, args.seed + 1, pairs=pairs)
        P = W / np.maximum(G, 1)
        pil_o = [float(np.mean([P[i, j] for j in range(K) if j != i])) for i in range(K)]
        pil_v = [float(np.mean([P[K + i, j] for j in range(K) if j != i])) for i in range(K)]
        print("pilot, original vs variant:", np.round(pil_o, 3).tolist(), np.round(pil_v, 3).tolist(), flush=True)
    finally:
        rp.close()

    # 2b. the same under SimpleBot on both sides
    sb_o, sb_v = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(K):
            for label, deck, acc in (("o", pool.names(best[i][1]), sb_o), ("v", pool.names(var[i][0]), sb_v)):
                f = Path(tmp) / f"{label}{i}.json"
                opp = [{"name": f"opp{j}", "cards": pool.names(best[j][1])} for j in range(K) if j != i]
                f.write_text(json.dumps([{"name": "target", "cards": deck}] + opp))
                res = Path(tmp) / f"{label}{i}_res.json"
                subprocess.run(["node", str(ROOT / "env/tools/evaluate.js"), "--x", "simplebot", "--y", "simplebot",
                                "--decks-file", str(f), "--d1", "target", "--d2", "opp", "--games", str(args.simplebot_games),
                                "--workers", str(args.workers), "--concurrency", "8", "--seed", str(args.seed + i),
                                "--tokens", "--json", str(res)], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
                r = json.load(open(res))
                acc.append((r["dir1"]["xWinRate"] + 1 - r["dir2"]["xWinRate"]) / 2)   # the target deck's win rate
    d_pilot, d_sb = np.array(pil_v) - np.array(pil_o), np.array(sb_v) - np.array(sb_o)
    out["swap"] = {"pilot": {"original": np.round(pil_o, 4).tolist(), "variant": np.round(pil_v, 4).tolist(),
                             "delta_mean": round(float(d_pilot.mean()), 4), "games_per_pair": args.swap_games},
                   "simplebot": {"original": np.round(sb_o, 4).tolist(), "variant": np.round(sb_v, 4).tolist(),
                                 "delta_mean": round(float(d_sb.mean()), 4), "games_per_deck": args.simplebot_games}}
    print(json.dumps(out["swap"]))
    if args.out:
        Path(ROOT / args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(ROOT / args.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
