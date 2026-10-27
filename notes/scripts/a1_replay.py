"""A1 replay (log #272; the research session's round 1): does a trained pilot pick better answers on A1's stored prompts?

A1 (#267) stored 488 decisions from the start pilot's self-play with every answer's Q-hat (32 rollouts to the game's
end). This reruns a trained pilot on the same stored rows (no games) and compares its greedy answer's Q-hat with the
start pilot's: dG = mean over decisions of Q-hat(trained greedy) - Q-hat(start greedy), SE over decisions; also the
within-decision Spearman of the trained logits with Q-hat. Valid for pilots that read the same observation (the chain
head reads rows A1's chain-0 observations lack, so a chain pilot's dG is reported as not valid). Evaluation only.

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/a1_replay.py --pilot <trained pilot.pt> --out <json>
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_target_signal import offline, prepare, spearman, zpool   # noqa: E402
from rl.gpu_matrix import load_policy                                 # noqa: E402

NAMED = ("Computer Search", "Super Energy Removal", "Energy Removal", "Energy Retrieval", "Gust of Wind")


def greedy_q(model, probes, device):
    """Per decision: (Q-hat of the pilot's greedy answer among the branched ones, its logits over them)."""
    ps = [dict(p) for p in probes]
    offline(model, ps, device)
    out = []
    for p in ps:
        d = prepare(p)
        lg = np.array([p["logit"][a] for a in p["answers"]])
        out.append((float(d["Q"][int(np.argmax(lg))]), lg, d["Q"]))
    return out


def group(rows, keep):
    g = [r for r, k in zip(rows, keep) if k]
    if not g:
        return {"n": 0}
    dg = np.array([x["dG"] for x in g])
    se = float(dg.std(ddof=1) / np.sqrt(len(dg))) if len(dg) > 1 else float("nan")
    rho = zpool([spearman(x["lg"], x["Q"]) if len(x["Q"]) >= 3 else None for x in g])
    call = ("moved" if dg.mean() >= 0.009 and dg.mean() > 2 * se else "null" if abs(dg.mean()) < 0.005 else "between")
    return {"n": len(g), "dG": round(float(dg.mean()), 4), "se": round(se, 4), "rho_logit_Q": rho, "call": call}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--start", default="ar/data/start.pt")
    ap.add_argument("--raw", default="runs/probe/A1-targetsignal/a1.json.probes.json.gz")
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    probes = [p for p in json.loads(gzip.open(a.raw, "rt").read())["probes"] if not np.isnan(prepare(dict(p))["Q"]).any()]
    trained, _ = load_policy(a.pilot, a.device)
    if trained.config().get("chain", 0):
        res = {"pilot": a.pilot, "valid": False, "why": "chain pilot: A1's observations have no chain rows"}
    else:
        start, _ = load_policy(a.start, a.device)
        t, s = greedy_q(trained, probes, a.device), greedy_q(start, probes, a.device)
        rows = [{"dG": tq - sq, "lg": tl, "Q": Q, "stratum": p["stratum"]} for (tq, tl, Q), (sq, _, _), p in zip(t, s, probes)]
        st = [r["stratum"] for r in rows]
        res = {"pilot": a.pilot, "valid": True, "decisions": len(rows),
               "named5": group(rows, [x in NAMED for x in st]),
               "prompts_all": group(rows, [x != "main" for x in st]),
               "main": group(rows, [x == "main" for x in st]),
               "by_trainer": {n: group(rows, [x == n for x in st]) for n in NAMED},
               "changed_share": round(float(np.mean([abs(r["dG"]) > 0 for r in rows])), 3)}
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: v for k, v in res.items() if k != "by_trainer"}, default=float))


if __name__ == "__main__":
    main()
