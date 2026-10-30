"""Flow probe summary (follow-up to C115): runs/probe/C115-goldfish/flow/<pilot>_P<list>_s<seed>.jsonl from goldfish_games2.py -> flow/summary.json and a table.
Per attacker and list: Energy in hand without an attach, draws, Oak/Bill held, attack choice and damage vs printed, benches and Defender HP, opening hand and
mulligans against the hypergeometric expectation for the list, plus list 1's Wigglytuff (Do the Wave, PlusPower) block. The attacker is seat 1 on an odd seed, seat 2 on an even one.
Run: .venv/Scripts/python.exe notes/scripts/audit/summarize_flow.py [--seed 91]"""
import argparse, json
from math import comb
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=91)
args = ap.parse_args()
ROOT = Path.cwd()
OUT = ROOT / "runs/probe/C115-goldfish/flow"
PILOTS = ["simplebot", "arm0", "start"]
decks = json.loads((ROOT / "runs/probe/BENCH/decks_P.json").read_text(encoding="utf-8"))
pool = {c["fullName"]: c for c in json.loads((ROOT / "notes/data/cards/pool.json").read_text(encoding="utf-8"))["cards"]}
r = lambda x, k=3: None if x is None else round(x, k)
mean = lambda x: sum(x) / len(x) if x else None
share = lambda n, d: n / d if d else None


def expect(di):
    cs = [pool[c] for c in decks[di]["cards"]]
    B = sum(1 for c in cs if c["superType"] == 1 and c["stage"] == 2)      # Pokemon, Basic stage (Fossil and Doll are Trainers)
    E = sum(1 for c in cs if c["superType"] == 3)
    return {"name": decks[di]["name"], "basics": B, "energy": E, "exp_basics_in_7": 7 * B / 60, "exp_energy_in_7": 7 * E / 60,
            "p_no_basic_in_7": comb(60 - B, 7) / comb(60, 7)}


