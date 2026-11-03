"""C167 (runs/probe/C167-body-trainer-cross/record.md): base scores of the lists (A), body with scrambled Trainers (T), body with scrambled identities at the lists' copy counts (C),
Trainers with a scrambled body (B) and rules-only decks (R) against the rules-only field. Effects on the points and logit scales: Gap = A - R; Body = [(A - B) + (T - R)]/2;
Trainers = [(A - T) + (B - R)]/2; I = A - T - B + R; Identities = A - C; Concentration = C - T. SE is the larger of a deal bootstrap and a bootstrap over source lists (A, T, C, B
together) and decks (R). A cell under 0.25 or over 0.75 makes its effects provisional, passing only if the logit version does; under 0.15 or over 0.85 is unreadable. Bands per
pilot, and a band needs both. Arm 0 s1's A and R are C163's games (LR_s91, RR_s91: the same decks, opponents, keys and deals; their copies aren't read).
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c167_read.py [--pilots s16,arm0] [--check FILE]
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from c139_read import pts, r3

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C167-body-trainer-cross"
C163, C164 = ROOT / "runs/probe/C163-draw-deck-field", ROOT / "runs/probe/C164-list-knockout"
CELLS = ("A", "T", "C", "B", "R")
DECKS = {"A": C163 / "L_base.json", "T": C164 / "T.json", "C": C164 / "C.json", "B": C164 / "B.json", "R": C163 / "R_base.json"}
USES = {"Gap": "AR", "Body": "ATBR", "Trainers": "ATBR", "I": "ATBR", "Identities": "AC", "Concentration": "CT"}
BOUNDS = ((12, 15), (26, 30), (16, 20))


def path_of(pilot, cell):
    if pilot == "arm0" and cell in ("A", "R"):
        return C163 / ("LR_s91.json" if cell == "A" else "RR_s91.json")
    return OUT / f"{cell}_{pilot}.json"


def read_cell(path, cell):
    """Each base deck's games: its source (a list, or the deck itself for R), the score, the ending; and the checks."""
    r = json.loads(Path(path).read_text(encoding="utf-8"))
    decks = json.loads(DECKS[cell].read_text(encoding="utf-8"))
    names = r["deck_names"]
    by = {(x["i"], x["j"], x["seed"]): x for x in r["results"] if not x.get("error")}
    n_err = sum(1 for x in r["results"] if x.get("error"))
    src, score, win, full, opp, deck, end, opps = [], [], [], [], [], [], Counter(), set()
    games_by = defaultdict(list)
    for (i, j, _), x in by.items():
        games_by[(i, j)].append(x)
    for m in r["meta"]:
        for x in games_by[(m["list"], m["opp"])]:
            src.append(decks[m["list"]]["src"])
            score.append(pts(x)[0])
            win.append(pts(x)[1])
            full.append(pts(x)[1] == 1.0 and x.get("ending") != "time")
            opp.append(names[m["opp"]])
            deck.append(m["list"])
            end[x.get("ending")] += 1
        opps.add((m["list"], m["opp"]))
    never = all(names[o] != decks[k]["src"] for k, o in opps)
    return {"src": np.array(src), "score": np.array(score, dtype=float), "win": np.array(win, dtype=float), "full": np.array(full, dtype=float), "opp": np.array(opp), "deck": np.array(deck), "endings": dict(end), "errors": n_err, "n": len(r["results"]),
            "never_source": never, "seeds": len({s for (_, _, s) in by}), "last": r.get("last", {})}


def logit(p):
    p = np.clip(p, 1e-3, 1 - 1e-3)
    return np.log(p / (1 - p))


def effects(m):
    A, T, C, B, R = (m[k] for k in CELLS)
    return {"Gap": A - R, "Body": 0.5 * ((A - B) + (T - R)), "Trainers": 0.5 * ((A - T) + (B - R)), "I": A - T - B + R, "Identities": A - C, "Concentration": C - T}


def per_list(cells):
    return {k: {s: float(c["score"][c["src"] == s].mean()) for s in sorted(set(c["src"].tolist()))} for k, c in cells.items()}


def analyse(cells, reps=2000):
    rng = np.random.default_rng(167)
    means = {k: float(c["score"].mean()) for k, c in cells.items()}
    point, point_l = effects(means), effects({k: logit(v) for k, v in means.items()})
    deal, deal_l = defaultdict(list), defaultdict(list)
    clus, clus_l = defaultdict(list), defaultdict(list)
    pl = per_list(cells)
    lists = sorted(pl["A"])
    for _ in range(reps):
        d = {k: float(c["score"][rng.integers(len(c["score"]), size=len(c["score"]))].mean()) for k, c in cells.items()}
        for k, v in effects(d).items():
            deal[k].append(v)
        for k, v in effects({x: logit(y) for x, y in d.items()}).items():
            deal_l[k].append(v)
        draw = [lists[int(i)] for i in rng.integers(len(lists), size=len(lists))]
        rs = list(pl["R"].values())
        cl = {k: float(np.mean([pl[k][s] for s in draw])) for k in "ATCB"}
        cl["R"] = float(np.mean([rs[int(i)] for i in rng.integers(len(rs), size=len(rs))]))
        for k, v in effects(cl).items():
            clus[k].append(v)
        for k, v in effects({x: logit(y) for x, y in cl.items()}).items():
            clus_l[k].append(v)
    se = lambda a, b, k: max(float(np.std(a[k], ddof=1)), float(np.std(b[k], ddof=1)))
    return means, {k: {"est": point[k], "se": se(deal, clus, k), "se_deal": float(np.std(deal[k], ddof=1)), "se_cluster": float(np.std(clus[k], ddof=1)),
                       "logit": point_l[k], "logit_se": se(deal_l, clus_l, k)} for k in point}


