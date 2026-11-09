"""C105's readout (runs/probe/C105-target-margin/record.md): per pilot and added card, the price q of one extra copy (the
variant's share against its list, 1 - the list's per-pair score), per list and pooled over lists and seeds (binomial SE,
64 games a pair), beside each list's Computer Search price at 256 games under the same pilot (bench_ctx); the record's
bands; and the verdict that gates C104 (arm 0 s1's extra Energy Removal: not-capped if q - 2 SE >= 0.55). Evaluation only.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/c105_read.py
"""
import collections
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / "runs" / "probe" / "C105-target-margin"
B = ROOT / "runs" / "probe" / "BENCH"
CTX = {"ar/data/start.pt": B / "ctx-start" / "ctx.json", "runs/probe/BENCH/arm-arm0-s1/pilot.pt": B / "ctx-arm0-s1" / "ctx.json"}


def main():
    decks = json.loads((B / "decks_P.json").read_text(encoding="utf-8"))
    rows = collections.defaultdict(lambda: collections.defaultdict(list))      # (pilot, group) -> list -> [q]
    for f in sorted(C.glob("tv_s*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        for pl, v in j["players"].items():
            for p, s in zip(j["pairs"], v["per_pair"]):
                rows[(pl, p["group"])][decks[p["base"]]["name"]].append(1 - s)
    res = {}
    for (pl, g), per in rows.items():
        cs = {}
        if CTX.get(pl) and CTX[pl].exists():
            cs = {r["list"]: r["price"] for r in json.loads(CTX[pl].read_text(encoding="utf-8"))["cards"]["Computer Search"]}
        qs = [q for v in per.values() for q in v]
        q = float(np.mean(qs))
        se = float(np.sqrt(sum(max(x * (1 - x), 1e-4) / 64 for x in qs)) / len(qs))
        band = "R-capped" if q - 2 * se < 0.53 else "R-not-capped" if q - 2 * se >= 0.55 else "between"
        res[f"{pl}|{g}"] = {"q": round(q, 4), "se": round(se, 4), "band": band, "n_pairs": len(qs),
                            "per_list": {n: {"q": round(float(np.mean(v)), 4), "computer_search_256": cs.get(n)} for n, v in per.items()}}
        print(f"{pl[-28:]:28s} {g:22s} q {q:.3f} ± {se:.3f}  {band:12s}  "
              + "  ".join(f"{n[:18]}: q {x['q']:.3f} CS {x['computer_search_256']}" for n, x in res[f'{pl}|{g}']['per_list'].items()))
    gate = res.get("runs/probe/BENCH/arm-arm0-s1/pilot.pt|plus:Energy Removal", {})
    res["c104_gate"] = {"basis": "arm 0 s1, extra Energy Removal", "band": gate.get("band"), "run_c104": gate.get("band") == "R-not-capped"}
    print("C104 gate:", res["c104_gate"])
    (C / "readout.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
