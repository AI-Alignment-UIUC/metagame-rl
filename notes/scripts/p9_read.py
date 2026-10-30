"""BENCH-P9's readout (runs/probe/BENCH/P9/record.md): each training seed's P9 pilot against arm 0 of the same seed, read from the
game files its chain writes (arm 0 s1's are C113's, C114's and C115's own), ground truth first:
  1. M under the real-STS stand-in (C113's iii-b: T 65 at eval seed 91, T 64 at seed 2) and under the cap, both in event points;
  2. pace in the P-list mirrors, untimed (C114's games, eval seeds 91 and 2 pooled): knockouts per own turn, own turns to the first
     payable attack, the payable share, endings, the deck-out share, retreats a game, and the 80th percentile of game turns;
  3. the goldfish (C115's flow games, seed 91): per list, the median own turns to six Prizes (wins by Prizes only, as C115);
     Oak or Bill played when held, PlusPower per attack, a full Bench (5) at attack;
  4. the four focus cards' prices (event points, cap and iii-b); head-to-head against arm 0; KL, entropy and the p9 lines.
Then the record's bands. Evaluation only.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/p9_read.py
"""
import collections
import json
import re
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from c113_read import FOCUS, read as c113   # noqa: E402

B, P9 = ROOT / "runs/probe/BENCH", ROOT / "runs/probe/BENCH/P9"
T_OF = {91: 65, 2: 64}                      # arm 0 s1's untimed 80th percentiles (C113), the same clock for every pilot
SRC = {"arm0s1": {"pace": ROOT / "runs/probe/C114-pace/arm0_P{d}_s{e}.jsonl", "flow": ROOT / "runs/probe/C115-goldfish/flow/arm0_P{d}_s91.jsonl",
                  "c113": ROOT / "runs/probe/C113-end-rule/arm0s1_{rule}_s{e}.json"}}
for lab in ("p9s1", "p9s2", "arm0s2"):
    SRC[lab] = {"pace": P9 / "pace" / (lab + "_P{d}_s{e}.jsonl"), "flow": P9 / "flow" / (lab + "_P{d}_s91.jsonl"),
                "c113": P9 / "c113" / (lab + "_{rule}_s{e}.json")}
LISTS = ["list 3", "list 1", "list 21", "list 2"]


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()] if Path(p).exists() else None


def pace(lab):
    games = []
    for e in (91, 2):
        for d in range(4):
            g = jl(str(SRC[lab]["pace"]).format(d=d, e=e))
            if g is None:
                return None
            games += g
    turns = [t for g in games for t in g["turns"]]
    first = []
    for g in games:
        for p in (1, 2):
            i = next((i for i, t in enumerate((t for t in g["turns"] if t["p"] == p), 1) if t["payE"]), None)
            first.append(i)
    got, known = [f for f in first if f is not None], [t for t in turns if t["payE"] is not None]
    end = collections.Counter(g["ending"] or "none" for g in games)
    return {"games": len(games), "errors": sum(1 for g in games if g["error"]), "kos_per_own_turn": round(sum(t["kos"] for t in turns) / len(turns), 4),
            "median_own_turns_to_first_payable_attack": statistics.median(got) if got else None,
            "payable_share_end_of_turn": round(sum(1 for t in known if t["payE"]) / len(known), 3), "endings": dict(end),
            "deck_out_share": round(end.get("deck-out", 0) / len(games), 3), "retreats_per_game": round(sum(t["retreat"] for t in turns) / len(games), 2),
            "game_turns_p80": float(np.percentile([g["turn"] for g in games], 80)), "game_turns_mean": round(float(np.mean([g["turn"] for g in games])), 1)}


def flow(lab):
    six, ob, obp, att, pp, full, eh, ehn = {}, 0, 0, 0, 0, 0, 0, 0
    for d in range(4):
        games = jl(str(SRC[lab]["flow"]).format(d=d))
        if games is None:
            return None
        s = []
        for g in games:
            at = 3 - (2 if g["seed"] % 2 == 0 else 1)
            mine = [t for t in g["turns"] if t["p"] == at]
            if g["ending"] == "prizes" and g["winner"] == at:
                s.append(len(mine))
            for t in mine:
                ob += t["ob"] > 0
                eh += t["eH"] > 0
                ehn += t["eH"] > 0 and t["att"] == 0
                obp += t["ob"] > 0 and t["obp"] > 0
                if t["A"]:
                    att += 1
                    pp += t["ppP"]
                    full += t["A"][0]["bA"] == 5
        six[LISTS[d]] = statistics.median(s) if s else None
    return {"goldfish_median_own_turns_to_six": six, "oak_bill_played_when_held": round(obp / max(ob, 1), 3),
            "pluspower_per_attack": round(pp / max(att, 1), 4), "full_bench_at_attack": round(full / max(att, 1), 3),
            "energy_in_hand_not_attached": round(ehn / max(eh, 1), 3)}


