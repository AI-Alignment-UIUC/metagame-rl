"""C180, research's read after stage 1: is d14's gain the list decking itself out? From the saved games, no new ones. Per pilot: (1) each side's event points split by how the game ended, each ending's share of games x its points; (2) the side's own deck-out losses; (3) the same deals split by how the LIST's game went, so the parts sum to d14 - list: share of deals x mean (copy - list) on them.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c180_endings.py
"""
import collections
import json
from pathlib import Path

import numpy as np

from c139_read import pts, r3

ROOT = Path(__file__).resolve().parents[2]
C179 = ROOT / "runs/probe/C179-shape-dose"
C180 = ROOT / "runs/probe/C180-dose-by-practice"
ENDINGS = ("no-pokemon", "prizes", "deck-out", "time")


def label(x):
    won = x["winner"] == x["iSeat"]
    lost = x["winner"] in (1, 2) and not won
    e = x.get("ending")
    return ("win " if won else "loss " if lost else "no winner ") + str(e)


def read(f, copies):
    r = json.loads(f.read_text(encoding="utf-8"))
    n0 = r["n_lists"]
    deals = collections.defaultdict(dict)
    for x in r["results"]:
        if not x.get("error"):
            deals[x["seed"]][x["i"]] = x
    lst, cop, parts = [], [], collections.defaultdict(list)
    clean = collections.defaultdict(list)                  # C181 Amendment 1: deck-out deals removed from both arms, pair by pair, by list
    for g in deals.values():
        base = next((v for i, v in g.items() if i < n0), None)
        if base is None:
            continue
        cs = [v for i, v in g.items() if i >= n0 and copies[i - n0]["arm"] == "d14"]
        if not cs:
            continue
        lst.append(base)
        for v in cs:
            if base.get("ending") != "deck-out" and v.get("ending") != "deck-out":
                clean[base["i"]].append(pts(v)[0] - pts(base)[0])
        cop += cs
        parts[label(base)].append(float(np.mean([pts(v)[0] for v in cs])) - pts(base)[0])
    def side(rows):
        n = len(rows)
        c = collections.Counter(label(x) for x in rows)
        p = collections.defaultdict(float)
        for x in rows:
            p[label(x)] += pts(x)[0] / n
        return {"games": n, "points": r3(sum(p.values())), "share": {k: r3(v / n) for k, v in sorted(c.items())}, "points_by_ending": {k: r3(v) for k, v in sorted(p.items()) if v}, "own_deck_out_losses": r3(c["loss deck-out"] / n), "opp_deck_out_wins": r3(c["win deck-out"] / n)}
    tot = sum(len(v) for v in parts.values())
    split = {k: {"share_of_deals": r3(len(v) / tot), "mean_change": r3(float(np.mean(v))), "contribution": r3(sum(v) / tot)} for k, v in sorted(parts.items(), key=lambda kv: -sum(kv[1]))}
    vals = np.array([float(np.mean(v)) for v in clean.values()])
    rng = np.random.default_rng(180)
    se = float(np.std([vals[rng.integers(len(vals), size=len(vals))].mean() for _ in range(4000)]))
    return {"pilot": r["pilot"], "gain_no_deck_outs": r3(float(vals.mean())), "se_no_deck_outs": r3(se), "list": side(lst), "d14": side(cop), "gain": r3(sum(sum(v) for v in parts.values()) / tot), "by_list_game": split}


def main():
    copies = json.loads((C179 / "decks.json").read_text(encoding="utf-8"))
    fresh = json.loads((C180 / "decks_fresh.json").read_text(encoding="utf-8"))
    out = {"C49": read(C179 / "G_C49.json", copies), "arm0_s1": read(C179 / "G_arm0.json", copies)}
    for f in sorted(C180.glob("G_*.json")):
        out[f.stem[2:]] = read(f, fresh if f.stem.endswith("_fresh") else copies)
    (C180 / "endings.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("no deck-outs in either arm (SE):", {k: (v["gain_no_deck_outs"], v["se_no_deck_outs"]) for k, v in out.items()})
    print("pilot | gain | list deck-out losses, d14's | contribution of deals the list lost by deck-out (share) | other losses | wins | no winner")
    for k, v in out.items():
        b = v["by_list_game"]
        g = lambda pre: r3(sum(x["contribution"] for q, x in b.items() if q.startswith(pre)))
        dq = b.get("loss deck-out", {"contribution": 0, "share_of_deals": 0})
        print(k, v["gain"], "|", v["list"]["own_deck_out_losses"], v["d14"]["own_deck_out_losses"], "|", dq["contribution"], f"({dq['share_of_deals']})", "|", r3(g("loss") - dq["contribution"]), "|", g("win"), "|", g("no winner"), "| opp deck-out wins", v["list"]["opp_deck_out_wins"], v["d14"]["opp_deck_out_wins"])


if __name__ == "__main__":
    main()
