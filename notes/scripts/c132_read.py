"""C132 (runs/probe/C132-goldfish-search/record.md): the goldfish under the pilot's own search, read per arm (G, SV, SP) and list.
C115's per-game summary (notes/scripts/audit/summarize_goldfish.py: own turns to six Prizes among the games that reach it, with
the IQR and share, own turns to the first knockout, knockouts per own turn, endings, the payable-attack share, Energy attached a
turn), plus PlusPower on the Active per attack and the share of attacks with a full Bench (5). Then the record's bands on the
median own turns to six Prizes: a list with no game reaching six counts as 16 or more, as in C115. Writes summary.json.
C132b adds arms SPh3 and SPh5 (SP at horizon 3 and 5, the goldfish inside lines), their bands, and two readouts: Oak or Bill
played on own turns that start with one in hand, and the share of own turns that start with Energy in hand.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c132_read.py [--seed 91] [--tag ""]
"""
import argparse
import collections
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C132-goldfish-search"
LISTS = {0: "list 3", 1: "list 1", 2: "list 21", 3: "list 2"}
ARMS = ["G", "SV", "SP", "SPh3", "SPh5"]
r = lambda x, k=2: None if x is None else round(x, k)


def q(x):
    if len(x) < 2:
        return [x[0]] * 3 if x else [None] * 3
    return [r(v, 1) for v in statistics.quantiles(x, n=4, method="inclusive")]


def summarize(games):
    six, first, rows, attacks = [], [], [], []
    for g in games:
        at = 3 - (2 if g["seed"] % 2 == 0 else 1)          # the Goldfish is seat 2 on an even seed (goldfish_worker3.js)
        mine = [t for t in g["turns"] if t["p"] == at]
        rows += mine
        attacks += [a for t in mine for a in t.get("A", [])]
        if g["ending"] == "prizes" and g["winner"] == at:
            six.append(len(mine))
        i = next((i for i, t in enumerate(mine, 1) if t["kos"]), None)
        if i:
            first.append(i)
    n, nt = len(games), len(rows)
    pay = [t for t in rows if t["payE"] is not None]
    return {"games": n, "errors": sum(1 for g in games if g["error"]), "attacker_own_turns": nt,
            "six_share": r(len(six) / n, 3) if n else None, "six_games": len(six),
            "median_to_six": statistics.median(six) if six else None, "iqr_to_six": q(six),
            "median_to_first_ko": statistics.median(first) if first else None, "first_ko_games": len(first),
            "kos_per_own_turn": r(sum(t["kos"] for t in rows) / nt, 3) if nt else None,
            "endings": dict(collections.Counter(g["ending"] for g in games)),
            "payable_attack_share": r(sum(1 for t in pay if t["payE"]) / len(pay), 3) if pay else None,
            "energy_per_own_turn": r(sum(t["att"] for t in rows) / nt, 3) if nt else None,
            "attacks": len(attacks), "pluspower_per_attack": r(sum(a["pp"] for a in attacks) / len(attacks), 3) if attacks else None,
            "full_bench_at_attack": r(sum(1 for a in attacks if a["bA"] >= 5) / len(attacks), 3) if attacks else None,
            "ob_played_when_held": r(sum(1 for t in rows if t["ob"] and t["obp"]) / max(1, sum(1 for t in rows if t["ob"])), 3),
            "energy_in_hand_turns": r(sum(1 for t in rows if t["eH"]) / nt, 3) if nt else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    out = {}
    for arm in ARMS:
        out[arm] = {}
        for di, name in LISTS.items():
            f = OUT / f"{arm}_P{di}_s{a.seed}{a.tag}.jsonl"
            if f.exists():
                out[arm][name] = summarize([json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()])
    med = {arm: [v["median_to_six"] for v in out[arm].values()] for arm in ARMS}
    le = lambda m, x: sum(1 for v in m if v is not None and v <= x)
    ge = lambda m, x: sum(1 for v in m if v is None or v >= x)
    sv, sp = med["SV"], med["SP"]
    if len(sv) == 4 and le(sv, 12) >= 3:
        band = "R-learnable"
    elif len(sv) == 4 and len(sp) == 4 and ge(sv, 16) >= 3 and le(sp, 12) >= 3:
        band = "R-value-limited"
    elif len(sp) == 4 and ge(sp, 16) >= 3:
        band = "R-reach"
    else:
        band = "between" if len(sv) == 4 and len(sp) == 4 else "incomplete"
    out["bands"] = {"medians": med, "SV_le_12": le(sv, 12), "SV_ge_16": ge(sv, 16), "SP_le_12": le(sp, 12), "SP_ge_16": ge(sp, 16), "band": band}
    h3, h5 = med["SPh3"], med["SPh5"]                  # C132b's bands
    if len(h3) == 4 and len(h5) == 4:
        b2 = ("R-horizon" if le(h3, 12) >= 3 or le(h5, 12) >= 3 else "R-not-horizon" if ge(h5, 16) >= 3 else "between")
    else:
        b2 = "incomplete"
    out["bands_b"] = {"h3_le_12": le(h3, 12), "h5_le_12": le(h5, 12), "h5_ge_16": ge(h5, 16), "band": b2}
    (OUT / f"summary{a.tag}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for arm in ARMS:
        for name, v in out[arm].items():
            print(arm, name, "| n", v["games"], "err", v["errors"], "six", v["six_share"], "med", v["median_to_six"], v["iqr_to_six"],
                  "| 1stKO", v["median_to_first_ko"], "ko/t", v["kos_per_own_turn"], "| pay", v["payable_attack_share"],
                  "en/t", v["energy_per_own_turn"], "PP/atk", v["pluspower_per_attack"], "fullB", v["full_bench_at_attack"],
                  "OB|held", v["ob_played_when_held"], "Ehand", v["energy_in_hand_turns"], "|", v["endings"])
    print(out["bands"])
    print(out["bands_b"])


if __name__ == "__main__":
    main()
