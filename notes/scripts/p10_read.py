"""BENCH-P10's readout (runs/probe/BENCH/P10/record.md): each P10 seed against arm 0 of the same seed, from the game files its
chain writes (arm 0's from C113-C115 and P9's base), with p9_read's readers, ground truth first:
  1. M under iii-b (T 65 / 64) and the cap, event points, and the four focus cards' prices (C113's pairs, 256 games, seeds 91, 2);
  2. Computer Search and Item Finder at 256 games a pair (bench_eval --only 1f; arm 0's eval256-arm-arm0-sN);
  3. play (C115's flow games): Oak or Bill played when held, PlusPower per attack, a full Bench at attack, Energy in hand not
     attached; 4. goldfish medians and untimed mirror pace; 5. C116's value check on Oak (dV, dB; arm 0 s1's C116);
  6. head-to-head against arm 0, KL (policy rows) and entropy, and the forced counts (p10.jsonl).
Then the record's bands. Evaluation only.  PYTHONPATH=. .venv/Scripts/python notes/scripts/p10_read.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p9_read as p9   # noqa: E402

B, P10 = p9.B, p9.B / "P10"
for s in (1, 2):
    p9.SRC[f"p10s{s}"] = {"pace": P10 / "pace" / (f"p10s{s}" + "_P{d}_s{e}.jsonl"), "flow": P10 / "flow" / (f"p10s{s}" + "_P{d}_s91.jsonl"),
                          "c113": P10 / "c113" / (f"p10s{s}" + "_{rule}_s{e}.json")}
LABELS = ["arm0s1", "p10s1", "arm0s2", "p10s2"]


def jread(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else None


def focus256(lab):
    r = jread(B / ("eval256-arm-arm0-s" + lab[-1] if lab.startswith("arm0") else f"eval256-p10-s{lab[-1]}") / "bench_eval.json")
    return r and {c: v["score"] for c, v in r["readout1_focus"]["pooled"].items()}


def c116(lab):
    r = jread(ROOT_C116 if lab == "arm0s1" else P10 / f"c116-s{lab[-1]}-summary.json") if lab != "arm0s2" else None
    if not r:
        return None
    o = r["readouts"]["Oak"]["pooled"]
    return {"states": o["states"], "dV": o["dV"]["mean"], "dV_ci": [o["dV"]["lo"], o["dV"]["hi"]], "dB": o["dB"]["mean"],
            "dB_ci": [o["dB"]["lo"], o["dB"]["hi"]], "sign_agree_dV_dB": o["sign_agree_dV_dB"], "band": o.get("band")}


ROOT_C116 = p9.ROOT / "runs/probe/C116-draw-hold/summary.json"


def train(s):
    f = P10 / f"train_s{s}.log"
    if not f.exists():
        return None
    t = f.read_text(encoding="utf-8", errors="ignore").splitlines()
    it = [l for l in t if l.startswith("it ")]
    grab = lambda k: [float(re.search(rf" {k} ([-\d.]+)", l).group(1)) for l in it]
    forced = [json.loads(l[4:]) for l in t if l.startswith("p10 {")]
    ev = jread(B / f"eval-p10-s{s}" / "bench_eval.json")
    return {"iterations": len(it), "kl": grab("kl"), "entropy": grab("entropy"),
            "forced_per_game": [x["forced_per_game"] for x in forced], "eligible_per_game": [x["eligible_per_game"] for x in forced],
            "p10_gae_last": [l for l in t if l.startswith("p10 forced")][-1:],
            "h2h_vs_arm0": (ev["readout4"].get("mirror_vs_ref_pooled") or {}).get("share") if ev else None}


def bands(res):
    per = {}
    for s in (1, 2):
        p, a = res[f"p10s{s}"], res[f"arm0s{s}"]
        if not (p["flow"] and a["flow"] and p["prices"] and a["prices"]):
            continue
        gp, ga = p["flow"]["goldfish_median_own_turns_to_six"], a["flow"]["goldfish_median_own_turns_to_six"]
        ratio = {l: round(gp[l] / ga[l], 3) if gp[l] and ga[l] else None for l in p9.LISTS}
        per[s] = {"oak_bill": p["flow"]["oak_bill_played_when_held"], "oak_bill_arm0": a["flow"]["oak_bill_played_when_held"],
                  "pluspower": p["flow"]["pluspower_per_attack"], "goldfish_ratio": ratio,
                  "dM_iiib": round(p["prices"]["M_iiib"] - a["prices"]["M_iiib"], 4), "dM_cap": round(p["prices"]["M_cap"] - a["prices"]["M_cap"], 4),
                  "h2h": (res["train"].get(f"s{s}") or {}).get("h2h_vs_arm0")}
    if len(per) < 2:
        return {"per_seed": per, "band": "incomplete"}
    both = lambda f: all(f(v) for v in per.values())
    out = {"per_seed": per,
           "R-uses": both(lambda v: v["oak_bill"] >= 0.25) or both(lambda v: v["pluspower"] >= 0.10),
           "R-pace": both(lambda v: sum(1 for x in v["goldfish_ratio"].values() if x is not None and x <= 0.8) >= 3),
           "R-M": both(lambda v: v["dM_iiib"] >= 0.03),
           "R-not": both(lambda v: abs(v["oak_bill"] - v["oak_bill_arm0"]) <= 0.05
                         and all(x is not None and 0.9 <= x <= 1.1 for x in v["goldfish_ratio"].values())),
           "harm": both(lambda v: v["h2h"] is not None and v["h2h"] < 0.45) or both(lambda v: v["dM_cap"] <= -0.03)}
    out["band"] = ", ".join(k for k in ("R-uses", "R-pace", "R-M", "R-not") if out[k]) or "between"
    return out


if __name__ == "__main__":
    res = {lab: {"prices": p9.prices(lab), "focus256": focus256(lab), "flow": p9.flow(lab), "pace": p9.pace(lab), "c116_oak": c116(lab)}
           for lab in LABELS}
    res["train"] = {f"s{s}": train(s) for s in (1, 2)}
    res["bands"] = bands(res)
    (P10 / "readout.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for lab in LABELS:
        r = res[lab]
        print(lab, json.dumps({"M": r["prices"] and {k: r["prices"][k] for k in ("M_iiib", "M_cap")}, "focus256": r["focus256"],
                               "flow": r["flow"], "pace": r["pace"] and {k: r["pace"][k] for k in ("kos_per_own_turn", "deck_out_share",
                                                                                                    "retreats_per_game")},
                               "c116_oak": r["c116_oak"]}))
    print("train", json.dumps({k: v and {"it": v["iterations"], "h2h": v["h2h_vs_arm0"], "forced_per_game": v["forced_per_game"][-1:]}
                               for k, v in res["train"].items()}))
    print("bands", json.dumps(res["bands"]))
