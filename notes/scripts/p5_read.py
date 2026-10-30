"""BENCH-P5c/P5d readout (P5's record): for an eval folder holding price_s91.json and price_s2.json (probe_prompt_oracle G, PlusPower,
256 games a pair, --timing-card PlusPower) and bench_eval.json (readout 4 against arm 0), with the arm's train log:
  PlusPower's same-pilot price per list and pooled (raw wins, draws half, from per_pair x 256); conversions caught a game; attach
  shares at hits by class (conversion / no-KO / KO anyway, engine damage); head-to-head against arm 0; KL and kl-stop's cut share.
Evaluation only.  PYTHONPATH=. .venv/Scripts/python notes/scripts/p5_read.py <eval folder> <train log> [<train log> ...]
"""
import json
import re
import sys
from pathlib import Path

import numpy as np


def read(ev, logs):
    ev = Path(ev)
    wins, per, conv, games = 0.0, [], 0, 0
    cnt = {"conv": [0, 0], "noko": [0, 0], "ko": [0, 0]}
    for e in (91, 2):
        a = json.loads((ev / f"price_s{e}.json").read_text(encoding="utf-8"))["arms"]["G"]
        w = [round(p * 256 * 2) / 2 for p in a["per_pair"]]
        per.append(a["per_pair"]); wins += sum(w)
        conv += a["follow"]["conversions"]["conversions"]; games += a["last"]["games"]
        for h in a["follow"].get("pp_log", []):
            if h.get("left") is None or h.get("base") is None or not ((h.get("plus") or 0) > 0 or (h.get("inHand") or 0) > 0):
                continue
            b, l = h["base"], h["left"]
            k = "ko" if b >= l else "conv" if b + 10 >= l else "noko"
            cnt[k][0] += 1
            cnt[k][1] += int((h.get("plus") or 0) > 0)
    m = np.array(per).mean(0)
    pooled = wins / (len(m) * 512)
    se = float(np.sqrt((np.maximum(m * (1 - m), 1e-4) / 512).sum()) / len(m))
    r4 = json.loads((ev / "bench_eval.json").read_text(encoding="utf-8"))["readout4"] if (ev / "bench_eval.json").exists() else {}
    kl, took, tot = [], 0, 0
    for lg in logs:
        for line in open(lg, encoding="utf-8", errors="ignore"):
            if line.startswith("it "):
                kl.append(float(re.search(r" kl ([-\d.]+)", line).group(1)))
            elif line.startswith("kl-stop:"):
                x = line.split()
                took += int(x[1]); tot += int(x[4].rstrip(","))
    return {"price_per_list": m.round(4).tolist(), "price_pooled": round(pooled, 5), "pooled_se": round(se, 4), "wins": wins,
            "caught_a_game": round(conv / games, 4), "caught": conv, "games": games,
            "attach": {k: round(p / n, 3) if n else None for k, (n, p) in cnt.items()}, "attach_n": {k: n for k, (n, p) in cnt.items()},
            "h2h_vs_arm0": r4.get("mirror_vs_ref_pooled"), "kl": kl, "minibatches_taken": f"{took}/{tot}",
            "cut_share": round(1 - took / tot, 3) if tot else None}


if __name__ == "__main__":
    res = read(sys.argv[1], sys.argv[2:])
    (Path(sys.argv[1]) / "p5_read.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))
