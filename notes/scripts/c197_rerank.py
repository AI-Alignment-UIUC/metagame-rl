"""C197 (runs/probe/C197-judge-rerank/record.md): re-score every deck of a W population at 44 as the loop's selection does, under
three judges, and compare who'd be kept. Each deck plays field_sample = 4 decks of the same population (drawn once, seeded, the
same for every judge), --deals a pair with seats alternating, under the round rule 20-45; a deck's z is its mean round_score
(rl/train.py) over all its games, as the deck and as another's field. Judges: G1 greedy on deals set 1; G2 greedy on deals set 2
(the noise floor); H C194's two-turn search on both seats (c139_run.SEARCH, horizon 2) on deals set 1, paired with G1. The pilot
is W's own net from that snapshot, saved as {config, model} and checked to load exactly.
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c197_rerank.py --run C171-W-s48 --judge G1
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c197_rerank.py --read
C202 (runs/probe/C202-rerank-lists-like/record.md): --it N (another snapshot), --out-dir D (another record's folder), and --read
--runs A,B with the top quarter's median E, DCE, basic types and names, ΔE, and corr(z, E) beside C197's reads.
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c197_rerank.py --run C191-WL-s52 --it 44 --out-dir runs/probe/C202-rerank-lists-like --judge G1
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
from c139_run import SEARCH                             # noqa: E402
from rl.decks import Pool                               # noqa: E402

OUT = ROOT / "runs/probe/C197-judge-rerank"
IT = 44                                                  # C202: --it, the snapshot re-scored (and the pilot taken from it)
POOL = Pool()
ST = {c["fullName"]: c["superType"] for c in POOL.cards}
FIELD, FIELD_SEED = 4, 1970
DEAL_SEED = {"G1": 1971, "G2": 1972, "H": 1971}
H_SPEC = {**SEARCH, "horizon": 2}
ROUND = [20, 45]


def pilot(run):
    import torch
    from rl.gpu_matrix import load_policy
    st = torch.load(ROOT / f"runs/screens/{run}/population_it{IT:04d}.pt", map_location="cpu", weights_only=False)
    pf = OUT / f"pilot_{run}_it{IT}.pt"
    if not pf.exists():
        torch.save({"config": st["config"], "model": st["net"]}, pf)
    model, _ = load_policy(pf.relative_to(ROOT).as_posix(), "cpu")
    sd, net = model.state_dict(), st["net"]
    missing, extra = sorted(set(sd) - set(net)), sorted(set(net) - set(sd))
    diff = max((float((sd[k].float() - net[k].float()).abs().max()) for k in sd if k in net and sd[k].numel()), default=0.0)
    return pf, st["population"], {"missing": len(missing), "extra": len(extra), "max_diff": diff}


def field_pairs(n):
    rng = np.random.default_rng(FIELD_SEED)
    return [(d, int(f)) for d in range(n) for f in rng.choice([e for e in range(n) if e != d], FIELD, replace=False)]


def hold(log, t0):
    import queue_c90 as Q
    while True:
        if time.time() - t0 > 75 * 60:
            log("KILL: stage past 75 minutes"); sys.exit(4)
        if Q.GPU_PAUSE.exists():
            log("GPU-PAUSE: stopping at a chunk boundary"); sys.exit(5)
        free, _ = Q.loop.ram_gb()
        g = Q.loop.gpu_mem()
        if free >= 2 and g and g[0] <= 0.8 * g[1]:
            return
        log(f"holding: free RAM {free:.1f} GB, GPU {g}")
        time.sleep(60)


def run(a):
    from rl import limits
    from rl.gpu_matrix import GpuMatrix, load_policy
    from rl.remote import RemotePool
    OUT.mkdir(exist_ok=True)

    def log(s):
        line = time.strftime("%Y-%m-%d %H:%M:%S ") + s
        print(line, flush=True)
        with open(OUT / "log.txt", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    pf, pop, chk = pilot(a.run)
    log(f"{a.run} pilot load: {chk}")
    if chk["missing"] or chk["extra"] or chk["max_diff"] > 0:
        log("KILL: the net doesn't load exactly"); sys.exit(3)
    if a.pilot:                                          # C197 Amendment 1: another pilot (C49-sd) on the same decks, field and deals
        pf, chk = ROOT / a.pilot, {"pilot": a.pilot}
    decks = [{"name": f"{a.run} #{x['id']}", "cards": list(x["deck"])} for x in pop]
    if a.add_lists:                                      # C203 (a): the 24 lists added to the population, scored, never trained on
        from rl.decks import archived_decks
        decks += [{"name": f"LIST {n}", "cards": POOL.names(v)} for n, v in archived_decks(POOL)]
    n = len(decks) if not a.limit else a.limit
    pairs = [p for p in field_pairs(len(decks)) if p[0] < n]
    keys = [d * FIELD + k % FIELD for k, (d, _) in enumerate(pairs)]
    part = ""
    if a.part:                                           # C202: part K of N of the pairs (keys from the full list), for 30-minute stages
        k_, n_ = (int(x) for x in a.part.split("/"))
        lo, hi = (k_ - 1) * len(pairs) // n_, k_ * len(pairs) // n_
        pairs, keys, part = pairs[lo:hi], keys[lo:hi], f"_part{k_}of{n_}"
    workers = limits.cap_workers(a.workers)
    limits.apply(a.device, workers)
    model, _ = load_policy(pf.relative_to(ROOT).as_posix(), a.device)
    rp = RemotePool(workers)
    rp.pace = 0.25
    t0, res, errs, games, lines, capped = time.time(), [], 0, 0, 0, 0
    spec = {**H_SPEC, **({"maxSteps": a.max_steps} if a.max_steps else {}), **({"trace": True} if a.trace else {})}   # C202 Amendment 3
    trace = {"lineSteps": {}, "cappedKeys": {}}
    tag = ("_C49" if a.pilot else "") + ("_lists" if a.add_lists else "")
    f = OUT / f"{a.run}_{a.judge}{tag}{'_limit' + str(a.limit) if a.limit else ''}{part}{'_ms' + str(a.max_steps) if a.max_steps else ''}.json"

    def save(done):
        f.write_text(json.dumps({"run": a.run, "judge": a.judge, "deals": a.deals, "deal_seed": DEAL_SEED[a.judge], "field_seed": FIELD_SEED,
                                 "search": spec if a.judge == "H" else None, "pilot_check": chk, "games": games, "errors": errs,
                                 **({"trace": trace} if a.trace else {}),
                                 "lines": lines, "capped": capped, "seconds": round(time.time() - t0, 1), "complete": done, "results": res}),
                     encoding="utf-8")
    try:
        gm = GpuMatrix.attach(model, rp, workers, device=a.device)
        for c0 in range(0, len(pairs), a.chunk):
            hold(log, t0)
            ps, ks = pairs[c0:c0 + a.chunk], keys[c0:c0 + a.chunk]
            gm.play(decks, a.deals, DEAL_SEED[a.judge], pairs=ps, pair_keys=ks, round_turns=ROUND, search=spec if a.judge == "H" else None)
            errs += gm.last["errors"]; games += gm.last["games"]
            st = gm.last.get("search") or {}
            lines += st.get("lines", 0); capped += st.get("capped", 0)
            for q in trace:
                for k, v in (st.get(q) or {}).items():
                    trace[q][k] = trace[q].get(k, 0) + v
            res += [{"i": r["i"], "j": r["j"], "iSeat": r["iSeat"], "winner": r["winner"], "ending": r.get("ending"), "error": bool(r.get("error"))}
                    for r in gm.results]
            save(False)
            log(f"{a.run} {a.judge}: pairs {c0}-{c0 + len(ps) - 1} done, {gm.last['games']} games, {errs} errors, lines {lines}, "
                f"capped {capped} ({capped / max(lines, 1):.1%}), {time.time() - t0:.0f} s so far")
            if errs > 0.02 * max(games, 1):
                log(f"KILL: errors {errs} of {games}"); sys.exit(2)
            if lines and capped / lines > 0.05:
                log(f"KILL: {capped} of {lines} lines cut by maxSteps"); sys.exit(6)
        save(True)
        log(f"{a.run} {a.judge}: {games} games, {errs} errors, {time.time() - t0:.0f} s -> {f.name}")
    finally:
        rp.close()


def zs(results, n, idx=None):
    from rl.train import round_score
    s, c = np.zeros(n), np.zeros(n)
    rows = results if idx is None else [results[k] for k in idx]
    for r in rows:
        for d, seat in ((r["i"], r["iSeat"]), (r["j"], 3 - r["iSeat"])):
            s[d] += round_score(r, seat, ROUND); c[d] += 1
    return np.where(c > 0, s / np.maximum(c, 1), np.nan)


def read(boot=200, runs=("C171-W-s48", "C171-W-s49")):
    import torch
    from collections import Counter
    card = {c["fullName"]: c for c in POOL.cards}
    out = {}
    for spec in runs:
        run, it = (spec.split(":")[0], int(spec.split(":")[1])) if ":" in spec else (spec, IT)   # C202: RUN:IT, each run's own snapshot
        pop = torch.load(ROOT / f"runs/screens/{run}/population_it{it:04d}.pt", map_location="cpu", weights_only=False)["population"]
        n = len(pop)
        pte = np.array([[sum(ST[c] == k for c in x["deck"]) for k in (1, 2, 3)] for x in pop])
        dce = np.array([list(x["deck"]).count("Double Colorless Energy BS") for x in pop])
        J = {}
        for j in ("G1", "G2", "H", "G1_C49", "H_C49"):
            fp = OUT / f"{run}_{j}.json"
            if fp.exists():
                d = json.loads(fp.read_text(encoding="utf-8"))
                if d.get("complete"):
                    J[j] = d["results"]
            else:                                        # C202: a judge run in parts, read once every part is complete
                parts = sorted(OUT.glob(f"{run}_{j}_part*of*.json"))
                ds = [json.loads(x.read_text(encoding="utf-8")) for x in parts]
                if parts and all(d.get("complete") for d in ds) and len(parts) == int(parts[0].stem.split("of")[-1]):
                    J[j] = [r for d in ds for r in d["results"]]
                for x in sorted(OUT.glob(f"{run}_{j}_ms*.json")):   # C202 Amendment 3: H rerun at a higher maxSteps (the highest complete one)
                    d = json.loads(x.read_text(encoding="utf-8"))
                    if d.get("complete"):
                        J[j] = d["results"]
        if not J:
            continue
        o, top = {}, {}
        rng = np.random.default_rng(0)
        for j, r in J.items():
            z = zs(r, n)
            top[j] = set(np.argsort(-np.nan_to_num(z, nan=-1))[:25].tolist())
            corr = float(np.corrcoef(z, pte[:, 1])[0, 1])
            corr_e = float(np.corrcoef(z, pte[:, 2])[0, 1])
            bz = [zs(r, n, rng.integers(len(r), size=len(r))) for _ in range(boot)]
            bs = [np.corrcoef(b, pte[:, 1])[0, 1] for b in bz]
            be = [np.corrcoef(b, pte[:, 2])[0, 1] for b in bz]
            tq = sorted(top[j])
            o[j] = {"top25_median_pte": np.median(pte[tq], 0).tolist(), "corr_z_T": round(corr, 4),
                    "corr_se": round(float(np.nanstd(bs, ddof=1)), 4), "games": len(r),
                    "corr_z_E": round(corr_e, 4), "corr_E_se": round(float(np.nanstd(be, ddof=1)), 4),          # C202
                    "top25_dce_a_deck": round(float(dce[tq].mean()), 2),
                    "top25_basics": dict(Counter(c for k in tq for c in pop[k]["deck"] if ST[c] == 3 and card[c]["energyType"] == 0).most_common()),
                    "top25_pokemon": dict(Counter(card[c]["name"] for k in tq for c in pop[k]["deck"] if ST[c] == 1).most_common(12))}
        rng2, B = np.random.default_rng(1), {j: [] for j in J}    # C202 Amendment 2: the top quarter's mean P/T/E, decks and games resampled
        for _ in range(boot):
            didx = rng2.integers(n, size=n)
            for j, r in J.items():
                zb = zs(r, n, rng2.integers(len(r), size=len(r)))[didx]
                B[j].append(pte[didx[np.argsort(-np.nan_to_num(zb, nan=-1))[:25]]].mean(0))
        for j in J:
            o[j]["top25_mean_pte"] = np.round(pte[sorted(top[j])].mean(0), 3).tolist()
            o[j]["top25_mean_pte_se"] = np.round(np.std(B[j], axis=0, ddof=1), 3).tolist()
        if "G1" in J:
            for j in ("G2", "H"):
                if j in J:
                    d = np.array(B[j]) - np.array(B["G1"])
                    o[f"mean_dT_{j}"] = round(o[j]["top25_mean_pte"][1] - o["G1"]["top25_mean_pte"][1], 3)
                    o[f"mean_dE_{j}"] = round(o[j]["top25_mean_pte"][2] - o["G1"]["top25_mean_pte"][2], 3)
                    o[f"mean_dT_{j}_se"], o[f"mean_dE_{j}_se"] = round(float(d[:, 1].std(ddof=1)), 3), round(float(d[:, 2].std(ddof=1)), 3)
            if "H" in J and "G2" in J:                   # Amendment 2: mean dT_H - mean dT_G = mean T(H's top) - mean T(G2's top)
                d = np.array(B["H"])[:, 1] - np.array(B["G2"])[:, 1]
                o["mean_dT_H_minus_G"] = round(o["H"]["top25_mean_pte"][1] - o["G2"]["top25_mean_pte"][1], 3)
                o["mean_dT_H_minus_G_se"] = round(float(d.std(ddof=1)), 3)
        if "G1" in J:
            for j in ("G2", "H"):
                if j in J:
                    o[f"dT_{j}"] = o[j]["top25_median_pte"][1] - o["G1"]["top25_median_pte"][1]
                    o[f"dE_{j}"] = o[j]["top25_median_pte"][2] - o["G1"]["top25_median_pte"][2]          # C202
                    o[f"overlap_{j}_G1"] = len(top[j] & top["G1"])
                    o[f"changes_{j}_vs_G1"] = 25 - len(top[j] & top["G1"])     # research: H's reshuffle against G2's (the noise floor)
            if "H" in J and "G2" in J:
                o["overlap_H_G2"] = len(top["H"] & top["G2"])
        if "G1_C49" in J and "H_C49" in J:                   # Amendment 1: C49-sd's dT_H on the same decks and deals
            o["dT_H_C49"] = o["H_C49"]["top25_median_pte"][1] - o["G1_C49"]["top25_median_pte"][1]
            o["overlap_H_G1_C49"] = len(top["H_C49"] & top["G1_C49"])
        out[run] = o
    (OUT / "read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


def read_lists(runs):
    """C203 (a): per run and judge, over the population plus the 24 lists: the lists in the top quarter (31 of 123, by z) and their
    mean z rank (1 the best), against the loop's decks; bootstrap SE over games for the count."""
    import torch
    out = {}
    for spec in runs:
        run, it = (spec.split(":")[0], int(spec.split(":")[1])) if ":" in spec else (spec, IT)
        n_pop = len(torch.load(ROOT / f"runs/screens/{run}/population_it{it:04d}.pt", map_location="cpu", weights_only=False)["population"])
        o = {}
        for j in ("G1", "G2"):
            fp = OUT / f"{run}_{j}_lists.json"
            if not fp.exists():
                continue
            d = json.loads(fp.read_text(encoding="utf-8"))
            if not d.get("complete"):
                continue
            r, n = d["results"], n_pop + 24
            z = zs(r, n)
            order = np.argsort(-np.nan_to_num(z, nan=-1))
            rank = np.empty(n, dtype=int); rank[order] = np.arange(1, n + 1)
            q = round(n / 4)
            rng = np.random.default_rng(2)
            boot = [int(sum(k >= n_pop for k in np.argsort(-np.nan_to_num(zs(r, n, rng.integers(len(r), size=len(r))), nan=-1))[:q])) for _ in range(200)]
            o[j] = {"decks": n, "top_quarter": q, "lists_in_top_quarter": int(sum(k >= n_pop for k in order[:q])), "count_se": round(float(np.std(boot, ddof=1)), 2),
                    "lists_mean_rank": round(float(rank[n_pop:].mean()), 1), "loop_mean_rank": round(float(rank[:n_pop].mean()), 1),
                    "lists_mean_z": round(float(np.nanmean(z[n_pop:])), 4), "loop_mean_z": round(float(np.nanmean(z[:n_pop])), 4),
                    "top10": [("LIST" if k >= n_pop else "loop") for k in order[:10]], "games": len(r), "errors": d["errors"]}
        out[run] = o
    (OUT / "read_lists.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--judge", choices=["G1", "G2", "H"])
    ap.add_argument("--deals", type=int, default=6, help="deals a (deck, field deck) pair, even so seats balance")
    ap.add_argument("--chunk", type=int, default=100, help="pairs a chunk (25 decks)")
    ap.add_argument("--limit", type=int, default=0, help="the first N decks only (the timed pilot)")
    ap.add_argument("--max-steps", type=int, default=0, help="C202 Amendment 3: H's maxSteps (0: C139's 40)")
    ap.add_argument("--trace", action="store_true", help="C202 Amendment 3: steps per line by Trainer count, keys in capped lines")
    ap.add_argument("--part", default="", help="C202: K/N, the K-th of N equal slices of the pairs (merged by --read)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--pilot", default="", help="C197 Amendment 1: a pilot other than W's own (runs/pilot/C49-sd/model_it00199.pt)")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--add-lists", action="store_true", help="C203 (a): the 24 lists added to the population (123 decks)")
    ap.add_argument("--read-lists", action="store_true", help="C203 (a): the lists' count in the top quarter and mean z rank")
    ap.add_argument("--it", type=int, default=44, help="C202: the snapshot (population_it{N}.pt) and its pilot")
    ap.add_argument("--out-dir", default="", help="C202: another record's folder")
    ap.add_argument("--runs", default="C171-W-s48,C171-W-s49", help="C202: --read these runs, RUN or RUN:IT")
    a = ap.parse_args()
    global OUT, IT
    IT = a.it
    if a.out_dir:
        OUT = ROOT / a.out_dir
    if a.read:
        return read(runs=tuple(a.runs.split(",")))
    if a.read_lists:
        return read_lists(runs=tuple(a.runs.split(",")))
    run(a)


if __name__ == "__main__":
    main()
