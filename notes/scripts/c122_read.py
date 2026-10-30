"""C122 stage A's readout (runs/probe/C122-L-search/record.md): for each eval seed, M and the four focus prices under arm S (the
pilot's own search at Trainer-playable decisions) and arm G (greedy), in event points under the cap (notes/scripts/c113_read.py),
their paired differences on the same deals, and the record's bands (R-search-lifts: M_S - M_G >= +0.03 at both seeds;
R-not: |M_S - M_G| < 0.03 at both). With the traces (c122_run.py --trace), the play readouts for both seats pooled: Oak or Bill
played when held, PlusPower per attack, a full Bench at attack. Evaluation only.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c122_read.py runs/probe/C122-L-search [--seeds 91 2]
"""
import argparse
import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c113_read import FOCUS, read   # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)   # c113_read's F over cards that weren't run


def flow(path: Path, seeds: set):
    """Only the arm's own games (their job seeds): a search's copy of a game that ends inside its turn has no job seed."""
    if not path.exists():
        return None
    last = {}                                        # a copy ends before its game does, so a seed's last line is the game's
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            g = json.loads(line)
            if g.get("seed") in seeds:
                last[g["seed"]] = g
    ob = obp = att = pp = full = 0
    for g in last.values():
        for t in g["turns"]:
            ob += t["ob"] > 0
            obp += t["ob"] > 0 and t["obp"] > 0
            if t.get("A"):
                att += 1
                pp += t["ppP"]
                full += t["A"][0]["bA"] == 5
    return {"oak_bill_played_when_held": round(obp / max(ob, 1), 3), "pluspower_per_attack": round(pp / max(att, 1), 4),
            "full_bench_at_attack": round(full / max(att, 1), 3), "held_turns": ob, "attacks": att}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--seeds", type=int, nargs="+", default=[91, 2])
    a = ap.parse_args()
    d = Path(a.dir)
    out = {"seeds": {}}
    for s in a.seeds:
        r = {arm: read(str(d / f"{arm}_s{s}.json")) for arm in ("G", "S") if (d / f"{arm}_s{s}.json").exists()}
        if len(r) < 2:
            out["seeds"][s] = {"incomplete": sorted(r)}
            continue
        g, sr = r["G"], r["S"]
        out["seeds"][s] = {"M_G": g["M_points"], "M_S": sr["M_points"], "dM": round(sr["M_points"] - g["M_points"], 4),
                           # focus prices only for the cards that were run (stage A's cut dropped them; NaN otherwise)
                           "cards": {c: {"G": g["cards_points"][c]["pooled"], "S": sr["cards_points"][c]["pooled"],
                                         "d": round(sr["cards_points"][c]["pooled"] - g["cards_points"][c]["pooled"], 4)}
                                     for c in FOCUS if g["cards_points"][c]["per_list"]},
                           "games": [g["games"], sr["games"]], "time_share": [g["time_share"], sr["time_share"]],
                           "flow": {arm: flow(d / f"{arm}_s{s}.trace.jsonl", {x["seed"] for x in json.loads((d / f"{arm}_s{s}.json").read_text())["results"]})
                                    for arm in ("G", "S")}}
    dm = [v["dM"] for v in out["seeds"].values() if "dM" in v]
    out["band"] = ("incomplete" if len(dm) < len(a.seeds) else "R-search-lifts" if all(x >= 0.03 for x in dm)
                   else "R-not" if all(abs(x) < 0.03 for x in dm) else "between")
    (d / "readout.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
