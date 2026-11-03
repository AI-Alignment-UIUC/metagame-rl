"""C134 (runs/probe/C134-breakpoints/record.md): breakpoint readouts per field from notes/scripts/audit/bp_worker.js's attack rows.
Over attacks that deal damage (the engine's base damage > 0 and the Defender's HP left fell or it was knocked out):
  b10  the share that leave the Defending Pokemon at exactly 10 HP by the attack's own damage, max(0, base + 10 x PlusPower - 20 x
       Defender) (one more PlusPower would flip the knockout; a poison tick after the attack isn't counted);
  bG   the share where the Defender wasn't knocked out but some benched opposing Pokemon has HP left at or under d10, this attack's
       damage to it with one more PlusPower (Gust of Wind plus PlusPower flips a knockout);
  also the Defender's HP left at attack, damage dealt, the knockout share and the Weakness-hit share.
Checks (the build's acceptance): the engine's own HP drop on every damaging attack the Defender survived against
max(0, base + 10 x PlusPower - 20 x Defender), base being after Weakness and Resistance as the engine passes it; and Weakness hits against
notes/data/cards/pool.json's type vectors. --hand N prints N damaging attacks for a hand count. Bands as the record. Writes
summary.json.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c134_read.py [--seed 91] [--tag ""] [--hand 20]
"""
import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C134-breakpoints"
POOL = {c["fullName"]: c for c in json.loads((ROOT / "notes/data/cards/pool.json").read_text(encoding="utf-8"))["cards"]}
r3 = lambda x: None if x is None else round(x, 3)


def hit(x):                                          # the attack's own damage, as the engine applies it (the drop check below)
    return max(0, x["base"] + 10 * x["pp"] - 20 * x["df"]) if x["base"] is not None else 0


def damaging(x):
    return x["base"] is not None and x["base"] > 0 and hit(x) > 0 and x["left0"] is not None


def flags(x):                                        # from the attack's own damage, so a poison tick after it doesn't count
    left = x["left0"] - hit(x)
    b10 = left == 10
    bg = left > 0 and any(b["left"] is not None and 0 < b["left"] <= b["d10"] for b in x["bench"])
    return b10, bg


def read(rows):
    d = [x for x in rows if damaging(x)]
    n = len(d)
    if not n:
        return {"attacks": len(rows), "damaging": 0}
    f = [flags(x) for x in d]
    dealt = [min(x["left0"], hit(x)) for x in d]
    return {"attacks": len(rows), "damaging": n, "b10": r3(sum(a for a, _ in f) / n), "bG": r3(sum(b for _, b in f) / n),
            "b10_plus_bG": r3(sum(a or b for a, b in f) / n), "ko_share": r3(sum(x["left0"] - hit(x) <= 0 for x in d) / n),
            "weak_share": r3(sum(x["weak"] for x in d) / n), "mean_left_at_attack": r3(statistics.mean(x["left0"] for x in d)),
            "mean_dealt": r3(statistics.mean(dealt)), "with_bench_share": r3(sum(1 for x in d if x["bench"]) / n)}


def checks(rows):
    drop_ok = drop_n = weak_ok = weak_n = 0
    bad = []
    for x in rows:
        if not damaging(x):
            continue
        if not x["ko"] and x["left1"] is not None:
            exp = max(0, x["base"] + 10 * x["pp"] - 20 * x["df"])   # base is after W and R (bp_worker.js)
            drop_n += 1
            if x["left0"] - x["left1"] == exp:
                drop_ok += 1
            elif len(bad) < 5:
                bad.append({k: x[k] for k in ("ac", "an", "dc", "base", "multA", "modA", "pp", "df", "left0", "left1")})
        a, dc = POOL.get(x["ac"]), POOL.get(x["dc"])
        if a and dc:
            weak_n += 1
            weak_ok += (any(t and w for t, w in zip(a["types"], dc["weakness"])) == x["weak"])
    return {"drop_matches": f"{drop_ok}/{drop_n}", "weak_matches_pool": f"{weak_ok}/{weak_n}", "drop_mismatch_examples": bad}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--tag", default="")
    ap.add_argument("--hand", type=int, default=0)
    a = ap.parse_args()
    res = {}
    for f in ("H", "L", "LH"):
        p = OUT / f"{f}_s{a.seed}{a.tag}.jsonl"
        if p.exists():
            rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
            res[f] = {**read(rows), "checks": checks(rows)}
            if a.hand and f == "H":
                for x in [x for x in rows if damaging(x)][:a.hand]:
                    b10, bg = flags(x)
                    print(f"  {x['ac']}/{x['an']} base {x['base']} raw {x.get('raw')} pp {x['pp']} -> {x['dc']} W{x['multA']}{x['modA']:+d} df {x['df']} "
                          f"left {x['left0']}->{'KO' if x['ko'] else x['left1']} | bench {[(b['c'], b['left'], b['d10']) for b in x['bench']]} "
                          f"| b10 {b10} bG {bg}")
    if "H" in res and "L" in res and res["H"].get("damaging") and res["L"].get("damaging"):
        h, l = res["H"]["b10_plus_bG"], res["L"]["b10_plus_bG"]
        res["band"] = ("R-field" if l < 0.5 * h else "R-same" if abs(l - h) <= 0.25 * h else "between")
        res["L_over_H"] = r3(l / h) if h else None
    (OUT / f"summary{a.tag}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for f, v in res.items():
        print(f, v)


if __name__ == "__main__":
    main()
