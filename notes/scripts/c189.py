"""C189 driver (runs/probe/C189-specialist-dividend/record.md, Amendments 1-2): does a deck's gain from its own pilot rise with its Trainers?
  groups      --run C171-W-s49 --it 44   z-matched pairs -> H and L, 32 field decks, groups_<run>.json, matchups_<run>_{H,L}.json,
                                         pilot_<run>.pt ({config, model} of the population's net) and its load check
  train-cmds  --run C171-W-s49 --seed 1  prints the two bench_train.py commands (the budget in transitions: --arm-log of the first arm)
  cells       --run C171-W-s49 --pilot SH-s1=<pilot.pt> ...   M of each group's decks against the field per pilot (shared match check first)
  read        --run C171-W-s49           Gain, Dividend, Own - other (probability and logit), the bands, cells_<run>.csv
Evaluation only: nothing here trains or launches. `groups`, `read` and `cells --tiny` run on CPU.
  CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=".;notes/scripts" .venv/Scripts/python notes/scripts/c189.py groups --run C171-W-s49 --it 44
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "notes/scripts")]
from rl.decks import Pool, deck_shape  # noqa: E402

OUT = ROOT / "runs/probe/C189-specialist-dividend"
Z_TOL, T_GAP, T_MIN, T_MAX, PAIRS_WANT, PAIRS_MIN, FIELD_N, FIELD_SEED = 0.02, 6, 8, 40, 12, 8, 32, 189
ROUND_TURNS = [20, 45]        # the 2000 round rule, as ar/fixed.py GAME and g3_yardstick.py
DEAL_SEED = 189


def rel(p) -> str:
    return Path(p).resolve().relative_to(ROOT).as_posix()


# ---- groups ---------------------------------------------------------------------------------------------------------

def greedy_pairs(cands, cap: int):
    """Amendment 4: pairs among cands [(id, T, z)] inside the z limit, widest T gap first (then smallest |dz|, then ids); each id once."""
    valid = sorted(((-abs(a[1] - b[1]), abs(a[2] - b[2]), a[0], b[0]), a, b) for k, a in enumerate(cands) for b in cands[k + 1:]
                   if abs(a[2] - b[2]) <= Z_TOL + 1e-12 and abs(a[1] - b[1]) >= T_GAP)
    used, out = set(), []
    for _, a, b in valid:
        if len(out) >= cap:
            break
        if a[0] not in used and b[0] not in used:
            used |= {a[0], b[0]}
            out.append((a, b))
    return out


def load_check(pilot_file: Path, net: dict):
    from rl.gpu_matrix import load_policy
    model, _ = load_policy(rel(pilot_file), "cpu")
    sd = model.state_dict()
    missing, extra = sorted(set(sd) - set(net)), sorted(set(net) - set(sd))
    diff = max((float((sd[k].float() - net[k].float()).abs().max()) for k in sd if k in net and sd[k].numel()), default=0.0)
    return len(missing), len(extra), diff


def cmd_groups(a):
    src = ROOT / f"runs/screens/{a.run}/population_it{a.it:04d}.pt"
    st = torch.load(src, map_location="cpu", weights_only=False)
    pop, pool = st["population"], Pool()
    info = {}
    for x in pop:
        v = pool.vector(x["deck"])
        info[x["id"]] = {**deck_shape(pool, v), "z": float(x["last"]) if x.get("last") is not None else None,   # the newest decks have no z yet: not paired
                          "x": x,
                         "names": len({pool.name[pool.id[c]] for c in x["deck"]})}
    cands = [(i, d["trainer"], d["z"]) for i, d in sorted(info.items()) if T_MIN <= d["trainer"] <= T_MAX and d["z"] is not None]
    possible = greedy_pairs(cands, 10 ** 6)
    pairs = possible[:PAIRS_WANT]
    print(f"{a.run} it {a.it}: {len(pop)} decks, {len(cands)} with {T_MIN}-{T_MAX} Trainers and a z; greedy pairs possible {len(possible)}; taken {len(pairs)}")
    if len(pairs) < PAIRS_MIN:
        raise SystemExit(f"FAIL: {len(pairs)} pairs, under {PAIRS_MIN}")
    ph = [(p, q) if p[1] >= q[1] else (q, p) for p, q in pairs]
    H, L = [h for h, _ in ph], [l for _, l in ph]
    chosen = {c[0] for p in pairs for c in p}
    rest = sorted(i for i in info if i not in chosen)
    field = sorted(np.random.default_rng(FIELD_SEED).choice(rest, FIELD_N, replace=False).tolist()) if len(rest) >= FIELD_N else rest
    deck = lambda i: {"name": f"a{i}", "id": i, "parent": info[i]["x"]["parent"], "z": None if info[i]["z"] is None else round(info[i]["z"], 4),
                      "P": info[i]["pokemon"], "T": info[i]["trainer"], "E": info[i]["basic_energy"] + info[i]["special_energy"],
                      "cards": info[i]["x"]["deck"]}
    group = lambda ids: {"decks": [deck(c[0] if isinstance(c, tuple) else c) for c in ids]}
    gaps = [h[1] - l[1] for h, l in ph]
    g = {"run": a.run, "it": a.it, "pairs": len(pairs), "pairs_possible": len(possible), "T_gap_mean": round(float(np.mean(gaps)), 2), "T_gap_min": min(gaps),
         "H": group(H), "L": group(L), "field": group(field)}
    for k in "HL":
        ds = g[k]["decks"]
        g[k].update({"P": round(float(np.mean([d["P"] for d in ds])), 2), "T": round(float(np.mean([d["T"] for d in ds])), 2),
                     "E": round(float(np.mean([d["E"] for d in ds])), 2), "z": round(float(np.mean([d["z"] for d in ds])), 4),
                     "names_a_deck": round(float(np.mean([info[d["id"]]["names"] for d in ds])), 2), "n": len(ds)})
        print(f"  {k}: n {len(ds)} P {g[k]['P']} T {g[k]['T']} E {g[k]['E']} distinct names a deck {g[k]['names_a_deck']} mean z {g[k]['z']}; T {[d['T'] for d in ds]}")
    print(f"  field: {len(field)} decks, mean T {np.mean([info[i]['trainer'] for i in field]):.1f}, mean z {np.mean([info[i]['z'] for i in field if info[i]['z'] is not None]):.4f} ({sum(info[i]['z'] is None for i in field)} unscored)")
    print("  max |dz| in a pair", round(max(abs(h[2] - l[2]) for h, l in ph), 4), "T gap mean", g["T_gap_mean"], "min", g["T_gap_min"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"groups_{a.run}.json").write_text(json.dumps(g, indent=1), encoding="utf-8")
    fd = [{"name": d["name"], "cards": d["cards"]} for d in g["field"]["decks"]]
    for k in "HL":                                    # ordered pairs, as BENCH's 4 x 4: mirrors, cross pairs, and each against the field both ways
        gd = [{"name": d["name"], "cards": d["cards"]} for d in g[k]["decks"]]
        m = [[x, y] for x in gd for y in gd] + [[x, y] for x in gd for y in fd] + [[y, x] for x in gd for y in fd]
        (OUT / f"matchups_{a.run}_{k}.json").write_text(json.dumps(m), encoding="utf-8")
        print(f"  matchups_{a.run}_{k}.json: {len(m)} ({len(gd) ** 2} group, {2 * len(gd) * len(fd)} against the field)")
    pf = OUT / f"pilot_{a.run}.pt"
    torch.save({"config": st["config"], "model": st["net"]}, pf)
    print(f"  pilot {rel(pf)}: load_policy missing {{}} extra {{}} max param diff {{}}".format(*load_check(pf, st["net"])))


# ---- train-cmds -----------------------------------------------------------------------------------------------------

def arm_log_counts(log: Path):
    """(iterations, transitions) from a bench_train log's `it k games g T t ...` lines."""
    t = [int(m.group(1)) for m in re.finditer(r"^it \d+ games \d+ T (\d+)", log.read_text(encoding="utf-8", errors="replace"), re.M)]
    return len(t), sum(t)


