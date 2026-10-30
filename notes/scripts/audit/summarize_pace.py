"""C114 (pace probe): summaries of runs/probe/C114-pace/<pilot>_P<list>_s<seed>.jsonl from pace_games.py, per pilot and list, pooled over lists, and the
record's bands (SimpleBot vs arm 0 knockouts per own turn). Writes runs/probe/C114-pace/summary.json.
Run: .venv/Scripts/python.exe notes/scripts/audit/summarize_pace.py [--seeds 91 2]"""
import argparse, collections, json, math, statistics
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--seeds", type=int, nargs="*", default=[91, 2])
args = ap.parse_args()
OUT = Path.cwd() / "runs/probe/C114-pace"
LISTS = {0: "P0 list 3 (Osborn Haymaker)", 1: "P1 list 1 (Lieu Wigglytuff)", 2: "P2 list 21 (Graham Haymaker)", 3: "P3 list 2 (Neathery Haymaker)"}
PILOTS = ["start", "arm0", "simplebot"]


def load(pilot, di, seeds):
    games = []
    for s in seeds:
        f = OUT / f"{pilot}_P{di}_s{s}.jsonl"
        if f.exists():
            games += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return games


def med(x):
    return statistics.median(x) if x else None


def r(x, k=3):
    return None if x is None else round(x, k)


def summarize(games):
    n = len(games)
    turns = [t for g in games for t in g["turns"]]
    nt = len(turns)
    kos = sum(t["kos"] for t in turns)
    per_game = [sum(t["kos"] for t in g["turns"]) / max(1, len(g["turns"])) for g in games]
    se = statistics.stdev(per_game) / math.sqrt(n) if n > 1 else None
    by_prizes = [g for g in games if g["ending"] == "prizes"]
    six = [sum(1 for t in g["turns"] if t["p"] == g["winner"]) for g in by_prizes]
    first = []
    for g in games:
        for p in (1, 2):
            idx = [i for i, t in enumerate((t for t in g["turns"] if t["p"] == p), 1) if t["payE"]]
            first.append(idx[0] if idx else None)
    got = [f for f in first if f is not None]
    pay_known = [t for t in turns if t["payE"] is not None]
    att = sum(t["att"] for t in turns)
    non_atk = sum(t["att"] for t in turns if t["att"] and not t["attAtk"])
    end = collections.Counter(g["ending"] or "none" for g in games)
    cap = lambda g: g["ending"] == "time"
    return {
        "games": n, "own_turns": nt, "errors": sum(1 for g in games if g["error"]),
        "kos_per_own_turn": r(kos / nt, 4), "kos_per_own_turn_se": r(se, 4),
        "prizes_per_own_turn": r(sum(t["prizes"] for t in turns) / nt, 4),
        "share_games_ending_by_prizes": r(len(by_prizes) / n),
        "median_own_turns_to_six_prizes": med(six), "mean_own_turns_to_six_prizes": r(statistics.mean(six)) if six else None,
        "median_own_turns_to_first_payable_attack": med(got), "share_seats_never_payable": r(1 - len(got) / len(first)),
        "payable_share_end_of_turn": r(sum(1 for t in pay_known if t["payE"]) / len(pay_known)),
        "payable_share_start_of_main": r(sum(1 for t in turns if t["payS"]) / nt),
        "attack_share": r(sum(t["atk"] for t in turns) / nt),
        "energy_attached_per_own_turn": r(att / nt), "attach_share_to_non_attackers": r(non_atk / att) if att else None,
        "attach_share_to_active": r(sum(t["att"] for t in turns if t["attTo"] == "active") / att) if att else None,
        "energy_lost_to_removal_per_game": r(sum(t["erLost"] for t in turns) / n), "energy_attached_per_game": r(att / n),
        "energy_lost_over_attached": r(sum(t["erLost"] for t in turns) / att) if att else None,
        "retreats_per_game": r(sum(t["retreat"] for t in turns) / n), "switches_per_game": r(sum(t["sw"] for t in turns) / n),
        "evolutions_per_game": r(sum(t["evolve"] for t in turns) / n), "cards_drawn_per_own_turn": r(sum(t["drawn"] for t in turns) / nt),
        "endings": dict(end), "safety_cap_games": sum(1 for g in games if cap(g)), "mean_game_turns": r(statistics.mean(g["turn"] for g in games), 1),
    }


def band(rows, seeds_label):
    ratios = {}
    for di in LISTS:
        a, b = rows["arm0"][LISTS[di]], rows["simplebot"][LISTS[di]]
        ratios[LISTS[di]] = r(b["kos_per_own_turn"] / a["kos_per_own_turn"], 3)
    hi = sum(1 for v in ratios.values() if v >= 1.5)
    lo = sum(1 for v in ratios.values() if v <= 1.2)
    return {"seeds": seeds_label, "simplebot_over_arm0_ko_per_turn": ratios, "lists_ge_1.5": hi, "lists_le_1.2": lo,
            "band": "R-learnable" if hi >= 3 else "R-deck-paced" if lo >= 3 else "between"}


out = {}
for label, seeds in [("all_seeds", args.seeds), *[(f"seed_{s}", [s]) for s in args.seeds]]:
    rows = {p: {LISTS[di]: summarize(load(p, di, seeds)) for di in LISTS} for p in PILOTS}
    for p in PILOTS:
        rows[p]["pooled"] = summarize([g for di in LISTS for g in load(p, di, seeds)])
    out[label] = {"seeds": seeds, "rows": rows, "band": band(rows, seeds)}
(OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for label, o in out.items():
    print("==", label, o["band"])
    keys = ["games", "kos_per_own_turn", "kos_per_own_turn_se", "median_own_turns_to_six_prizes", "share_games_ending_by_prizes",
            "median_own_turns_to_first_payable_attack", "payable_share_end_of_turn", "attack_share", "energy_attached_per_own_turn",
            "attach_share_to_non_attackers", "energy_lost_over_attached", "retreats_per_game", "switches_per_game", "evolutions_per_game",
            "cards_drawn_per_own_turn", "endings", "mean_game_turns"]
    for p in PILOTS:
        for name, row in o["rows"][p].items():
            print(f"{p:9s} {name[:14]:14s}", " | ".join(f"{k.split('_per_')[0][:12]}={row[k]}" for k in keys))