def statuses(means, eff):
    """Per effect: carries, doesn't or neither, under the record's provisional and unreadable rules."""
    soft = {k: not 0.25 <= v <= 0.75 for k, v in means.items()}
    hard = {k: not 0.15 <= v <= 0.85 for k, v in means.items()}
    out = {}
    for name, e in eff.items():
        if any(hard[c] for c in USES[name]):
            out[name] = {"unreadable": True, "provisional": True, "carries": False, "doesnt": False}
            continue
        prov = any(soft[c] for c in USES[name])
        carries = e["est"] >= 0.10 and e["est"] >= 2 * e["se"] and (not prov or (e["logit"] >= 0.40 and e["logit"] >= 2 * e["logit_se"]))
        doesnt = e["est"] < 0.05 and (not prov or e["logit"] < 0.20)
        out[name] = {"unreadable": False, "provisional": prov, "carries": carries, "doesnt": doesnt}
    return out


def band_of(st):
    b, t, i = st["Body"], st["Trainers"], st["I"]
    if b["carries"] and t["doesnt"]:
        return "R-body"
    if t["carries"] and b["doesnt"]:
        return "R-trainers"
    if b["carries"] and t["carries"]:
        return "R-both"
    if not b["carries"] and not t["carries"] and i["carries"]:
        return "R-joint"
    return "between"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilots", default="s16,arm0")
    ap.add_argument("--check", default="")
    ap.add_argument("--cell", default="")
    a = ap.parse_args()
    if a.check:
        c = read_cell(a.check, a.cell)
        print(json.dumps({"cell": a.cell, "games": c["n"], "errors": c["errors"], "score": r3(float(c["score"].mean())), "never_source": c["never_source"], "last": {k: c["last"].get(k) for k in ("games", "seconds", "games_per_s")}}))
        sys.exit(0 if c["never_source"] and c["errors"] <= 0.02 * c["n"] else 3)
    pilots = a.pilots.split(",")
    res = {}
    for p in pilots:
        cells = {k: read_cell(path_of(p, k), k) for k in CELLS}
        means, eff = analyse(cells)
        st = statuses(means, eff)
        res[p] = {"means": {k: r3(v) for k, v in means.items()}, "effects": {k: {x: r3(y) for x, y in v.items()} for k, v in eff.items()}, "status": st, "band": band_of(st),
                  "endings": {k: c["endings"] for k, c in cells.items()}, "games": {k: c["n"] for k, c in cells.items()}, "errors": {k: c["errors"] for k, c in cells.items()},
                  "never_source": all(c["never_source"] for c in cells.values()), "games_per_s": {k: c["last"].get("games_per_s") for k, c in cells.items()}}
        from rl.decks import Pool
        card = {x["fullName"]: x for x in Pool().cards}
        lists = json.loads((C163 / "L.json").read_text(encoding="utf-8"))
        shape = {d["name"]: (sum(card[x]["superType"] == 1 for x in d["cards"]), sum(card[x]["superType"] == 2 for x in d["cards"]), sum(card[x]["superType"] == 3 for x in d["cards"])) for d in lists}
        inside = [n for n, s in shape.items() if all(lo <= v <= hi for v, (lo, hi) in zip(s, BOUNDS))]
        pl = per_list(cells)
        r_mean = means["R"]
        res[p]["lists_inside_C162_bounds"] = {"n": len(inside), "A_minus_R": r3(float(np.mean([pl["A"][n] for n in inside])) - r_mean) if inside else None}
        res[p]["per_list"] = {n: {"A": r3(pl["A"][n]), "Body": r3(0.5 * ((pl["A"][n] - pl["B"][n]) + (pl["T"][n] - r_mean))), "Trainers": r3(0.5 * ((pl["A"][n] - pl["T"][n]) + (pl["B"][n] - r_mean)))} for n in pl["A"]}
    first, second = pilots[0], pilots[1] if len(pilots) > 1 else pilots[0]
    gap = {p: res[p]["status"]["Gap"] for p in pilots}
    if res[first]["effects"]["Gap"]["est"] < 0.10 and gap[second]["carries"]:
        band = "R-pilot-blind"
    elif res[second]["effects"]["Gap"]["est"] < 0.10:
        band = "R-no-gap"
    elif res[first]["band"] == res[second]["band"]:
        band = res[first]["band"]
    else:
        band = "between"
    out = {"band": band, "pilots": res}
    if a.pilots == "s16,arm0":
        (OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    else:
        (OUT / f"summary_{a.pilots.replace(',', '_')}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("band", band)
    for p, v in res.items():
        print(p, "band", v["band"], "means", v["means"], "games", v["games"], "errors", v["errors"], "never_source", v["never_source"], "inside", v["lists_inside_C162_bounds"])
        for k, e in v["effects"].items():
            print("  ", k, e, {x: y for x, y in v["status"][k].items() if y})
        print("   endings", v["endings"])


if __name__ == "__main__":
    main()