def cmd_train_cmds(a):
    tag = a.run.split("-")[-1]
    first, second = ("H", "L") if a.first == "H" else ("L", "H")
    cmd = lambda k, extra: (f"PYTHONPATH=\".;notes/scripts\" .venv/Scripts/python notes/scripts/bench_train.py "
                            f"--name C189-S{k}-{tag} --seed {a.seed} {extra}--start {rel(OUT / f'pilot_{a.run}.pt')} --adam-warm 2 "
                            f"--matchups {rel(OUT / f'matchups_{a.run}_{k}.json')} --out-dir {rel(OUT)}/arm-S{k}-{tag}-s{a.seed} "
                            f"> {rel(OUT)}/arm-S{k}-{tag}-s{a.seed}.log 2>&1")
    n = "<N: iterations of the first arm>"
    if a.arm_log:
        its, tr = arm_log_counts(Path(a.arm_log))
        n = str(its)
        print(f"# first arm {a.arm_log}: {its} iterations, {tr} transitions (sum of the T column)")
    print(f"# arm 1 ({first}): 30 minutes sets the budget\n{cmd(first, '--minutes 30 ')}")
    print(f"# arm 2 ({second}): same iteration count N; --minutes 60 is only a stall cap. Then compare the T sums of the two logs\n"
          f"{cmd(second, f'--minutes 60 --iters {n} ')}")
    print("# bench_train's blocked() wants ar/PAUSE and an idle GPU; runs/GPU-PAUSE is Evan's, and these are printed, not run.")


