"""C206's read (runs/probe/C206-draw-mask-price/record.md), written before the runs: c193_run's read over the C206 cell files
(M by tag, seed and direction, SE with the lists fixed), then per pilot (C49, W48) and mask (M0, M10, M15):
- M_minus and M_plus pooled over both seeds (mean of the seeds' M; SE the seeds' lists-fixed SEs combined, as C193's pooled);
- Δ = M_minus(Mk) - M_minus(M0), the mean of the per-seed differences. Its SE is paired (taken by default, row 115, before
  the runs): both masks play the same variants on the same deals, so per seed and (list, variant) the share difference, its
  variance over a list's variants / their number, summed over lists / lists² (C193 Amendment 3's lists-fixed form), and the two
  seeds combined. The unpaired SE (the cells' SEs combined) is reported beside it;
- deck-out share of all games, mean game length (turns), and the mask's bite: masked / main-phase asked decisions, and empty
  (the kill: must be 0);
- the check that C49-M0 reproduces C193's greedy cells (M_minus and M_plus per seed).
Bands (record): R-overdraw-prices if, for both pilots, Δ(M10) ≥ +0.03 at 2 SE or M_minus(M10) ≥ 0.50; R-not-pricing if, for
both pilots, |Δ(M10)| < 0.015 with SE ≤ 0.0075; between otherwise. M15 is reported beside it.
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c206_read.py
"""
import contextlib
import io
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT / "ar"))
sys.path.insert(0, str(ROOT))
import c193_run as C                                     # noqa: E402

D = ROOT / "runs/probe/C206-draw-mask-price"
PILOTS, MASKS, DIRS = ("C49", "W48"), ("M0", "M10", "M15"), ("minus", "plus")


def cell(tag, seed):
    f = D / f"cells_greedy-{tag}_s{seed}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def shares(d, dr):
    """(list, v) -> share of decisive games the list won, for one direction."""
    a = {}
    for x in d["results"]:
        if x["dir"] == dr and x["winner"] in (1, 2):
            e = a.setdefault((x["list"], x["v"]), [0, 0]); e[0] += x["winner"] == x["iSeat"]; e[1] += 1
    return {k: w / n for k, (w, n) in a.items() if n}


def paired_se(d1, d0, dr):
    s1, s0 = shares(d1, dr), shares(d0, dr)
    keys = sorted(set(s1) & set(s0))
    lists = sorted({k[0] for k in keys})
    var = 0.0
    for li in lists:
        dv = np.array([s1[k] - s0[k] for k in keys if k[0] == li])
        if len(dv) > 1:
            var += dv.var(ddof=1) / len(dv)
    return float(np.sqrt(var) / len(lists)) if lists else None


def main():
    C.OUT = D
    with contextlib.redirect_stdout(io.StringIO()):
        C.read()
    r = json.loads((D / "read.json").read_text(encoding="utf-8"))
    out = {"pilots": {}}
    for p in PILOTS:
        po = {}
        for m in MASKS:
            tag = f"{p}-{m}"
            o = {}
            for dr in DIRS:
                a, b = r.get(f"cells_greedy-{tag}_s1_{dr}"), r.get(f"cells_greedy-{tag}_s2_{dr}")
                if a and b:
                    o[f"M_{dr}"] = {"M": round((a["M"] + b["M"]) / 2, 4), "se": round(float(np.hypot(a["se_lists_fixed"], b["se_lists_fixed"]) / 2), 4),
                                    "s1": a["M"], "s2": b["M"]}
            dc, games, turns, cnt = 0, 0, [], {}
            for sd in (1, 2):
                d = cell(tag, sd)
                if not d:
                    continue
                for x in d["results"]:
                    games += 1; dc += x.get("ending") == "deck-out"
                    if x.get("turns") is not None:
                        turns.append(x["turns"])
                for q, v in (d.get("draw_mask_counts") or {}).items():
                    cnt[q] = cnt.get(q, 0) + v
                o.setdefault("runs", []).append({"seed": sd, "games": d["games"], "errors": d["errors"], "seconds": d["seconds"], "complete": d["complete"]})
            o.update({"deckout_share": round(dc / games, 4) if games else None, "turns_mean": round(float(np.mean(turns)), 2) if turns else None,
                      "mask_counts": cnt, "masked_share_of_main": round(cnt["masked"] / cnt["main"], 4) if cnt.get("main") else None})
            po[m] = o
        for m in ("M10", "M15"):
            if "M_minus" not in po[m] or "M_minus" not in po["M0"]:
                continue
            ds, ses = [], []
            for sd in (1, 2):
                d1, d0 = cell(f"{p}-{m}", sd), cell(f"{p}-M0", sd)
                ds.append(r[f"cells_greedy-{p}-{m}_s{sd}_minus"]["M"] - r[f"cells_greedy-{p}-M0_s{sd}_minus"]["M"])
                ses.append(paired_se(d1, d0, "minus"))
            po[m]["delta_minus"] = {"d": round(float(np.mean(ds)), 4), "se_paired": round(float(np.hypot(*ses) / 2), 4),
                                    "se_unpaired": round(float(np.hypot(po[m]["M_minus"]["se"], po["M0"]["M_minus"]["se"])), 4),
                                    "s1": round(ds[0], 4), "s2": round(ds[1], 4)}
        out["pilots"][p] = po
    c193 = json.loads((ROOT / "runs/probe/C193-lists-swap-depth/read.json").read_text(encoding="utf-8"))
    out["check_C49_M0_vs_C193"] = {f"s{sd}_{dr}": [r.get(f"cells_greedy-C49-M0_s{sd}_{dr}", {}).get("M"), (c193.get(f"cells_greedy_s{sd}_{dr}") or {}).get("M")]
                                   for sd in (1, 2) for dr in DIRS}
    ok = all("delta_minus" in out["pilots"][p].get("M10", {}) for p in PILOTS)
    if ok:
        dl = {p: out["pilots"][p]["M10"]["delta_minus"] for p in PILOTS}
        m10 = {p: out["pilots"][p]["M10"]["M_minus"]["M"] for p in PILOTS}
        prices = all((dl[p]["d"] >= 0.03 and dl[p]["d"] >= 2 * dl[p]["se_paired"]) or m10[p] >= 0.50 for p in PILOTS)
        flat = all(abs(dl[p]["d"]) < 0.015 and dl[p]["se_paired"] <= 0.0075 for p in PILOTS)
        out["band"] = "R-overdraw-prices" if prices else "R-not-pricing" if flat else "between"
    else:
        out["band"] = "not ready"
    empty = sum(out["pilots"][p][m].get("mask_counts", {}).get("empty", 0) for p in PILOTS for m in MASKS)
    out["kill_empty"] = empty
    (D / "c206_read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