def summarize(games, di):
    rows, gs_rows, op = [], [], {"attacker": [], "goldfish": []}
    for g in games:
        gf = 2 if g["seed"] % 2 == 0 else 1
        at = 3 - gf
        rows += [t for t in g["turns"] if t["p"] == at]
        for who, pid in (("attacker", at), ("goldfish", gf)):
            s = (g.get("setup") or {}).get(str(pid))
            if s: op[who].append(s)
    n = len(rows)
    eh = [t for t in rows if t["eH"] > 0]
    ds = [t["dS"] for t in rows if t["dS"] is not None]
    ob = [t for t in rows if t["ob"] > 0]
    atk = [(t, t["A"][0]) for t in rows if t["A"]]
    multi = [(t, a) for t, a in atk if a["np"] >= 2]
    hit = [(t, a) for t, a in atk if a["pd"] > 0]
    plain = [(t, a) for t, a in hit if a["plain"]]
    res = {"games": len(games), "attacker_own_turns": n,
           "energy_in_hand_turns_share": r(share(len(eh), n)), "energy_in_hand_no_attach_share_of_those": r(share(sum(1 for t in eh if t["att"] == 0), len(eh))),
           "energy_in_hand_no_attach_share_of_all_turns": r(share(sum(1 for t in eh if t["att"] == 0), n)),
           "turn_draw_per_own_turn": r(mean(ds)), "turn_draw_counts": {str(k): ds.count(k) for k in sorted(set(ds))},
           "trainer_draw_per_own_turn": r(mean([t["dT"] for t in rows])),
           "oak_bill_held_turns_share": r(share(len(ob), n)), "oak_bill_held_not_played_share_of_held": r(share(sum(1 for t in ob if t["obp"] == 0), len(ob))),
           "oak_bill_held_not_played_share_of_all_turns": r(share(sum(1 for t in ob if t["obp"] == 0), n)),
           "attack_decisions": len(atk), "multi_option_decisions": len(multi), "multi_highest_damage_share": r(share(sum(1 for _, a in multi if a["top"]), len(multi))),
           "hits_printed_gt0": len(hit), "mean_printed_damage": r(mean([a["pd"] for _, a in hit]), 1), "mean_expected_after_WR_PP": r(mean([a["exp"] for _, a in hit]), 1),
           "mean_damage_dealt": r(mean([t["dmg"] for t, _ in hit]), 1),
           "plain_hits": len(plain), "plain_dealt_equals_expected_share": r(share(sum(1 for t, a in plain if t["dmg"] == a["exp"]), len(plain))),
           "plain_mean_dealt_minus_expected": r(mean([t["dmg"] - a["exp"] for t, a in plain]), 2),
           "mean_attacker_bench_at_attack": r(mean([a["bA"] for _, a in atk]), 2), "mean_goldfish_bench_at_attack": r(mean([a["bD"] for _, a in atk]), 2),
           "mean_defender_hp_printed": r(mean([a["hp"] for _, a in atk if a["hp"] is not None]), 1), "mean_defender_hp_remaining": r(mean([a["rem"] for _, a in atk if a["rem"] is not None]), 1),
           "pluspower_played_per_attack": r(share(sum(t["ppP"] for t, _ in atk), len(atk)))}
    for who, ss in op.items():
        res["opening_" + who] = {"hands": len(ss), "first_basics": r(mean([s["first"]["b"] for s in ss])), "first_energy": r(mean([s["first"]["e"] for s in ss])),
                                 "mulligan_rate": r(share(sum(1 for s in ss if s["draws"] > 1), len(ss))), "mulligans_per_game": r(mean([s["draws"] - 1 for s in ss])),
                                 "final_hand_basics": r(mean([s["last"]["b"] for s in ss])), "final_hand_energy": r(mean([s["last"]["e"] for s in ss]))}
    res["expected"] = expect(di)
    if di == 1:
        w = [(t, a) for t, a in atk if a["ac"] == "Wigglytuff JU" and a["an"] == "Do the Wave"]
        if w:
            res["wigglytuff"] = {"do_the_wave_attacks": len(w), "attacks_all_by_card": len(atk),
                "bench_dist": {str(k): sum(1 for _, a in w if a["bA"] == k) for k in range(6)}, "mean_bench": r(mean([a["bA"] for _, a in w]), 2),
                "mean_dealt": r(mean([t["dmg"] for t, _ in w]), 1),
                "mean_expected_10_plus_10_per_bench_before_WR": r(mean([10 + 10 * a["bA"] for _, a in w]), 1),
                "dealt_equals_expected_before_WR_share": r(share(sum(1 for t, a in w if t["dmg"] == 10 + 10 * a["bA"]), len(w)), 3),
                "mean_expected_after_WR_PP": r(mean([a["exp"] for _, a in w]), 1),
                "mean_expected_with_bench_after_WR_noPP": r(mean([max(0, (10 + 10 * a["bA"]) * a["mult"] + a["mod"]) for _, a in w]), 1),
                "dealt_equals_expected_incl_bench_PP_WR_share": r(share(sum(1 for t, a in w if t["dmg"] == max(0, (10 + 10 * a["bA"] + 10 * a["pp"]) * a["mult"] + a["mod"] - 20 * a["df"])), len(w)), 3),
                "pluspower_played_per_wigglytuff_attack": r(share(sum(t["ppP"] for t, _ in w), len(w)), 3),
                "attacks_with_pluspower_attached_share": r(share(sum(1 for _, a in w if a["pp"] > 0), len(w)), 3),
                "item_finder_returned_pluspower_total": sum(t["ifPP"] for t in rows), "item_finder_returned_pluspower_per_game": r(sum(t["ifPP"] for t in rows) / len(games), 3),
                "ko_in_one_hit_70hp_share": r(share(sum(1 for t, a in w if a["hp"] == 70 and a["rem"] == 70 and t["kos"] > 0), len(w)), 3),
                "ko_70hp_any_share": r(share(sum(1 for t, a in w if a["hp"] == 70 and t["kos"] > 0), len(w)), 3),
                "defender_70hp_fresh_share": r(share(sum(1 for _, a in w if a["hp"] == 70 and a["rem"] == 70), len(w)), 3),
                "five_benched_share": r(share(sum(1 for _, a in w if a["bA"] == 5), len(w)), 3)}
    return res


out = {}
for p in PILOTS:
    out[p] = {}
    for di in range(4):
        f = OUT / f"{p}_P{di}_s{args.seed}.jsonl"
        if f.exists(): out[p][f"P{di} {decks[di]['name']}"] = summarize([json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()], di)
(OUT / "summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for p in PILOTS:
    for k, v in out[p].items():
        e = v["expected"]; a = v["opening_attacker"]; g = v["opening_goldfish"]
        print(f"{p:9s} {k[:28]:28s} | Eh-noatt {v['energy_in_hand_no_attach_share_of_those']} (of {v['energy_in_hand_turns_share']}) | draw {v['turn_draw_per_own_turn']}+{v['trainer_draw_per_own_turn']} "
              f"| OB held-unplayed {v['oak_bill_held_not_played_share_of_held']} ({v['oak_bill_held_turns_share']}) | multi {v['multi_option_decisions']}/{v['attack_decisions']} top {v['multi_highest_damage_share']} "
              f"| dealt {v['mean_damage_dealt']} exp {v['mean_expected_after_WR_PP']} pr {v['mean_printed_damage']} plain= {v['plain_dealt_equals_expected_share']} "
              f"| bench {v['mean_attacker_bench_at_attack']} gf {v['mean_goldfish_bench_at_attack']} hp {v['mean_defender_hp_printed']}/{v['mean_defender_hp_remaining']} "
              f"| open B {a['first_basics']} (exp {e['exp_basics_in_7']:.2f}) E {a['first_energy']} (exp {e['exp_energy_in_7']:.2f}) mull {a['mulligan_rate']} (exp {e['p_no_basic_in_7']:.3f}) | gf mull {g['mulligan_rate']} B {g['first_basics']} E {g['first_energy']}")
        if "wigglytuff" in v: print("   wiggly", v["wigglytuff"])