# ---- cells ----------------------------------------------------------------------------------------------------------

def run_cell(gm, decks, n, m, games, models, slots, mode):
    from rl.gpu_matrix import GpuMatrix  # noqa: F401
    gm.greedy = mode == "greedy"
    pairs = [(i, n + j) for i in range(n) for j in range(m)]
    t0 = time.time()
    gm.play(decks, games, DEAL_SEED, pairs=pairs, pair_keys=[i * m + j for i in range(n) for j in range(m)], slots=slots, models=models,
            round_turns=ROUND_TURNS)
    wins, dec = np.zeros((n, m)), np.zeros((n, m))
    err, ends = 0, {}
    for r in gm.results:
        if r.get("error"):
            err += 1
            continue
        if r.get("ending"):
            ends[r["ending"]] = ends.get(r["ending"], 0) + 1
        if r["winner"] in (1, 2):
            dec[r["i"], r["j"] - n] += 1
            wins[r["i"], r["j"] - n] += r["winner"] == r["iSeat"]
    share = np.where(dec > 0, wins / np.maximum(dec, 1), np.nan)
    return {"wins": wins.tolist(), "decisive": dec.tolist(), "M_deck": np.nanmean(share, 1).tolist(), "errors": err,
            "games": len(gm.results), "endings": ends, "seconds": round(time.time() - t0, 1)}


def se(x):
    x = np.asarray(x, float)
    return float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else float("nan")


