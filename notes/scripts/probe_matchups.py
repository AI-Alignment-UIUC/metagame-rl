"""Group-against-group matchups under one pilot (evaluation only, log #127): every deck of --a against every deck
of --b, --games games a pair (seats alternate), greedy, the pilot on both sides. Prints the matrix of A's scores and
each A deck's mean, and writes them with --out. With --pilot-b the B decks are played by that pilot instead (agents
against agents: each population's decks under its own pilot).

  .venv/Scripts/python notes/scripts/probe_matchups.py --pilot runs/lab/main/seg_0450.pt \
      --a runs/probe/a.json --b archived --games 32 --out runs/probe/main_vs_archived.json

--a / --b: a JSON file of [{name, cards}], "archived" (the 24 lists) or "best:<checkpoint>:<k>" (a metagame
checkpoint's k best decks by recent results).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl import limits  # noqa: E402
from rl.decks import Pool, archived_decks  # noqa: E402
from rl.gpu_matrix import GpuMatrix  # noqa: E402
from rl.metagame import recent_score  # noqa: E402
from rl.remote import RemotePool  # noqa: E402
from rl.train import round_score, round_turns  # noqa: E402
from rl.train import token_net  # noqa: E402


def search_spec(text: str, conc: int):
    """--search "K:DETS[:crn]" -> GpuMatrix.play's search dict (maxSteps 40, as #147), or None."""
    if not text:
        return None
    p = text.split(":")
    return {"k": int(p[0]), "dets": int(p[1]), "maxSteps": 40, "concurrency": conc, "crn": len(p) > 2 and p[2] == "crn"}


def group(spec: str, pool: Pool) -> list:
    if spec == "archived":
        return [{"name": n, "cards": pool.names(v)} for n, v in archived_decks(pool)]
    if spec.startswith("best:"):
        path, k = spec[5:].rsplit(":", 1)
        st = torch.load(ROOT / path, map_location="cpu", weights_only=False)

        def score(a):                                  # the judged score with --judge-search (log #148)
            return recent_score(a, 0.0)
        best = sorted(st["population"], key=lambda a: -score(a))[:int(k)]
        return [{"name": f"pop{a['id']}", "cards": a["deck"]} for a in best]
    return json.load(open(ROOT / spec, encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--pilot-b", default="", help="pilot for the B decks (default: --pilot for both)")
    ap.add_argument("--games", type=int, default=32)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--sample", action="store_true", help="sample the pilot's moves instead of greedy")
    ap.add_argument("--round-turns", default="0",
                    help='the 2000 round rule in every game, "T" or "A-B" (log #160); adds "sts", the A decks share of the '
                         'event points with equal weight per B deck')
    ap.add_argument("--search", default="",
                    help='both seats searched on the GPU (C03, log #162): "K:DETS" or "K:DETS:crn" (env/agents.js PolicySearchAgent)')
    ap.add_argument("--search-conc", type=int, default=16, help="searched games at once per worker")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args.workers = limits.cap_workers(args.workers)
    limits.apply(device, args.workers)
    pool = Pool()
    A, B = group(args.a, pool), group(args.b, pool)
    decks = A + B
    rp = RemotePool(args.workers)
    rp.pace = 0.25
    info = rp.ask_all([{"cmd": "info"}] * args.workers)[0]

    def load(path):
        st = torch.load(ROOT / path, map_location=device, weights_only=False)
        net = token_net(st["config"], info).to(device)
        net.load_state_dict(st["model"] if "model" in st else st["net"])
        return net.eval()
    net = load(args.pilot)
    models = {0: net, 1: load(args.pilot_b)} if args.pilot_b else None
    try:
        gm = GpuMatrix.attach(net, rp, args.workers, device=device)
        gm.greedy = not args.sample
        pairs = [(i, len(A) + j) for i in range(len(A)) for j in range(len(B))]
        W, G, _ = gm.play(decks, args.games, args.seed, pairs=pairs, models=models,
                          slots=[0] * len(A) + [1] * len(B) if models else None, round_turns=round_turns(args.round_turns),
                          search=search_spec(args.search, args.search_conc))
    finally:
        rp.close()
    P = (W / np.maximum(G, 1))[:len(A), len(A):]
    by_side = {}                                         # ending -> [A's wins, B's wins, undecided] (log #137)
    for r in gm.results:
        if r.get("ending"):
            k = 0 if r["winner"] == r["iSeat"] else 1 if r["winner"] in (1, 2) else 2
            by_side.setdefault(r["ending"], [0, 0, 0])[k] += 1
    out = {"pilot": args.pilot, "pilot_b": args.pilot_b or args.pilot, "games": args.games,
           "a": [d["name"] for d in A], "b": [d["name"] for d in B],
           "P": np.round(P, 4).tolist(), "a_mean": np.round(P.mean(1), 4).tolist(), "mean": round(float(P.mean()), 4),
           **gm.last, "endings_by_winner": by_side}
    if round_turns(args.round_turns):                    # the event's points: A's share per B deck, then the mean
        pts = np.zeros((len(B), 2))
        for r in gm.results:
            a = round_score(r, r["iSeat"], True) * 3
            b = round_score(r, 3 - r["iSeat"], True) * 3
            pts[r["j"] - len(A)] += (a, b)
        out["sts"] = round(float(np.mean(pts[:, 0] / np.maximum(pts.sum(1), 1e-9))), 4)
        out["round_turns"] = args.round_turns
        print("STS share", out["sts"])
    for name, row in zip(out["a"], P):
        print(f"{name[:40]:40s} {row.mean():.3f}  " + " ".join(f"{x:.2f}" for x in row))
    print("mean", out["mean"], gm.last)
    print("endings [A wins, B wins, undecided]:", by_side)
    if args.out:
        Path(ROOT / args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(ROOT / args.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
