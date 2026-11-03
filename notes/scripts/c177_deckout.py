"""C177, research's read (#860), from saved games: does G3 flatter what simply outlasts lists that deck themselves out? M and event points for W s49's top 12 at 59 and 74, greedy and search, and the lists against the lists, three ways: all games; without the games the opposing list lost by deck-out; without any deck-out. M is per pair over decisive games, as G3.
  PYTHONPATH=.:notes/scripts .venv/Scripts/python notes/scripts/c177_deckout.py
"""
import glob
import json
from pathlib import Path

from c139_read import r3
from g3_yardstick import reads

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "runs/probe/C177-g3-yardstick"


def rows(pattern):
    out = []
    for f in sorted(glob.glob(str(D / pattern))):
        out += json.loads(Path(f).read_text(encoding="utf-8"))["results"]
    return out


def opp_out(x):
    return x.get("ending") == "deck-out" and x["winner"] == x["iSeat"]


def own_out(x):
    return x.get("ending") == "deck-out" and x["winner"] in (1, 2) and x["winner"] != x["iSeat"]


def main():
    cells = {"lists greedy": "lists.json", "W49 at 59 greedy": "w49_0059.json", "W49 at 74 greedy": "w49_0074.json", "W49 at 29 greedy": "w49_0029.json", "W49 at 59 search": "search59_*.json", "W49 at 74 search": "search74_*.json", "lists search": "searchlists_*.json", "D s48 at 0 greedy": "d48_0000.json", "D s49 at 0 greedy": "d49_0000.json", "W s48 at 0 greedy": "w48_0000.json", "W s49 at 0 greedy": "w49_0000.json", "D s48 at 0 search": "searchd48_*.json", "D s49 at 0 search": "searchd49_*.json", "D s48 at 29 greedy": "d48_0029.json", "D s49 at 29 greedy": "d49_0029.json", "D s48 at 44 greedy": "d48_0044.json", "D s49 at 44 greedy": "d49_0044.json", "D s48 at 29 search": "searchd48at29_*.json", "D s49 at 29 search": "searchd49at29_*.json", "D s48 at 44 search": "searchd48at44_*.json", "D s49 at 44 search": "searchd49at44_*.json"}
    out = {}
    for name, pattern in cells.items():
        r = rows(pattern)
        if not r:
            continue
        keep = lambda q: {k: q[k] for k in ("games", "M", "se_pairs", "win_share_all_games", "full_wins", "full_losses", "event_points")}
        out[name] = {"opp_lost_by_deck_out": r3(sum(map(opp_out, r)) / len(r)), "own_deck_out_losses": r3(sum(map(own_out, r)) / len(r)), "all": keep(reads(r)), "without_opp_deck_outs": keep(reads([x for x in r if not opp_out(x)])), "without_any_deck_out": keep(reads([x for x in r if x.get("ending") != "deck-out"]))}
    (D / "deckout.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, "| opp out", v["opp_lost_by_deck_out"], "own out", v["own_deck_out_losses"], "| M all", v["all"]["M"], "without opp", v["without_opp_deck_outs"]["M"], "without any", v["without_any_deck_out"]["M"], "| points", v["all"]["event_points"], v["without_opp_deck_outs"]["event_points"], v["without_any_deck_out"]["event_points"])


if __name__ == "__main__":
    main()