def cmd_cells(a):
    import torch
    from rl import limits
    from rl.gpu_matrix import GpuMatrix, load_policy
    from rl.remote import RemotePool
    g = json.loads((OUT / f"groups_{a.run}.json").read_text(encoding="utf-8"))
    nd, nf, games = (2, 2, 2) if a.tiny else (a.decks or g["pairs"], a.field, a.games)
    wpath = rel(OUT / f"pilot_{a.run}.pt")
    spec = {p.split("=")[0]: p.split("=")[1] for p in a.pilot}
    if a.tiny:
        spec = {"SH-s1": wpath, "SL-s1": wpath}
    device = "cpu" if (a.cpu or a.tiny) else ("cuda" if torch.cuda.is_available() else "cpu")
    workers = limits.cap_workers(2 if device == "cpu" else a.workers)
    limits.apply(device, workers)
    if device == "cpu":
        torch.set_num_threads(2)                      # 2 workers + 2 threads = the 4-thread budget
    field = g["field"]["decks"][:nf]
    models = {"shared": load_policy(wpath, device)[0]}
    models.update({k: load_policy(p if p != "W" else wpath, device)[0] for k, p in spec.items()})
    f = OUT / f"cells_{a.run}{'_tiny' if a.tiny else ''}.json"
    res = json.loads(f.read_text()) if f.exists() and not a.fresh else {"run": a.run, "tiny": a.tiny, "n_decks": nd, "n_field": nf, "games": games,
                                                                         "deal_seed": DEAL_SEED, "cells": {}}
    modes = ["sampled", "greedy"] if a.mode == "both" else [a.mode]
    rp = RemotePool(workers)
    try:
        gm = GpuMatrix.attach(models["shared"], rp, workers, device=device)
        order = [("shared", gr) for gr in "HL"] + [(p, gr) for p in spec for gr in "HL"]
        for pilot, gr in order:
            for mode in modes:
                key = f"{gr}|{pilot}|{mode}"
                if key in res["cells"]:
                    continue
                if a.match_only and pilot != "shared":
                    continue
                decks = [{"name": d["name"], "cards": d["cards"]} for d in g[gr]["decks"][:nd]] + [{"name": d["name"], "cards": d["cards"]} for d in field]
                # the group's decks under `pilot` (slot 1), the field always under W's shared pilot (slot 0)
                if pilot == "shared":
                    ms, sl = {0: models["shared"]}, None
                else:
                    ms, sl = {0: models["shared"], 1: models[pilot]}, [1] * nd + [0] * len(field)
                c = run_cell(gm, decks, nd, len(field), games, ms, sl, mode)
                res["cells"][key] = c
                print(f"{key}: M {np.mean(c['M_deck']):.4f} errors {c['errors']}/{c['games']} {c['seconds']}s", flush=True)
                f.write_text(json.dumps(res), encoding="utf-8")
            if pilot == "shared" and gr == "L":
                for mode in modes:
                    h, l = np.array(res["cells"][f"H|shared|{mode}"]["M_deck"]), np.array(res["cells"][f"L|shared|{mode}"]["M_deck"])
                    print(f"MATCH CHECK ({mode}, shared pilot): M(H) {h.mean():.4f}, M(L) {l.mean():.4f}, per-pair H - L {np.mean(h - l):+.4f} SE {se(h - l):.4f}", flush=True)
    finally:
        rp.close()
    # same pilot, two cells: the paired difference per deck (tiny: shared vs a copy of W in slot 1)
    if a.tiny:
        for mode in modes:
            for gr in "HL":
                x, y = res["cells"][f"{gr}|shared|{mode}"]["M_deck"], res["cells"][f"{gr}|SH-s1|{mode}"]["M_deck"]
                print(f"TINY paired difference {gr} {mode}: shared vs W-copy in slot 1 per deck {np.round(np.array(y) - np.array(x), 6).tolist()}")
    print(f"wrote {rel(f)}; total errors {sum(c['errors'] for c in res['cells'].values())}")


# ---- read -----------------------------------------------------------------------------------------------------------

def logit(m):
    m = np.clip(np.asarray(m, float), 0.01, 0.99)
    return np.log(m / (1 - m))


def band(div, div_se, gH, gL, oo, oo_se, other_ok=True):
    """The record's bands as amended (probability scale, both training seeds' mean)."""
    why = []
    if gH < 0 or gL < 0:
        why.append("a negative gain is unread, and the line does not close on it")
    if div >= 0.03 and div >= 2 * div_se and oo >= 0.02 and oo >= 2 * oo_se:
        return "R-bias", why
    if div <= -0.03 and -div >= 2 * div_se:
        return "R-reverse", why
    if 0 <= gH < 0.01 and 0 <= gL < 0.01:
        return "R-no-gap", why
    if abs(div) < 0.015 and max(gH, gL) >= 0.01:
        if div_se <= 0.01:
            return "R-no-bias", why
        return "between (R-no-bias's SE limit 0.01 not reached: SE %.4f)" % div_se, why
    return "between", why


