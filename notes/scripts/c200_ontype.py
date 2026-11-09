"""C200 (runs/probe/C200-ontype-moves/record.md): does the head propose, and selection keep, off-type -> on-type basic Energy moves?
CPU only. Over C188 W0 and W0S (s48, s49) edit_slots, through c190_split's exact rebuild (its gate must PASS):
- an on-type-fix pick: out a basic Energy whose type matches none of the deck's Pokemon (at that proposal, before the row's
  edits), in a basic Energy of a type its Pokemon's attacks cost; single (n = 0) and group (n > 0) apart;
- their share of picks; the keep rate (paired_move's rule, c190_split.kept_rule) of rows holding one, against the base rate;
  their mean paired result (candidate - deck over the row's slots, thirds restored);
- Amendment 1 (R-cancel): fix rows' paired result by fix copies moved (1, 2-3, 4+), with SE, and an OLS of the row's paired
  result on its single-fix, group-fix and other copies (each row moves several picks, so a fix's own per-copy effect, net of
  its size cost, is the single-fix coefficient; taken by default, row 115);
- the population's on-type share by snapshot, 10,000 wide_deck draws' share (W0's chain sets no weights or ranges), and
  C192's split of the off-type count (exact): drift, kill, wide and mutant dilution, plus the stock at 44 by entry kind.
    py notes/scripts/c200_ontype.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c190_split as C                                   # noqa: E402

sys.path.insert(0, str(C.ROOT))
from rl.decks import wide_deck                           # noqa: E402

OUT = C.ROOT / "runs/probe/C200-ontype-moves"
RUNS = ("C188-W0-s48", "C188-W0-s49", "C188-W0S-s48", "C188-W0S-s49")
AT = 44
P = C.POOL
BT = {c["id"]: next(i for i, v in enumerate(c["provides"]) if v) for c in P.cards if c["superType"] == 3 and c["energyType"] == 0}
BTN = {c["fullName"]: BT[c["id"]] for c in P.cards if c["id"] in BT}
PTYPES = {c["id"]: {t for t, v in enumerate(c["types"]) if v and t != 0} for c in P.cards if c["superType"] == 1}
NEEDS = {c["id"]: {t for a in (c.get("attacks") or []) for t, v in enumerate(a["cost"]) if t and v} for c in P.cards if c["superType"] == 1}


def types_of(v):
    pt, nd = set(), set()
    for i in np.nonzero(v)[0]:
        pt |= PTYPES.get(int(i), set()); nd |= NEEDS.get(int(i), set())
    return pt, nd


def off_on(v):
    pt, _ = types_of(v)
    off = sum(int(v[i]) for i, t in BT.items() if v[i] > 0 and t not in pt)
    return off, sum(int(v[i]) for i in BT if v[i] > 0) - off


def mean_se(x):
    x = np.asarray(x, dtype=float)
    return [round(float(x.mean()), 4) if len(x) else None, round(float(x.std(ddof=1) / np.sqrt(len(x))), 4) if len(x) > 1 else None, len(x)]


def paired(r):
    d = np.array([round(c * 3) / 3 - round(a * 3) / 3 for _, a, c in r["slots"]], dtype=float)
    return float(d.mean()) if len(d) >= 2 else None


def one(name):
    run = C.ROOT / "runs/screens" / name
    gate = C.split(name, AT)["gate"]                     # C190's rebuild gate, the record's kill
    S, L, E = C.snaps(run, AT), C.log_rows(run), C.edits(run, AT)
    kept = defaultdict(dict)
    for (it, d), r in E.items():
        if r["kept"]:
            kept[d][it] = r
    first = {}
    for it in sorted(S):
        for d in S[it]:
            first.setdefault(d, it)
    entry = {d: S[it0][d][0] - sum((r["dv"] for i, r in kept[d].items() if i <= it0), np.zeros(P.n, dtype=np.int64)) for d, it0 in first.items()}
    kind = {d: "initial" for d in S[0]}
    for it in sorted(L):
        for x in (L[it].get("turnover") or []):
            kind.setdefault(x["in"], x["kind"])
    picks = fs = fg = 0
    rows, missing = [], 0
    for (it, d), r in sorted(E.items()):
        if d not in entry:
            missing += 1
            continue
        v = entry[d] + sum((x["dv"] for i, x in kept[d].items() if i < it), np.zeros(P.n, dtype=np.int64))
        pt, nd = types_of(v)
        c_fs = c_fg = c_o = 0
        for out, _, n, inn in r["picks"]:
            picks += 1
            fix = out in BTN and BTN[out] not in pt and inn in BTN and BTN[inn] in nd
            if fix and n == 0:
                fs += 1; c_fs += 1
            elif fix:
                fg += 1; c_fg += 1 + n
            else:
                c_o += 1 + n
        rows.append({"kept": r["kept"], "m": paired(r), "fs": c_fs, "fg": c_fg, "o": c_o})
    # population on-type share by snapshot, and C192's split of the off-type count (exact)
    share = {}
    for it in sorted(S):
        oo = np.array([off_on(v) for v, _ in S[it].values()])
        share[it] = {"on_share": round(float(oo[:, 1].sum() / oo.sum()), 4), "off_mean": round(float(oo[:, 0].mean()), 3)}
    D = len(S[0])
    offm = lambda it: float(np.mean([off_on(v)[0] for v, _ in S[it].values()]))
    tot, worst = {"drift": 0.0, "kill": 0.0, "dil_wide": 0.0, "dil_mutant": 0.0}, 0.0
    for t in range(4, AT + 1, 5):
        prev = t - 5 if t >= 9 else 0
        tov = (L.get(t) or {}).get("turnover") or []
        outs, ins = {x["out"] for x in tov}, {x["in"]: x["kind"] for x in tov}
        pre = {d: off_on(S[prev][d][0] + sum((r["dv"] for i, r in kept[d].items() if prev < i <= t), np.zeros(P.n, dtype=np.int64)))[0] for d in S[prev]}
        xpop = float(np.mean(list(pre.values())))
        kill = sum(xpop - pre[d] for d in outs) / D
        dil = {k: sum(off_on(S[t][d][0])[0] - xpop for d, kk in ins.items() if kk == k) / D for k in ("wide", "mutant")}
        drift = xpop - offm(prev)
        worst = max(worst, abs(offm(t) - offm(prev) - (drift + kill + dil["wide"] + dil["mutant"])))
        tot["drift"] += drift; tot["kill"] += kill; tot["dil_wide"] += dil["wide"]; tot["dil_mutant"] += dil["mutant"]
    stock = defaultdict(int)
    for d, (v, _) in S[AT].items():
        stock[kind.get(d, "?")] += off_on(v)[0]
    st = sum(stock.values())
    return {"run": name, "c190_gate": gate, "rows": rows, "picks": picks, "fix_single": fs, "fix_group": fg, "rows_missing_entry": missing,
            "share_by_snapshot": share, "off_split": {k: round(x, 3) for k, x in tot.items()} | {"off_0": round(offm(0), 3), f"off_{AT}": round(offm(AT), 3),
                                                                                          "identity_worst": round(worst, 9)},
            "off_stock_44_by_entry": {k: round(x / st, 3) for k, x in sorted(stock.items())} if st else {}}


def summary(rs):
    rows = [x for r in rs for x in r["rows"]]
    picks = sum(r["picks"] for r in rs)
    fix = [x for x in rows if x["fs"] + x["fg"]]
    base_keep = np.mean([x["kept"] for x in rows])
    fix_keep = np.mean([x["kept"] for x in fix]) if fix else None
    o = {"picks": picks, "fix_share": round((sum(r["fix_single"] + r["fix_group"] for r in rs)) / picks, 4),
         "fix_single_share": round(sum(r["fix_single"] for r in rs) / picks, 4), "fix_group_share": round(sum(r["fix_group"] for r in rs) / picks, 4),
         "rows": len(rows), "fix_rows": len(fix), "base_keep": round(float(base_keep), 4), "fix_keep": round(float(fix_keep), 4) if fix else None,
         "nonfix_keep": round(float(np.mean([x["kept"] for x in rows if not x["fs"] + x["fg"]])), 4),
         "fix_paired": mean_se([x["m"] for x in fix if x["m"] is not None]), "nonfix_paired": mean_se([x["m"] for x in rows if x["m"] is not None and not x["fs"] + x["fg"]])}
    bins = {}
    for lab, lo, hi in (("1", 1, 1), ("2-3", 2, 3), ("4+", 4, 99)):
        b = [x for x in fix if lo <= x["fs"] + x["fg"] <= hi and x["m"] is not None]
        bins[lab] = mean_se([x["m"] for x in b]) + [round(float(np.mean([x["fs"] + x["fg"] for x in b])), 2) if b else None]
    o["fix_paired_by_copies"] = bins                     # [mean, se, n, mean fix copies]
    X = np.array([[1, x["fs"], x["fg"], x["o"]] for x in rows if x["m"] is not None], dtype=float)
    y = np.array([x["m"] for x in rows if x["m"] is not None])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ b
    cov = np.linalg.inv(X.T @ X) * (res @ res) / (len(y) - X.shape[1])
    o["ols_per_copy"] = {k: [round(float(b[j]), 5), round(float(np.sqrt(cov[j, j])), 5)] for j, k in enumerate(("intercept", "fix_single", "fix_group", "other"))}
    return o


def main():
    OUT.mkdir(exist_ok=True)
    rs = [one(n) for n in RUNS]
    if any(r["c190_gate"] != "PASS" for r in rs):
        print("VOID: C190's rebuild gate fails:", {r["run"]: r["c190_gate"] for r in rs})
    rng = np.random.default_rng(2000)
    g = np.array([off_on(wide_deck(P, rng))[::-1] for _ in range(10000)])     # [on, off]
    gen = {"draws": 10000, "on_share": round(float(g[:, 0].sum() / g.sum()), 4), "off_mean": round(float(g[:, 1].mean()), 3)}
    out = {"generator": gen, "pooled": summary(rs), "by_run": {}}
    for r in rs:
        out["by_run"][r["run"]] = {"c190_gate": r["c190_gate"], **summary([r]), "rows_missing_entry": r["rows_missing_entry"],
                                   "share_by_snapshot": r["share_by_snapshot"], "off_split": r["off_split"], "off_stock_44_by_entry": r["off_stock_44_by_entry"]}
    p = out["pooled"]
    wide_half = np.mean([r["off_stock_44_by_entry"].get("wide", 0) for r in rs]) >= 0.5
    cancel = abs(p["ols_per_copy"]["fix_single"][0]) <= 0.005
    band = ("R-not-proposed" if p["fix_share"] <= 0.01 else
            "R-proposed-not-kept" if p["fix_share"] >= 0.03 and p["fix_keep"] <= p["base_keep"] else
            "R-refilled" if p["fix_keep"] > p["base_keep"] and wide_half else "between")
    out["band"], out["R_cancel"], out["wide_stock_share_mean"] = band, bool(cancel), round(float(np.mean([r["off_stock_44_by_entry"].get("wide", 0) for r in rs])), 3)
    (OUT / "read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "by_run"}, indent=1))
    for n, r in out["by_run"].items():
        print(n, {k: r[k] for k in ("c190_gate", "fix_share", "fix_keep", "base_keep", "fix_paired", "rows_missing_entry", "off_split", "off_stock_44_by_entry")},
              "on_share 0/44:", r["share_by_snapshot"][0]["on_share"], r["share_by_snapshot"][AT]["on_share"], "ols fix_single", r["ols_per_copy"]["fix_single"])


if __name__ == "__main__":
    main()
