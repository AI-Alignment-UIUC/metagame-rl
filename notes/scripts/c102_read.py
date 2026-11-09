"""C102's readout (runs/probe/C102-discard-cost/record.md): per pilot and card, S_fetch - G, S_discard - G and S_all - G,
paired by list (64 games a pair, binomial SE), per seed and as the two-seed mean, with S_all's CI; and from the follow-through
logs, what each arm discards (type mix, mean own price from the pilot's pooled readout-1 prices; a basic Energy 0.5).
Evaluation only.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/c102_read.py
"""
import collections
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / "runs" / "probe" / "C102-discard-cost"
B = ROOT / "runs" / "probe" / "BENCH"
PRICES = {"data": B / "eval-start", "arm-arm0-s1": B / "eval-arm0-s1"}


def pair_scores(arm):
    """[(p, se)] per pair from an arm's per_pair (a list of dicts or numbers)."""
    out = []
    for x in arm["per_pair"]:
        p = x["score"] if isinstance(x, dict) else float(x)
        n = x.get("games", 64) if isinstance(x, dict) else 64
        out.append((p, np.sqrt(max(p * (1 - p), 1e-4) / n)))
    return out


def diff(a, b):
    """Mean over lists of a - b and its SE (independent arms, binomial per pair)."""
    d = np.array([x[0] - y[0] for x, y in zip(a, b)])
    se = np.sqrt(sum(x[1] ** 2 + y[1] ** 2 for x, y in zip(a, b))) / len(d)
    return float(d.mean()), float(se)


def discards(log, price):
    kinds, ps = collections.Counter(), []
    for e in log:
        for c in e.get("discards") or []:
            k = "Energy" if c.endswith("Energy") else "Trainer" if c in price else "Pokemon/other"
            kinds[k] += 1
            if k == "Energy":
                ps.append(0.5)
            elif c in price:
                ps.append(price[c])
    n = sum(kinds.values())
    return {"n": n, "mix": {k: round(v / n, 3) for k, v in kinds.most_common()} if n else {},
            "mean_price": round(float(np.mean(ps)), 4) if ps else None}


def main():
    res = {}
    for tag in ("data", "arm-arm0-s1"):
        price = {k: v["score"] for k, v in
                 json.loads((PRICES[tag] / "bench_eval.json").read_text(encoding="utf-8"))["readout1"]["pooled"]["price"].items()}
        for card in ("ComputerSearch", "ItemFinder"):
            seeds, logs = {}, collections.defaultdict(list)
            for e in (91, 2):
                f = {k: C / f"{tag}_{card}_{k}_s{e}.json" for k in ("all", "fetch", "discard")}
                if not all(p.exists() for p in f.values()):
                    continue
                js = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in f.items()}
                g = pair_scores(js["all"]["arms"]["G"])
                arms = {"S_all": js["all"]["arms"]["S"], "S_fetch": js["fetch"]["arms"]["S"], "S_discard": js["discard"]["arms"]["S"]}
                seeds[e] = {"G": float(np.mean([x[0] for x in g])),
                            **{k: dict(zip(("d", "se"), diff(pair_scores(v), g))) for k, v in arms.items()},
                            "S_all_p": float(np.mean([x[0] for x in pair_scores(arms["S_all"])])),
                            "S_all_se": float(np.sqrt(sum(x[1] ** 2 for x in pair_scores(arms["S_all"])))) / len(g)}
                logs["G"] += js["all"]["arms"]["G"]["follow"]["log"]
                for k, v in arms.items():
                    logs[k] += v["follow"]["log"]
            if not seeds:
                continue
            two = {k: {"d": round(float(np.mean([s[k]["d"] for s in seeds.values()])), 4),
                       "se": round(float(np.sqrt(sum(s[k]["se"] ** 2 for s in seeds.values())) / len(seeds)), 4)}
                   for k in ("S_fetch", "S_discard", "S_all")}
            sp = float(np.mean([s["S_all_p"] for s in seeds.values()]))
            sse = float(np.sqrt(sum(s["S_all_se"] ** 2 for s in seeds.values())) / len(seeds))
            row = {"seeds": seeds, "two_seed": two, "G": round(float(np.mean([s["G"] for s in seeds.values()])), 4),
                   "S_all": {"p": round(sp, 4), "ci": [round(sp - 1.96 * sse, 4), round(sp + 1.96 * sse, 4)]},
                   "discards": {k: discards(v, price) for k, v in logs.items()}}
            row["bands"] = {"R-discard": two["S_discard"]["d"] >= 0.03,
                            "fetch-side": two["S_fetch"]["d"] >= 0.03 and two["S_discard"]["d"] < 0.03,
                            "R-intrinsic": sp + 2 * sse < 0.5}
            res[f"{tag}|{card}"] = row
            print(f"{tag:12s} {card:15s} G {row['G']:.3f}  S_all {sp:.3f} {row['S_all']['ci']}  "
                  + "  ".join(f"{k}-G {v['d']:+.3f}±{v['se']:.3f}" for k, v in two.items()) + f"  bands {row['bands']}")
            for k, v in row["discards"].items():
                print(f"    discards {k:9s} n {v['n']:4d}  mean price {v['mean_price']}  mix {v['mix']}")
    (C / "readout.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