def prices(lab):
    out = {}
    for rule in ("cap", "T"):                 # event points under both rules, as the record's arm-0 figures (cap 0.492 / 0.510)
        metric = "points"
        reads = []
        for e in (91, 2):
            f = Path(str(SRC[lab]["c113"]).format(rule="cap" if rule == "cap" else f"T{T_OF[e]}", e=e))
            if not f.exists():
                return None
            reads.append(c113(str(f)))
        key = "cap" if rule == "cap" else "iiib"
        out[f"M_{key}"] = round(float(np.mean([r[f"M_{metric}"] for r in reads])), 4)
        out[f"M_{key}_by_eval_seed"] = [r[f"M_{metric}"] for r in reads]
        out[f"M_{key}_share"] = round(float(np.mean([r["M_share"] for r in reads])), 4)
        out[f"cards_{key}"] = {c: round(float(np.mean([r[f"cards_{metric}"][c]["pooled"] for r in reads])), 4) for c in FOCUS}
        out[f"time_share_{key}"] = [r["time_share"] for r in reads]
    return out


def train(s):
    f = P9 / f"train_s{s}.log"
    if not f.exists():
        return None
    it = [l for l in f.read_text(encoding="utf-8", errors="ignore").splitlines() if l.startswith("it ")]
    p9 = [l for l in f.read_text(encoding="utf-8", errors="ignore").splitlines() if l.startswith("p9 ")]
    grab = lambda k: [float(re.search(rf" {k} ([-\d.]+)", l).group(1)) for l in it]
    ev = B / f"eval-p9-s{s}" / "bench_eval.json"
    return {"iterations": len(it), "kl": grab("kl"), "entropy": grab("entropy"), "p9_first": p9[:1], "p9_last": p9[-1:],
            "h2h_vs_arm0": (json.loads(ev.read_text(encoding="utf-8"))["readout4"].get("mirror_vs_ref_pooled") or {}).get("share") if ev.exists() else None}


def bands(res):
    per = {}
    for s in (1, 2):
        p, a = res.get(f"p9s{s}"), res.get(f"arm0s{s}")
        if not p or not a or not p["pace"] or not a["pace"]:
            continue
        ko = p["pace"]["kos_per_own_turn"] / a["pace"]["kos_per_own_turn"]
        gf = sum(1 for l in LISTS if p["flow"] and a["flow"] and p["flow"]["goldfish_median_own_turns_to_six"][l] is not None
                 and p["flow"]["goldfish_median_own_turns_to_six"][l] <= 0.8 * a["flow"]["goldfish_median_own_turns_to_six"][l])
        dm = p["prices"]["M_iiib"] - a["prices"]["M_iiib"] if p["prices"] and a["prices"] else None
        dc = p["prices"]["M_cap"] - a["prices"]["M_cap"] if p["prices"] and a["prices"] else None
        h2h = (res.get("train") or {}).get(f"s{s}", {}) or {}
        per[s] = {"ko_ratio": round(ko, 3), "goldfish_lists_le_0.8x": gf, "dM_iiib": None if dm is None else round(dm, 4),
                  "dM_cap": None if dc is None else round(dc, 4), "h2h": h2h.get("h2h_vs_arm0")}
    if len(per) < 2:
        return {"per_seed": per, "band": "incomplete"}
    both = lambda f: all(f(v) for v in per.values())
    out = {"per_seed": per,
           "R-faster": both(lambda v: v["ko_ratio"] >= 1.2) or both(lambda v: v["goldfish_lists_le_0.8x"] >= 3),
           "R-M": both(lambda v: v["dM_iiib"] is not None and v["dM_iiib"] >= 0.03),
           "R-not": both(lambda v: 1 / 1.1 <= v["ko_ratio"] <= 1.1),
           "harm": both(lambda v: v["h2h"] is not None and v["h2h"] < 0.45) or both(lambda v: v["dM_cap"] is not None and v["dM_cap"] <= -0.03)}
    out["band"] = ", ".join(k for k in ("R-faster", "R-M", "R-not") if out[k]) or "between"
    return out


if __name__ == "__main__":
    res = {lab: {"pace": pace(lab), "flow": flow(lab), "prices": prices(lab)} for lab in SRC}
    res["train"] = {f"s{s}": train(s) for s in (1, 2)}
    res["bands"] = bands(res)
    (P9 / "readout.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for lab in SRC:
        r = res[lab]
        print(lab, json.dumps({"M": r["prices"] and {k: r["prices"][k] for k in ("M_iiib", "M_cap")}, "pace": r["pace"] and
                               {k: r["pace"][k] for k in ("kos_per_own_turn", "deck_out_share", "retreats_per_game", "game_turns_p80")},
                               "flow": r["flow"]}))
    print("train", json.dumps({k: v and {"it": v["iterations"], "h2h": v["h2h_vs_arm0"], "p9": v["p9_last"]} for k, v in res["train"].items()}))
    print("bands", json.dumps(res["bands"]))
