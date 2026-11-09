"""C133 (runs/probe/C133-scripted-rank/record.md): where arm 0 s1's policy ranks C115b's scripted fast line's moves. Reads
shadow_s<seed>.jsonl (one line a scripted main-phase decision with 2+ options: the scripted move's rank under the policy, its
probability, the policy's top-1, V) and pilot_s<seed>.jsonl (arm 0's own greedy games on the same deals). Readouts: top-1, top-3
and outside-top-3 shares and mean probability, overall and by kind; V at the first logged decision of own turns 2, 4 and 6, the
scripted line against arm 0's own games; the check that the shadowed games equal C115b's (own turns to six, ending, winner, per
seed). Then the record's bands. Writes summary.json.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c133_read.py [--seed 91]
"""
import argparse
import collections
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C133-scripted-rank"
r3 = lambda x: None if x is None else round(x, 3)


def shares(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    top1 = sum(1 for x in rows if x["rank"] == 1)
    top3 = sum(1 for x in rows if x["rank"] is not None and x["rank"] <= 3)
    ps = [x["p"] for x in rows if x["p"] is not None]
    return {"n": n, "top1": r3(top1 / n), "top3": r3(top3 / n), "outside_top3": r3(1 - top3 / n),
            "mean_p": r3(sum(ps) / len(ps)) if ps else None, "mean_legal": r3(sum(x["n"] for x in rows) / n)}


def v_at(rows, turns=(2, 4, 6)):
    first = {}
    for x in rows:                                   # the first logged decision of each (game, own turn)
        first.setdefault((x["seed"], x["own"]), x["v"])
    out = {}
    for t in turns:
        vs = [v for (s, o), v in first.items() if o == t]
        out[t] = {"n": len(vs), "mean_v": r3(statistics.mean(vs)) if vs else None,
                  "se": r3(statistics.stdev(vs) / len(vs) ** 0.5) if len(vs) > 1 else None}
    return out


def six(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        g = json.loads(line)
        at = 1 if g["seed"] % 2 == 0 else 2           # the attacker: seat 1 on an even seed (wiggly_worker.js, c133_worker.js)
        cum, s = 0, None
        for n, t in enumerate([t for t in g["turns"] if t["p"] == at], 1):
            cum += t["prizes"]
            if s is None and cum >= 6:
                s = n
        out[g["seed"]] = [s, g["ending"], g["winner"] == at]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=91)
    a = ap.parse_args()
    sh = [json.loads(l) for l in (OUT / f"shadow_s{a.seed}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    pi = [json.loads(l) for l in (OUT / f"pilot_s{a.seed}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    kinds = collections.defaultdict(list)
    for x in sh:
        kinds[x["kind"]].append(x)
    overall = shares(sh)
    by_kind = {k: shares(v) for k, v in sorted(kinds.items(), key=lambda kv: -len(kv[1]))}
    mine, ref = six(OUT / f"shadow_s{a.seed}.trace.jsonl"), six(ROOT / f"runs/probe/C115-goldfish/c115b/wiggly_s{a.seed}.jsonl")
    same = sum(1 for s in mine if ref.get(s) == mine[s])
    if overall["outside_top3"] >= 0.25:
        band = "R-candidates"
    elif overall["outside_top3"] <= 0.10 and overall["top1"] < 0.60:
        band = "R-coordination"
    else:
        band = "between"
    res = {"overall": overall, "by_kind": by_kind, "v_scripted": v_at(sh), "v_pilot": v_at(pi),
           "check_vs_c115b": {"games": len(mine), "identical": same}, "pilot_rank1_share": shares(pi).get("top1"), "band": band}
    (OUT / "summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("overall", overall)
    for k, v in by_kind.items():
        print(f"  {k:24s}", v)
    print("V scripted", res["v_scripted"])
    print("V pilot   ", res["v_pilot"])
    print("check vs C115b", res["check_vs_c115b"], "| pilot rank-1 share", res["pilot_rank1_share"], "| band", band)


if __name__ == "__main__":
    main()
