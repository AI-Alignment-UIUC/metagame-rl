"""Compares the tournament runs of rl/tournament.py (log #59-62) on the same measures, from their logs only.

Per run: equilibrium size (absolute and as a share of N, mean and over the last 10 rounds), rounds with a
mixed equilibrium, cyclic triads (all and statistically clear), deck types and distances, drafting
(adoptions, exploratory adoptions, drafted share of each deck), deck shape and the archived field's staples
in the final decks (labels only), each agent against SimpleBot on its own deck, entropy coefficients, and
the run's health (games cut off at the step cap, agents short of their training budget).

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/tournament_report.py runs/tourn-3 runs/tourn-6 runs/tourn-9 runs/tourn-3-s2 [--json out.json]
"""
import argparse
import collections
import json
from pathlib import Path

import numpy as np


def summarize(run: Path) -> dict:
    rows = [json.loads(l) for l in open(run / "log.jsonl")]
    N = rows[0]["agents_n"]
    t = [r["tournament"] for r in rows]
    late = rows[-10:]
    sup = [len(x["support"]) for x in t]
    drafts = [d for r in rows for d in r.get("draft", [])]
    trains = [x for r in rows for x in r.get("train", [])]
    last = rows[-1]["decks"]
    evals = [r["eval_simplebot_own_deck"] for r in rows if "eval_simplebot_own_deck" in r]
    shape = {k: float(np.mean([d[k] for d in last])) for k in ("basic_energy", "pokemon", "trainer", "special_energy")}
    shape_late = {k: float(np.mean([d[k] for r in late for d in r["decks"]])) for k in ("basic_energy", "pokemon", "trainer")}
    return {
        "run": run.name, "agents": N, "rounds": len(rows) - 1,
        "support_size_mean": round(float(np.mean(sup)), 3),
        "support_frac_mean": round(float(np.mean([s / N for s in sup])), 3),
        "support_size_last10": round(float(np.mean(sup[-10:])), 3),
        "effective_support_frac_mean": round(float(np.mean([x["effective_support_frac"] for x in t])), 3),
        "mixed_rounds": int(sum(s > 1 for s in sup)),
        "cyclic_frac_mean": round(float(np.mean([x["cyclic_frac"] or 0 for x in t])), 4),
        "clear_cycles_total": int(sum(x["cyclic_triads"][1] for x in t)),
        "rounds_with_clear_cycle": int(sum(x["cyclic_triads"][1] > 0 for x in t)),
        "deck_types_final": rows[-1]["deck_types"], "deck_types_min": int(min(r["deck_types"] for r in rows)),
        "deck_distance_final": rows[-1]["deck_distance"],
        "standings_spread_final": round(float(np.ptp(t[-1]["standings"])), 3),
        "adoptions_per_agent_round": round(sum(d["adopted"] for d in drafts) / max(len(drafts), 1), 3),
        "exploratory_adoptions": int(sum(bool(d.get("exploratory")) for d in drafts)),
        "cards_changed_when_adopted_mean": round(float(np.mean([d["changed"] for d in drafts if d["adopted"]] or [0])), 1),
        "drafted_share_final": [d["drafted_share"] for d in last],
        "deck_shape_final_mean": {k: round(v, 1) for k, v in shape.items()},
        "deck_shape_last10_mean": {k: round(v, 1) for k, v in shape_late.items()},
        "field_share_final_mean": round(float(np.mean([d["field_share"] for d in last])), 3),
        "nearest_archived_overlap_max": max(d["nearest"][1] for d in last),
        "staples_in_final_decks": dict(collections.Counter(s for d in last for s in d["staples"])),
        "decks_with_any_staple": int(sum(bool(d["staples"]) for d in last)),
        "own_deck_vs_simplebot_mean_by_check": [round(float(np.mean([v["all"] for v in e.values()])), 3) for e in evals],
        "own_deck_vs_simplebot_range_by_check": [[round(min(v["all"] for v in e.values()), 3),
                                                  round(max(v["all"] for v in e.values()), 3)] for e in evals],
        "entropy_coef_final": [d.get("ent_coef") for d in last],
        "policy_entropy_last_iter": round(trains[-1]["entropy"], 3) if trains else None,
        "cut_off_games": int(sum(x["cut_off"] for x in trains)), "training_games": int(sum(x["games"] for x in trains)),
        "iterations_short_of_budget": int(sum(1 for x in trains if x.get("short_of_budget"))),
        "seconds_per_round": round(float(np.mean([sum(r["seconds"].values()) for r in rows[:-1]])), 1),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    out = [summarize(Path(r)) for r in args.runs if (Path(r) / "log.jsonl").exists()]
    keys = [k for k in out[0] if k != "run"]
    w = max(len(k) for k in keys)
    print(f"{'':{w}}  " + "  ".join(f"{o['run']:>22}" for o in out))
    for k in keys:
        print(f"{k:{w}}  " + "  ".join(f"{json.dumps(o[k]):>22}" for o in out))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