def cmd_read(a):
    f = OUT / f"cells_{a.run}{'_tiny' if a.tiny else ''}.json"
    res = json.loads(f.read_text())
    cells = res["cells"]
    rows, summary = [], {}
    for mode in sorted({k.split("|")[2] for k in cells}):
        M = {(k.split("|")[0], k.split("|")[1]): np.array(v["M_deck"]) for k, v in cells.items() if k.endswith("|" + mode)}
        seeds = sorted({int(re.search(r"-s(\d+)$", p).group(1)) for (_, p) in M if p != "shared"})
        for (gr, pilot), m in sorted(M.items()):
            sh = M[(gr, "shared")]
            c = cells[f"{gr}|{pilot}|{mode}"]
            own = pilot[1] == gr if pilot != "shared" else None
            other = M.get((gr, f"S{'L' if gr == 'H' else 'H'}-{pilot.split('-')[-1]}")) if own else None
            d, dl = m - sh, logit(m) - logit(sh)
            row = {"run": res["run"], "mode": mode, "group": gr, "pilot": pilot, "n_decks": len(m), "n_field": res["n_field"],
                   "games_per_pair": res["games"], "games": c["games"], "errors": c["errors"], "decisive": int(np.sum(c["decisive"])),
                   "M": round(float(m.mean()), 4), "M_logit": round(float(logit(m).mean()), 4),
                   "d_vs_shared": round(float(d.mean()), 4), "d_vs_shared_se": round(se(d), 4),
                   "d_vs_shared_logit": round(float(dl.mean()), 4), "d_vs_shared_logit_se": round(se(dl), 4),
                   "own_minus_other": "" if other is None else round(float((m - other).mean()), 4),
                   "own_minus_other_se": "" if other is None else round(se(m - other), 4)}
            rows.append(row)
        S = {}
        for scale, tf in (("prob", lambda x: x), ("logit", logit)):
            if not seeds or any((g, f"S{s}-s{t}") not in M for g in "HL" for s in "HL" for t in seeds):
                continue
            gain = {g: np.mean([tf(M[(g, f"S{g}-s{t}")]) - tf(M[(g, "shared")]) for t in seeds], 0) for g in "HL"}
            oo = {g: np.mean([tf(M[(g, f"S{g}-s{t}")]) - tf(M[(g, f"S{'L' if g == 'H' else 'H'}-s{t}")]) for t in seeds], 0) for g in "HL"}
            div = gain["H"] - gain["L"]                       # paired by z-matched pair
            S[scale] = {"gain_H": float(gain["H"].mean()), "gain_H_se": se(gain["H"]), "gain_L": float(gain["L"].mean()), "gain_L_se": se(gain["L"]),
                        "dividend": float(div.mean()), "dividend_se": se(div), "own_minus_other_H": float(oo["H"].mean()), "own_minus_other_H_se": se(oo["H"]),
                        "own_minus_other_L": float(oo["L"].mean()), "own_minus_other_L_se": se(oo["L"]), "training_seeds": seeds}
            if scale == "prob" and len(div) > 2:
                drop = np.argsort(-(gain["H"]))[:2]
                S[scale]["dividend_drop_top2_H"] = float(np.delete(div, drop).mean())
        if "prob" in S:
            p = S["prob"]
            S["band"], S["flags"] = band(p["dividend"], p["dividend_se"], p["gain_H"], p["gain_L"], p["own_minus_other_H"], p["own_minus_other_H_se"])
        summary[mode] = S
    keys = list(rows[0])
    csv = OUT / f"cells_{a.run}{'_tiny' if a.tiny else ''}.csv"
    csv.write_text(",".join(keys) + "\n" + "\n".join(",".join(str(r[k]) for k in keys) for r in rows) + "\n", encoding="utf-8")
    (OUT / f"read_{a.run}{'_tiny' if a.tiny else ''}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print(f"wrote {rel(csv)} ({len(rows)} rows)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("groups")
    s.add_argument("--run", required=True)
    s.add_argument("--it", type=int, default=44)
    s = sub.add_parser("train-cmds")
    s.add_argument("--run", required=True)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--first", choices=["H", "L"], default="H")
    s.add_argument("--arm-log", help="the first arm's finished log: its iteration count goes into the second command")
    s = sub.add_parser("cells")
    s.add_argument("--run", required=True)
    s.add_argument("--pilot", nargs="*", default=[], help="SH-s1=<pilot.pt> SL-s1=<pilot.pt> ... (W = the shared pilot file)")
    s.add_argument("--decks", type=int, default=0)
    s.add_argument("--field", type=int, default=32)
    s.add_argument("--games", type=int, default=26, help="a deck-field pair (even: seats swap)")
    s.add_argument("--workers", type=int, default=6)
    s.add_argument("--mode", choices=["both", "sampled", "greedy"], default="both")
    s.add_argument("--match-only", action="store_true", help="only the shared-pilot cells and the match check")
    s.add_argument("--tiny", action="store_true", help="2 decks a group, 2 field decks, 2 games, W's pilot in every cell, CPU")
    s.add_argument("--cpu", action="store_true")
    s.add_argument("--fresh", action="store_true")
    s = sub.add_parser("read")
    s.add_argument("--run", required=True)
    s.add_argument("--tiny", action="store_true")
    a = ap.parse_args()
    {"groups": cmd_groups, "train-cmds": cmd_train_cmds, "cells": cmd_cells, "read": cmd_read}[a.cmd](a)


if __name__ == "__main__":
    main()
