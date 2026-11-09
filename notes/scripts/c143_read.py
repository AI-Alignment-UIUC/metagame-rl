"""C143 (runs/probe/C143-strength-ladder/record.md): PlusPower's field price on C139's pairs and deals at four rungs (R0 the start pilot
greedy, R1 = C139's G, R2 = C139's S, R3 the horizon-3 search), each with c139_read.arm, and the paired differences between neighbouring
rungs on the same deals (bootstrap SE over deals). The strength check (c143_h2h.py: R3's points against R2, gate 0.53) and the record's
bands; the joint tempo-four copy at R3 (c142_read.read's J) beside C142's R2 joint, unpaired. Writes summary.json.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c143_read.py
"""
import json
from pathlib import Path

import c139_read as R
from c139_read import boot, r3

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C143-strength-ladder"
C139 = ROOT / "runs/probe/C139-pp-field-price"
C142_J = {"price": -0.0365, "se": 0.0075}           # C142's pooled joint price at R2 (#641)
RUNGS = {"R0": OUT / "R0_s91.json", "R1": C139 / "G_s91.json", "R2": C139 / "S_s91.json", "R3": OUT / "R3_s91.json"}


def main():
    d, out = {}, {"rungs": {}, "steps": {}}
    for k, p in RUNGS.items():
        if p.exists():
            d[k], s = R.arm(p)
            out["rungs"][k] = {q: s[q] for q in ("deals", "errors", "price", "se", "win_share_diff", "checks")}
            if s.get("search"):
                out["rungs"][k]["capped"] = s["search"].get("capped")
    names = list(RUNGS)
    for a, b in zip(names, names[1:]):
        if a in d and b in d:
            keys = sorted(set(d[a]) & set(d[b]))
            xs = [d[b][x] - d[a][x] for x in keys]
            out["steps"][f"{b}-{a}"] = {"deals": len(keys), "mean": r3(sum(xs) / len(xs)), "se": r3(boot(xs))}
    h = OUT / "h2h_s91.json"
    if h.exists():
        hh = json.loads(h.read_text(encoding="utf-8"))
        out["strength"] = {q: hh[q] for q in ("games", "errors", "r3_points", "se", "by_r3_seat", "gate_0_53")}
    j = OUT / "J3_s91.json"
    if j.exists():
        from c142_read import read
        J = read([j])["J"]
        out["joint_R3"] = {**J, "vs_C142_R2": r3(J["price"] - C142_J["price"]), "se_diff": r3((J["se"] ** 2 + C142_J["se"] ** 2) ** 0.5)}
    if all(k in out["rungs"] for k in names) and "strength" in out:
        st, p = out["steps"], {k: out["rungs"][k]["price"] for k in names}
        top = st["R3-R2"]
        if not out["strength"]["gate_0_53"]:
            out["band"] = "void (R3 under 0.53 against R2)"
        elif all(st[f"{b}-{a}"]["mean"] >= -st[f"{b}-{a}"]["se"] for a, b in zip(names, names[1:])) \
                and p["R3"] >= 0.04 and top["mean"] >= 2 * top["se"]:
            out["band"] = "R-ladder-up"
        elif top["mean"] < 2 * top["se"] and p["R3"] < 0.04:              # the record: "R3 - R2 under 2 SE"
            out["band"] = "R-ladder-plateau"
        else:
            out["band"] = "between"
    (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
