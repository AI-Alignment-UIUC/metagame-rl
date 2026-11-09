"""BENCH Amendment 6: Item Finder and Computer Search per (card, list), never pooled, and their play context. For one pilot,
each P list that runs the card: probe_prompt_oracle's G arm on that list alone (the card turned into Energy against the list,
256 games a pair, the round rule, seed 91) with the follow-through log on (--timing-card). That gives the card's price in the
list and every play's target (Computer Search: the fetched card; Item Finder: the Trainer it recovers) and its two discards.
Each target is joined to its own price in the same list under the same pilot (bench_eval readout 1, --prices). Evaluation only.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/bench_ctx.py --pilot runs/probe/BENCH/arm-p2-s2/pilot.pt \
      --prices runs/probe/BENCH/eval-p2-s2 --out runs/probe/BENCH/eval-p2-s2/ctx.json
"""
import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import Pool  # noqa: E402

BENCH = ROOT / "runs" / "probe" / "BENCH"
CARDS = ("Item Finder", "Computer Search")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--prices", help="the pilot's bench_eval folder (readout 1's per-list prices, for the targets)")
    ap.add_argument("--games", type=int, default=256)
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pool = Pool()
    short = {c["fullName"]: c["name"] for c in pool.cards}
    kind = {c["name"]: {1: "Pokemon", 2: "Trainer", 3: "Energy"}[c["superType"]] for c in pool.cards}
    lists = json.loads((BENCH / "decks.json").read_text(encoding="utf-8"))["P"]
    per_list_price = {}
    if a.prices:
        r1 = json.loads((ROOT / a.prices / "bench_eval.json").read_text(encoding="utf-8"))["readout1"]
        per_list_price = {x["name"]: x["price"] for x in r1["per_list"]}
    out_dir = (ROOT / a.out).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {"pilot": a.pilot, "games": a.games, "seed": a.seed, "cards": {}}
    for card in CARDS:
        rows = []
        for k, d in enumerate(lists):
            if card not in d["trainer_kinds"]:
                continue
            o = out_dir / f"ctx_{card.replace(' ', '')}_P{k}_s{a.seed}.json"
            subprocess.run([sys.executable, "notes/scripts/probe_prompt_oracle.py", "--pilot", a.pilot, "--arms", "G",
                            "--timing-card", card, "--groups", card, "--decks", str(BENCH / f"decks_P{k}.json"),
                            "--games", str(a.games), "--workers", str(a.workers), "--round-turns", "20-45", "--seed", str(a.seed),
                            "--out", str(o)], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
            js = json.loads(o.read_text(encoding="utf-8"))
            rt, fo = js["readout"]["timing"], js["arms"]["G"]["follow"]
            p = rt["price"]["G"][card]["score"]
            se = float(np.sqrt(p * (1 - p) / a.games))
            log = fo["log"]
            prices = per_list_price.get(d["name"], {})
            tgt = [e["fetched"] for e in log if e.get("fetched")]
            tp = [prices[short.get(t, t)] for t in tgt if short.get(t, t) in prices]
            # C102: the discards' types and own prices. A Trainer is priced by the list's readout 1, a basic Energy 0.5 (the
            # reference card), a Pokemon not at all; net vs Energy = (p_target - 0.5) - sum over the discards of (p_d - 0.5).
            def own(n):
                n = short.get(n, n)
                return 0.5 if kind.get(n) == "Energy" else prices.get(n) if kind.get(n) == "Trainer" else None
            dis = [x for e in log for x in (e.get("discards") or [])]
            dp = [own(x) for x in dis if own(x) is not None]
            net = []
            for e in log:
                ps = [own(e["fetched"])] + [own(x) for x in e.get("discards") or []] if e.get("fetched") else [None]
                if len(ps) == 3 and None not in ps:
                    net.append((ps[0] - 0.5) - sum(q - 0.5 for q in ps[1:]))
            rows.append({
                "list": d["name"], "list_index": d["list_index"], "copies": sum(1 for c in d["cards"] if short.get(c) == card),
                "price": round(p, 4), "se": round(se, 4), "ci": [round(p - 1.96 * se, 4), round(p + 1.96 * se, 4)],
                "status": "clearly above" if p - 2 * se >= 0.5 else "meets" if p + 2 * se >= 0.5 else "misses",
                "plays": len(log),
                "targets": collections.Counter(short.get(t, t) for t in tgt).most_common(),
                "target_types": collections.Counter(e.get("type") for e in log if e.get("fetched")).most_common(),
                "discards": collections.Counter(x for e in log for x in (e.get("discards") or [])).most_common(10),
                "target_mean_price": round(float(np.mean(tp)), 4) if tp else None, "targets_priced": len(tp),
                "same_turn_use": fo["same_turn_use"],
                "discard_types": collections.Counter(kind.get(short.get(x, x)) for x in dis).most_common(),
                "discard_mean_price": round(float(np.mean(dp)), 4) if dp else None, "discards_priced": len(dp),
                "net_vs_energy": {"mean": round(float(np.mean(net)), 4) if net else None,
                                  "se": round(float(np.std(net, ddof=1) / np.sqrt(len(net))), 4) if len(net) > 1 else None,
                                  "plays": len(net), "unpriced": len(log) - len(net)}})
            print(f"{card:16s} {d['name'][:34]:34s} p {p:.3f} [{p - 1.96 * se:.3f}, {p + 1.96 * se:.3f}] {rows[-1]['status']:13s} "
                  f"plays {len(log)}  targets' mean price {rows[-1]['target_mean_price']}  top {rows[-1]['targets'][:4]}", flush=True)
            print(f"{'':16s} discards {rows[-1]['discard_types']} mean price {rows[-1]['discard_mean_price']} "
                  f"({rows[-1]['discards_priced']} priced)  net vs Energy {rows[-1]['net_vs_energy']}", flush=True)
        res["cards"][card] = rows
    (ROOT / a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
