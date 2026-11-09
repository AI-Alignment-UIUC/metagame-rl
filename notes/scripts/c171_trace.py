"""C171's trace read (runs/probe/C171-table-drafting/record.md, Amendment 1 item 4a; rule 9): how the 6 off-list names behave in games, against the printed card. Saved games keep no per-attack record, so these games are played for it: C165's factorial decks holding
a name, against a random deck of the same pod, under C127 s16, greedy, round rule [20, 45], through notes/scripts/audit/c171_trace_worker.js (log only). Reads per attack: uses, base damage values, conditions applied, hand changes, and impossible events.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c171_trace.py [--n 1200 --workers 2]
"""
import argparse
import collections
import json
import os
import random
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
import rl.remote as R                                                   # noqa: E402
from rl.decks import Pool                                               # noqa: E402
from rl.gpu_matrix import load_policy, history_of, chain_of, canon_of   # noqa: E402

D = ROOT / "runs/probe/C171-table-drafting"
NAMES = ("Tauros", "Lickitung", "Seaking", "Weepinbell", "Kangaskhan", "Snorlax")
PILOT = "runs/screens/C127-R1-K-paired-ledger-s16/checkpoint.pt"


def play(a, path):
    card = {c["fullName"]: c for c in Pool().cards}
    decks = json.loads((ROOT / "runs/probe/C165-trainer-factorial/decks.json").read_text(encoding="utf-8"))
    decks = [{"name": d["name"], "cards": d["cards"]} for d in decks]
    holders = {n: [k for k, d in enumerate(decks) if any(card[x]["name"] == n for x in d["cards"])] for n in NAMES}
    rng = random.Random(171)
    pick = [(rng.choice(holders[NAMES[k % len(NAMES)]]), rng.randrange(len(decks))) for k in range(a.n)]
    worker = str(ROOT / "notes/scripts/audit/c171_trace_worker.js")
    _popen = R.subprocess.Popen
    R.subprocess.Popen = lambda cmd, **kw: _popen(["node", worker], **kw)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _ = load_policy(PILOT, device)
    models = {0: model.eval()}
    path.unlink(missing_ok=True)
    os.environ["TRACE_OUT"] = str(path)
    jobs = [{"i": i, "j": j, "iSeat": 1 + (k % 2), "seed": 171 * 1000000 + k} for k, (i, j) in enumerate(pick) if i != j]
    shards = [jobs[w::a.workers] for w in range(a.workers)]
    msgs = [{"cmd": "games", "encoding": "tokens", "decks": decks, "jobs": s, "greedy": True, "concurrency": 16, "history": history_of(models), "chain": chain_of(models), "canon": canon_of(models),
             "slots": [0] * len(decks), "roundTurns": [20, 45]} for s in shards]
    pool = R.RemotePool(a.workers)
    t0 = time.time()
    try:
        reps = pool.collect(msgs, models, device)
    finally:
        pool.close()
    res = [x for r in reps for x in r["results"]]
    print("games", len(res), "errors", sum(1 for x in res if x.get("error")), "seconds", round(time.time() - t0), flush=True)


def read(path):
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    bare = lambda n: n.rsplit(" ", 1)[0] if n else n
    out = {}
    for n in NAMES:
        by = collections.defaultdict(list)
        for r in rows:
            if bare(r["ac"]) == n:
                by[r["an"]].append(r)
        out[n] = {}
        for an, rs in by.items():
            cond_new = lambda x, a, b: sum(1 for r in x if b in r and r[b] is not None and any(c not in (r[a] or []) for c in r[b]))
            added_d = collections.Counter(c for r in rs if r["condD1"] is not None for c in r["condD1"] if c not in r["condD0"])
            added_a = collections.Counter(c for r in rs if r["condA1"] is not None for c in r["condA1"] if c not in r["condA0"])
            on_snorlax = [r for r in rs if bare(r["dc"]) == "Snorlax"]
            out[n][an] = {"uses": len(rs), "base_values": dict(sorted(collections.Counter(str(r["base"]) for r in rs).items())),
                          "defender_conditions_added": dict(added_d), "attacker_conditions_added": dict(added_a),
                          "attacks_with_attacker_asleep_or_paralyzed": sum(1 for r in rs if any(c in (0, 2) for c in r["condA0"])),    # SpecialCondition: 0 Paralyzed, 1 Confused, 2 Asleep, 3 Poisoned
                          "hand_change": dict(sorted(collections.Counter(r["hand1"] - r["hand0"] for r in rs).items())), "deck_change": dict(sorted(collections.Counter(r["deck1"] - r["deck0"] for r in rs).items())),
                          "ko": sum(bool(r["ko"]) for r in rs),
                          "on_snorlax": {"uses": len(on_snorlax), "conditions_left_on_it": sum(bool(r["condD1"]) for r in on_snorlax)},
                          "damage_on_self_at_attack": dict(sorted(collections.Counter(str(r["dmgOnAttacker0"]) for r in rs).items())[:8])}
    # what happens to conditions on Snorlax when it's attacked by anything
    sn = [r for r in rows if bare(r["dc"]) == "Snorlax" and r["condD1"] is not None]
    allc = collections.Counter(str(c) for r in rows for c in (r["condD1"] or []))
    out["_all"] = {"attacks": len(rows), "conditions_seen_after_attacks": dict(allc), "attacks_on_snorlax": len(sn), "snorlax_with_a_condition_after": sum(bool(r["condD1"]) for r in sn),
                   "snorlax_with_a_condition_before": sum(bool(r["condD0"]) for r in sn),
                   "any_attacker_asleep_or_paralyzed": collections.Counter(str(c) for r in rows for c in r["condA0"]).most_common()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1200)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--read-only", action="store_true")
    a = ap.parse_args()
    path = D / "trace.jsonl"
    if not a.read_only:
        play(a, path)
    out = read(path)
    (D / "trace_read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for n, v in out.items():
        print(n, json.dumps(v)[:1500])


if __name__ == "__main__":
    main()
