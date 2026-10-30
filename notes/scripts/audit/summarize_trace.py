"""Engine audit part 1 (log #484, Evan's row 102): summary of the per-turn traces from trace_games.py, per list and pooled, capped
(round rule [20, 45]) and untimed. Writes runs/probe/AUDIT-engine/trace_summary.json. Run: .venv/Scripts/python.exe notes/scripts/audit/summarize_trace.py"""
import collections, json
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "runs/probe/AUDIT-engine"
decks = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
NAMES = [d["name"] for d in decks]


def mean(x):
    x = list(x)
    return round(sum(x) / len(x), 3) if x else None


def summarize(games):
    n = len(games)
    turns = [t for g in games for t in g["turns"]]
    nt = len(turns)
    first_ko = [min(k["turn"] for k in g["kos"]) for g in games if g["kos"]]
    timed = [g for g in games if g["ending"] == "time"]
    margins = collections.Counter()
    for g in timed:
        m = abs(g["prizesLeft"]["1"] - g["prizesLeft"]["2"])
        margins["0 (draw)" if m == 0 else "1" if m == 1 else "2+"] += 1
    atk_not_taken = [t for t in turns if t["atkLegal"] and not t["tried"]]
    return {
        "games": n,
        "endings": dict(collections.Counter(g["ending"] for g in games)),
        "errors": sum(1 for g in games if g["error"]),
        "game_turns_mean": mean(g["turn"] for g in games),
        "game_turns_median": sorted(g["turn"] for g in games)[n // 2] if n else None,
        "kos_per_game": mean(len(g["kos"]) for g in games),
        "prizes_taken_per_game_both_seats": mean(sum(12 - 0 - g["prizesLeft"]["1"] - g["prizesLeft"]["2"] for _ in [0]) for g in games),
        "games_with_no_ko": sum(1 for g in games if not g["kos"]),
        "first_ko_turn_mean_over_games_with_ko": mean(first_ko),
        "first_ko_turn_median": sorted(first_ko)[len(first_ko) // 2] if first_ko else None,
        "player_turns": nt,
        "turns_attack_legal_share": mean(t["atkLegal"] for t in turns),
        "turns_attacked_share": mean(t["attacked"] for t in turns),
        "turns_attack_available_not_taken_share_of_all_turns": round(len(atk_not_taken) / nt, 3) if nt else None,
        "turns_attack_available_not_taken_share_of_available": round(len(atk_not_taken) / max(1, sum(t["atkLegal"] for t in turns)), 3),
        "turns_active_cannot_pay_share": mean(not t["activeCanPay"] for t in turns),
        "turns_no_pokemon_in_play_can_pay_share": mean(not t["anyCanPay"] for t in turns),
        "check_attack_legal_but_active_cannot_pay": sum(1 for t in turns if t["atkLegal"] and not t["activeCanPay"]),
        "damage_per_turn_mean": mean(t["dmg"] for t in turns),
        "damage_per_attacking_turn_mean": mean(t["dmg"] for t in turns if t["attacked"]),
        "energy_attached_per_turn": mean(t["attach"] for t in turns),
        "retreats_per_turn": mean(t["retreat"] for t in turns),
        "evolutions_per_game": mean(sum(t["evolve"] for t in g["turns"]) for g in games),
        "healing_hp_per_game_heal_effect": mean(g["healTotal"] for g in games),
        "damage_removed_other_than_heal_per_game": mean(sum(t["otherDec"] for t in g["turns"]) for g in games),
        "heal_turns_share": mean(t["heal"] > 0 for t in turns),
        "time_ended_games": len(timed),
        "time_ended_prize_margin": dict(margins),
        "time_ended_margin_share": {k: round(v / len(timed), 3) for k, v in margins.items()} if timed else {},
        "draws": sum(1 for g in games if g["winner"] == 0),
    }


def ditto_check(games):
    """Ditto Slash into Scyther: base damage, and whether the same seat's Ditto copied Swords Dance on its previous turn."""
    rows = collections.Counter()
    for g in games:
        evs = g["attacks"]
        for i, e in enumerate(evs):
            if e["attacker"] == "Ditto" and e["attack"] == "Slash" and e["defender"] == "Scyther" and "base" in e:
                prior = any(p["seat"] == e["seat"] and p["attack"] == "Swords Dance" and p["attacker"] == "Ditto" and 0 < e["turn"] - p["turn"] <= 2
                            for p in evs[:i])
                rows[(e["base"], "after own Ditto Swords Dance" if prior else "no prior Swords Dance")] += 1
    return {f"base {b}, {why}": c for (b, why), c in sorted(rows.items())}


out = {}
for label in ("capped", "untimed"):
    f = OUT / f"trace_{label}.jsonl"
    if not f.exists():
        continue
    games = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    by = collections.defaultdict(list)
    for g in games:
        by[(g["seed"] - 1000) // 100000].append(g)
    out[label] = {"pooled": summarize(games), "ditto_slash_into_scyther": ditto_check(games),
                  "per_list": {f"P{di} {NAMES[di]}": summarize(gs) for di, gs in sorted(by.items())}}
(OUT / "trace_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for label, o in out.items():
    print("==", label)
    for k, v in o["pooled"].items():
        print(f"  {k}: {v}")
    print("  ditto:", o["ditto_slash_into_scyther"])
