"""C193 (runs/probe/C193-lists-swap-depth/record.md, Amendment 1): the 24 lists L against 8 saved variants per list per direction,
L-T (4 of the list's Trainer copies, drawn uniformly over its copies, out for 4 of its commonest basic Energy) and L+T (4 of that
Energy out for 4 copies of the list's own Trainer names with room under the limit, drawn uniformly over those names). ar/fixed.py's M
machinery (notes/scripts/search_m.py: the lists' share of decisive games, deals keyed by the list so every variant of a list and
both players see the same deals, seats alternating, the round rule), pilot C49-sd on both seats. Players: greedy, and C135's S-V
search exactly as C139 ran it (c139_run.SEARCH: top 3 plus every legal Trainer play, dets 2, CRN, horizon 1, scored by V).
Gate cell (Amendment 1, run first): each list against itself, the search seat against a greedy seat (deck slot 1, whose search
never triggers: a searchKey no option has, so PolicySearchAgent plays the policy's best move at every decision).
Chunks of lists, so the row-73 and GPU-PAUSE holds and the 75-minute stage limit are checked between them.
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c193_run.py --stage gate --seed 1
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c193_run.py --stage cells --seed 1 --players greedy,search
    PYTHONPATH=. .venv/Scripts/python notes/scripts/c193_run.py --read
"""
import argparse
import collections
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ar"))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import fixed                                            # noqa: E402
from c139_run import SEARCH                             # noqa: E402
from rl.decks import Pool                               # noqa: E402

OUT = ROOT / "runs/probe/C193-lists-swap-depth"
PILOT = "runs/pilot/C49-sd/model_it00199.pt"            # the same weights as ar/data/start.pt (126 of 126 tensors, max difference 0.0)
GAME_SEED = {1: 1931, 2: 1932}
VAR_SEED = {1: 19301, 2: 19302}
N_VAR, SWAP = 8, 4
POOL = Pool()
ST = {c["fullName"]: c["superType"] for c in POOL.cards}
BARE = {c["fullName"]: c["name"] for c in POOL.cards}
NEVER = "__c193_greedy__"                               # no option key starts with this
C139_SEARCH = {"k": 3, "dets": 2, "maxSteps": 40, "crn": True, "trainerOnly": True, "allTrainers": True}


DECKS = {"from": None, "top": 24}                        # C196: --decks-from a population, its top N by recent_score


def lists():
    if DECKS["from"]:
        return loop_decks(DECKS["from"], DECKS["top"])
    ev = json.loads((fixed.DATA / "eval_decks.json").read_text(encoding="utf-8"))
    idx = sorted({p[0] for p in ev["pairs"]})
    return [ev["decks"][i] for i in idx]


def loop_decks(path, top):
    """C196: a population's decks ranked by recent_score (the run's own mean z this window, else the last), skipping a deck
    with fewer than 4 Trainers or fewer than 4 of its commonest basic Energy (C193's swaps need both), next in rank instead."""
    import torch
    from rl.metagame import recent_score
    pop = torch.load(ROOT / path, map_location="cpu", weights_only=False)["population"]
    out = []
    for a in sorted(pop, key=lambda a: -recent_score(a, 0.0)):
        cards = list(a["deck"])
        en = [c for c in cards if POOL.basic_energy[POOL.id[c]]]
        tr = [c for c in cards if ST[c] == 2]
        names = collections.Counter(BARE[c] for c in tr)
        if len(tr) < SWAP or not en or max(en.count(e) for e in set(en)) < SWAP or sum(4 - k for k in names.values() if k < 4) < SWAP:
            continue                                     # taken by default: also no room under the limit for L+T's 4 copies
        out.append({"name": f"{Path(path).parent.name} #{a['id']} z {recent_score(a, 0.0):.3f}", "cards": cards})
        if len(out) == top:
            break
    assert len(out) == top, f"only {len(out)} usable decks in {path}"
    return out


def variants(L, seed):
    """Per list, N_VAR L-T and N_VAR L+T decks, with what moved; every deck checked legal."""
    if DECKS.get("c199"):                                # C201's arms (dce1, dce2) beside C199's, on the same decks and deal keys
        return c199_variants(L, seed)[0] + c201_variants(L, seed)[0]
    rng = np.random.default_rng(seed)
    out = []
    for li, d in enumerate(L):
        cards = list(d["cards"])
        energy = [c for c in cards if POOL.basic_energy[POOL.id[c]]]
        top = max(sorted(set(energy)), key=energy.count)
        tr = [c for c in cards if ST[c] == 2]
        for v in range(N_VAR):
            pick = sorted(rng.choice(len(tr), SWAP, replace=False).tolist())
            out_names = [tr[i] for i in pick]
            new = list(cards)
            for c in out_names:
                new.remove(c)
            new += [top] * SWAP
            out.append({"list": li, "dir": "minus", "v": v, "out": out_names, "in": [top] * SWAP, "cards": new})
        for v in range(N_VAR):
            assert energy.count(top) >= SWAP, f"{d['name']}: fewer than {SWAP} of {top}"
            new = list(cards)
            for _ in range(SWAP):
                new.remove(top)
            added = []
            for _ in range(SWAP):
                counts = {}
                for c in new:
                    if ST[c] == 2:
                        counts[BARE[c]] = counts.get(BARE[c], 0) + 1
                room = sorted(n for n, k in counts.items() if k < 4)
                if not room:
                    break
                name = room[int(rng.integers(len(room)))]
                prints = [c for c in cards if ST[c] == 2 and BARE[c] == name]
                c = max(sorted(set(prints)), key=prints.count)    # the list's own commonest printing of that name
                new.append(c)
                added.append(c)
            out.append({"list": li, "dir": "plus", "v": v, "out": [top] * SWAP, "in": added, "cards": new})
    if DECKS["from"]:                                    # C196 Amendment 1: L+T', 4 of that Energy out for 4 Trainer copies drawn
        pool = start_trainers(DECKS["from"])             # uniformly over the names in the run's population_it0000, under the limit
        for li, d in enumerate(L):
            cards = list(d["cards"])
            energy = [c for c in cards if POOL.basic_energy[POOL.id[c]]]
            top = max(sorted(set(energy)), key=energy.count)
            for v in range(N_VAR):
                new = list(cards)
                for _ in range(SWAP):
                    new.remove(top)
                added = []
                for _ in range(SWAP):
                    cnt = collections.Counter(BARE[c] for c in new if ST[c] == 2)
                    room = sorted(nm for nm in pool if cnt.get(nm, 0) < 4)
                    if not room:
                        break
                    nm = room[int(rng.integers(len(room)))]
                    new.append(pool[nm]); added.append(pool[nm])
                out.append({"list": li, "dir": "pplus", "v": v, "out": [top] * SWAP, "in": added, "cards": new})
    for x in out:
        x["legal"] = bool(POOL.legal(POOL.vector(x["cards"])))
    return out


def c199_variants(L, seed):
    """C199 (runs/probe/C199-offtype-replace/record.md): in each deck the k off-type basic Energy (matching none of its Pokemon's
    types) are replaced, same count, by (offa) basics of the deck's most-needed type (most typed cost symbols over its Pokemon's
    attacks, copy-weighted), one deterministic deck copied over the 8 deal sets; or (offb) copies of its own Trainer names with
    room, C193's L+T rule, 8 variants. Decks with k = 0 get none (counted)."""
    rng, rng_c = np.random.default_rng(seed), np.random.default_rng(seed + 7)
    card = {c["fullName"]: c for c in POOL.cards}
    btype = {c["fullName"]: next(i for i, v in enumerate(c["provides"]) if v) for c in POOL.cards if c["superType"] == 3 and c["energyType"] == 0}
    basic_of = {}
    for f, t in sorted(btype.items()):
        basic_of.setdefault(t, f)
    out, K = [], {}
    for li, d in enumerate(L):
        cards = list(d["cards"])
        ptypes = {t for c in cards if ST[c] == 1 for t, v in enumerate(card[c]["types"]) if v and t != 0}
        off = [c for c in cards if c in btype and btype[c] not in ptypes]
        K[li] = len(off)
        if not off:
            continue
        need = collections.Counter()
        for c in cards:
            if ST[c] == 1:
                for a in card[c].get("attacks") or []:
                    for t, v in enumerate(a["cost"]):
                        if t and v:
                            need[t] += v
        base = list(cards)
        for c in off:
            base.remove(c)
        t = max(sorted(need), key=need.get) if need else None
        if t in basic_of:
            for v in range(N_VAR):
                out.append({"list": li, "dir": "offa", "v": v, "out": off, "in": [basic_of[t]] * len(off), "cards": base + [basic_of[t]] * len(off)})
        for v in range(N_VAR):
            new, added = list(base), []
            for _ in range(len(off)):
                counts = collections.Counter(BARE[c] for c in new if ST[c] == 2)
                room = sorted(n for n, k in counts.items() if k < 4)
                if not room:
                    break
                name = room[int(rng.integers(len(room)))]
                prints = [c for c in cards if ST[c] == 2 and BARE[c] == name]
                c = max(sorted(set(prints)), key=prints.count)
                new.append(c); added.append(c)
            if len(added) == len(off):
                out.append({"list": li, "dir": "offb", "v": v, "out": off, "in": added, "cards": new})
        if t in basic_of and len(off) >= 3:                  # C199 Amendment 1 (c): k - 2 most-needed basics + 2 own Trainer copies
            for v in range(N_VAR):                           # (its own rng, so offa and offb stay as they were; k < 3 left out)
                new, added = base + [basic_of[t]] * (len(off) - 2), []
                for _ in range(2):
                    counts = collections.Counter(BARE[c] for c in new if ST[c] == 2)
                    room = sorted(n for n, k in counts.items() if k < 4)
                    if not room:
                        break
                    name = room[int(rng_c.integers(len(room)))]
                    prints = [c for c in cards if ST[c] == 2 and BARE[c] == name]
                    c = max(sorted(set(prints)), key=prints.count)
                    new.append(c); added.append(c)
                if len(added) == 2:
                    out.append({"list": li, "dir": "offc", "v": v, "out": off, "in": [basic_of[t]] * (len(off) - 2) + added, "cards": new})
    for x in out:
        x["legal"] = bool(POOL.legal(POOL.vector(x["cards"])))
    return out, K



DCE = "Double Colorless Energy BS"


def c201_variants(L, seed):
    """C201 (runs/probe/C201-dce-density/record.md): 2 basics out, the deck's commonest off-type basics where it has at least 2
    (they pay only Colourless, as DCE does; src "off"), else its commonest basics (src "main", reported apart); in, (dce1, arm e)
    1 DCE plus 1 copy of its own Trainer names with room (C193's L+T rule), 8 variants; (dce2, arm f) 2 DCE, one deck over the
    8 deal sets. Decks at 4 DCE (e), at 3 or more (f), or with fewer than 2 basics are left out and counted. Its own rng, so
    C199's arms don't move."""
    rng = np.random.default_rng(seed + 11)
    card = {c["fullName"]: c for c in POOL.cards}
    btype = {c["fullName"]: next(i for i, v in enumerate(c["provides"]) if v) for c in POOL.cards if c["superType"] == 3 and c["energyType"] == 0}
    out, skip = [], collections.Counter()
    for li, d in enumerate(L):
        cards = list(d["cards"])
        basics = [c for c in cards if c in btype]
        if len(basics) < 2:
            skip["fewer than 2 basics"] += 1
            continue
        ptypes = {t for c in cards if ST[c] == 1 for t, v in enumerate(card[c]["types"]) if v and t != 0}
        off = [c for c in basics if btype[c] not in ptypes]
        src = "off" if len(off) >= 2 else "main"
        cnt = collections.Counter(off if src == "off" else basics)
        gone = sorted(cnt.elements(), key=lambda c: (-cnt[c], c))[:2]
        base = list(cards)
        for c in gone:
            base.remove(c)
        n_dce = cards.count(DCE)
        if n_dce >= 4:
            skip["e: 4 DCE"] += 1
        else:
            for v in range(N_VAR):
                counts = collections.Counter(BARE[c] for c in base if ST[c] == 2)
                room = sorted(n for n, k in counts.items() if k < 4)
                if not room:
                    skip["e: no Trainer room"] += 1
                    break
                name = room[int(rng.integers(len(room)))]
                prints = [c for c in cards if ST[c] == 2 and BARE[c] == name]
                t = max(sorted(set(prints)), key=prints.count)
                out.append({"list": li, "dir": "dce1", "v": v, "src": src, "out": gone, "in": [DCE, t], "cards": base + [DCE, t]})
        if n_dce >= 3:
            skip["f: 3 or more DCE"] += 1
        else:
            for v in range(N_VAR):
                out.append({"list": li, "dir": "dce2", "v": v, "src": src, "out": gone, "in": [DCE, DCE], "cards": base + [DCE, DCE]})
    for x in out:
        x["legal"] = bool(POOL.legal(POOL.vector(x["cards"])))
    return out, dict(skip)

def start_trainers(path):
    """C196 Amendment 1: the Trainer names in the run's population_it0000.pt, each with its commonest printing there."""
    import torch
    pop = torch.load(ROOT / Path(path).parent / "population_it0000.pt", map_location="cpu", weights_only=False)["population"]
    prints = collections.Counter(c for a in pop for c in a["deck"] if ST[c] == 2)
    by = {}
    for c, k in prints.most_common():
        by.setdefault(BARE[c], c)
    return by


def hold(log, t_stage=None):
    """Row 73 and GPU-PAUSE, at every chunk boundary: wait while free RAM is under 2 GB or GPU memory over 80%; on GPU-PAUSE, stop.
    The record's 75-minute stage kill is checked while holding too (#991: a held stage could otherwise never reach it)."""
    import queue_c90 as Q
    while True:
        if t_stage is not None and time.time() - t_stage > 75 * 60:
            log("KILL: stage past 75 minutes while holding")
            sys.exit(4)
        if Q.GPU_PAUSE.exists():
            log("GPU-PAUSE: stopping at a chunk boundary")
            sys.exit(5)
        free, _ = Q.loop.ram_gb()
        g = Q.loop.gpu_mem()
        if free >= 2 and g and g[0] <= 0.8 * g[1]:
            return
        log(f"holding: free RAM {free:.1f} GB, GPU {g}")
        time.sleep(60)


RUN = {"horizon": 1, "maxSteps": None, "gate_vs": "greedy", "device": "cuda", "cap_kill": None}   # C194: --horizon, --max-steps, --gate-vs h1, --device
# C206 (runs/probe/C206-draw-mask-price/record.md): C205's draw and search Trainers, masked at test time only (--draw-mask N)
DRAW_NAMES = ["Professor Oak", "Bill", "Computer Search", "Gambler", "Item Finder", "Computer Error", "Challenge!"]


def run(stage, seed, players, games, chunk, workers, limit, dirs=("minus", "plus")):
    import torch                                        # noqa: F401
    from rl import limits
    from rl.gpu_matrix import GpuMatrix, load_policy
    from rl.remote import RemotePool
    assert SEARCH == C139_SEARCH, f"search spec {SEARCH} isn't C139's {C139_SEARCH}"
    spec = {**SEARCH, **({"horizon": RUN["horizon"]} if RUN["horizon"] != 1 else {}), **({"maxSteps": RUN["maxSteps"]} if RUN["maxSteps"] else {})}
    lines = capped = 0
    dm = RUN.get("draw_mask")
    assert not dm or players == ["greedy"] and stage == "cells", "C206's mask is for greedy cells only (the search runner isn't masked)"
    dmt = {q: 0 for q in ("asked", "main", "low", "masked", "removed", "empty")}
    tag = f"-{RUN['tag']}" if RUN.get("tag") else ""
    OUT.mkdir(exist_ok=True)
    logf = OUT / "log.txt"

    def log(s):
        line = time.strftime("%Y-%m-%d %H:%M:%S ") + s
        print(line, flush=True)
        with open(logf, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    L = lists()[: limit or None]
    V = variants(lists(), VAR_SEED[seed])
    vf = OUT / f"variants_s{seed}.json"
    if vf.exists():                                      # C199 Amendment 1: a new arm may be added; the old ones must not move
        was = {(x["list"], x["dir"], x["v"]): x["cards"] for x in json.loads(vf.read_text(encoding="utf-8"))}
        now = {(x["list"], x["dir"], x["v"]): x["cards"] for x in V}
        moved = [k for k, c in was.items() if now.get(k) != c]
        if moved:
            log(f"KILL: {len(moved)} saved variants differ from the rebuilt ones, e.g. {moved[0]}")
            sys.exit(3)
        if set(now) - set(was):
            vf.write_text(json.dumps(V, indent=1), encoding="utf-8")
    else:
        vf.write_text(json.dumps(V, indent=1), encoding="utf-8")
    bad = [x for x in V if not x["legal"] or len(x["in"]) != (len(x["out"]) if DECKS.get("c199") else SWAP)]
    if bad:
        log(f"KILL: {len(bad)} illegal or short variants, e.g. {bad[0]['list']} {bad[0]['dir']} {bad[0]['v']}")
        sys.exit(3)
    V = [x for x in V if x["list"] < len(L)]
    device = RUN["device"]
    workers = limits.cap_workers(workers)
    limits.apply(device, workers)
    model, _ = load_policy(PILOT, device)
    rp = RemotePool(workers)
    rp.pace = 0.25
    t_stage = time.time()
    try:
        gm = GpuMatrix.attach(model, rp, workers, device=device)
        for player in (["gate"] if stage == "gate" else players):
            res, meta, errs, n_games, t0 = [], [], 0, 0, time.time()
            label = player if stage == "gate" or len(dirs) > 1 else f"{player}-{dirs[0]}"
            f = OUT / f"{stage}_{label}{tag}_s{seed}{'_limit' + str(limit) if limit else ''}.json"

            def save(complete):                          # after every chunk, so a kill keeps the finished lists
                f.write_text(json.dumps({"stage": stage, "player": player, "dirs": list(dirs), "seed": seed, "game_seed": GAME_SEED[seed], "games_a_pair": games,
                                         "pilot": PILOT, "search": spec if player != "greedy" else None, "gate_vs": RUN["gate_vs"] if stage == "gate" else None,
                                         "lines": lines, "capped": capped, "games": n_games, "errors": errs,
                                         **({"tag": RUN["tag"]} if tag else {}), **({"draw_mask": dm, "draw_mask_counts": dmt} if dm else {}),
                                         "seconds": round(time.time() - t0, 1), "complete": complete, "results": res}), encoding="utf-8")
            for c0 in range(0, len(L), chunk):
                hold(log, t_stage)
                if time.time() - t_stage > 75 * 60:
                    log(f"KILL: stage past 75 minutes at {player}, lists from {c0}")
                    sys.exit(4)
                ids = list(range(c0, min(c0 + chunk, len(L))))
                if stage == "gate":
                    decks = [L[i] for i in ids] + [{"name": L[i]["name"] + " (greedy seat)", "cards": L[i]["cards"]} for i in ids]
                    n = len(ids)
                    pairs = [(k, n + k) for k in range(n)]
                    pm = [{"i": k, "j": n + k, "list": ids[k]} for k in range(n)]
                    kw = {"slots": [0] * n + [1] * n, "models": {0: model, 1: model},
                          "search": {**spec, "bySlot": {1: {"searchKey": NEVER} if RUN["gate_vs"] == "greedy" else {"horizon": 1, "maxSteps": SEARCH["maxSteps"]}}}}
                else:
                    vs = [x for x in V if x["list"] in ids and x["dir"] in dirs]
                    decks = [L[i] for i in ids] + [{"name": f"{L[x['list']]['name']} {x['dir']} {x['v']}", "cards": x["cards"]} for x in vs]
                    n = len(ids)
                    pairs = [(ids.index(x["list"]), n + q) for q, x in enumerate(vs)]
                    pm = [{"i": ids.index(x["list"]), "j": n + q, "list": x["list"], "dir": x["dir"], "v": x["v"],
                           "out": [BARE[c] for c in x["out"]] if x["dir"] == "minus" else []} for q, x in enumerate(vs)]
                    kw = {"search": spec if player == "search" else None}
                keys = [ids[i] for i, _ in pairs] if not DECKS.get("c199") else [m["list"] * N_VAR + m["v"] for m in pm]
                gm.play(decks, games, GAME_SEED[seed], pairs=pairs, pair_keys=keys,
                        round_turns=fixed.GAME["roundTurns"], **kw, **({"trainer_play": True} if RUN.get("trainer_play") else {}),
                        **({"draw_mask": dm} if dm else {}))
                errs += gm.last["errors"]
                for q in dmt:
                    dmt[q] += (gm.last.get("drawMask") or {}).get(q, 0)
                st = gm.last.get("search") or {}
                lines += st.get("lines", 0); capped += st.get("capped", 0)
                n_games += gm.last["games"]
                for r in gm.results:
                    m = next(m for m in pm if (m["i"], m["j"]) == (r["i"], r["j"]))
                    res.append({**{k: m[k] for k in m if k not in ("i", "j")}, "iSeat": r["iSeat"], "winner": r["winner"], "seed": r["seed"],
                                "error": bool(r.get("error")), "ending": r.get("ending"), **({"tplaySeat": r.get("tplaySeat"), "turnSeat": r.get("turnSeat")} if RUN.get("trainer_play") else {}),
                                **({"turns": r.get("turns")} if dm else {})})
                log(f"{stage} s{seed} {player}: lists {ids[0]}-{ids[-1]} done, {gm.last['games']} games, {gm.last['errors']} errors, "
                    f"lines {lines}, capped {capped} ({capped / max(lines, 1):.1%}), "
                    f"{time.time() - t0:.0f} s so far" + (f", mask {dmt}" if dm else ""))
                save(False)
                if dm and dmt["empty"]:                    # C206's kill: the mask must never leave a decision without a legal action
                    save(False)
                    log(f"KILL: the mask would have left {dmt['empty']} decisions without a legal action")
                    sys.exit(7)
                if errs > 0.02 * max(n_games, 1):
                    log(f"KILL: errors {errs} of {n_games}, over 2%")
                    sys.exit(2)
                if RUN["cap_kill"] and lines and capped / lines > RUN["cap_kill"]:
                    save(False)
                    log(f"KILL: {capped} of {lines} lines cut by maxSteps, over {RUN['cap_kill']:.0%}")
                    sys.exit(6)
            save(True)
            log(f"{stage} s{seed} {player}: {n_games} games, {errs} errors, {time.time() - t0:.0f} s -> {f.name}")
    finally:
        rp.close()


LIMIT_READ = False                                      # --read-pilot reads the timed pilot's files instead


def read():
    out = {}
    for f in sorted(x for x in OUT.glob("*.json") if x.stem.startswith(("gate_", "cells_")) and ("_limit" in x.stem) == LIMIT_READ):
        d = json.loads(f.read_text(encoding="utf-8"))
        r = d["results"]
        key = f"{d['stage']}_{d['player']}{'-' + d['tag'] if d.get('tag') else ''}_s{d['seed']}" + ("" if d.get("complete", True) else "_partial")
        if d["stage"] == "gate":
            won = {}; dec = {}
            for x in r:
                if x["winner"] in (1, 2):
                    dec[x["list"]] = dec.get(x["list"], 0) + 1
                    won[x["list"]] = won.get(x["list"], 0) + (x["winner"] == x["iSeat"])
            v = np.array([won.get(k, 0) / dec[k] for k in dec])
            out[key] = {"M_search_seat": round(float(v.mean()), 4), "se": round(float(v.std(ddof=1) / np.sqrt(len(v))), 4), "lists": len(v),
                        "games": d["games"], "errors": d["errors"], "seconds": d["seconds"]}
            continue
        for dr in ("minus", "plus", "pplus", "offa", "offb", "offc", "dce1", "dce2"):
            won, dec, name_won, name_dec = {}, {}, {}, {}
            for x in r:
                if x["dir"] != dr or x["winner"] not in (1, 2):
                    continue
                w = x["winner"] == x["iSeat"]
                dec[x["list"]] = dec.get(x["list"], 0) + 1
                won[x["list"]] = won.get(x["list"], 0) + w
                for n in set(x.get("out") or []):
                    name_dec[n] = name_dec.get(n, 0) + 1
                    name_won[n] = name_won.get(n, 0) + w
            sh = {k: won.get(k, 0) / dec[k] for k in dec}
            if len(sh) < 2:
                continue
            v = np.array(list(sh.values()))
            var_w, vn, within = 0.0, {}, {}                  # Amendment 3: lists fixed, variants random
            for x in r:
                if x["dir"] == dr and x["winner"] in (1, 2):
                    a = vn.setdefault((x["list"], x["v"]), [0, 0]); a[0] += x["winner"] == x["iSeat"]; a[1] += 1
            for li in sh:
                pv = np.array([w / n for (l2, _), (w, n) in vn.items() if l2 == li and n])
                if len(pv) > 1:
                    var_w += pv.var(ddof=1) / len(pv)
            if dr == "minus":                                # Amendment 3: a name read within the lists that hold it
                for li in sh:
                    names = {n for x in r if x["dir"] == "minus" and x["list"] == li for n in (x.get("out") or [])}
                    held = {n for n in names}
                    for n in held:
                        g = {True: [0, 0], False: [0, 0]}
                        for x in r:
                            if x["dir"] == "minus" and x["list"] == li and x["winner"] in (1, 2):
                                k = n in (x.get("out") or []); g[k][0] += x["winner"] == x["iSeat"]; g[k][1] += 1
                        if g[True][1] and g[False][1]:
                            e = within.setdefault(n, {"lists": 0, "dec_with": 0, "won_with": 0, "diff": []})
                            e["lists"] += 1; e["dec_with"] += g[True][1]; e["won_with"] += g[True][0]
                            e["diff"].append(g[True][0] / g[True][1] - g[False][0] / g[False][1])
            nfix = len(sh)
            out[f"{key}_{dr}"] = {"M": round(float(v.mean()), 4), "se_lists_fixed": round(float(np.sqrt(var_w) / nfix), 4),
                                  "se_over_lists": round(float(v.std(ddof=1) / np.sqrt(len(v))), 4), "lists": len(v),
                                  **({"within_list_name": {n: {"lists": e["lists"], "share_with": round(e["won_with"] / e["dec_with"], 4), "decisive_with": e["dec_with"],
                                                               "diff_mean": round(float(np.mean(e["diff"])), 4)} for n, e in sorted(within.items())}} if dr == "minus" else {}),
                                  "decisive": int(sum(dec.values())), "by_list": {str(k): round(x, 4) for k, x in sorted(sh.items())},
                                  **({"by_removed_name": {n: [round(name_won[n] / name_dec[n], 4), name_dec[n]] for n in sorted(name_dec)}} if dr == "minus" else {}),
                                  "games": d["games"], "errors": d["errors"], "seconds": d["seconds"]}
    (OUT / "read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, {x: y for x, y in v.items() if x not in ("by_list", "by_removed_name", "within_list_name")})


def pooled():
    """C193's bands (Amendments 1, 3): each cell pooled over both seeds (mean of the seeds' M, SE from the lists-fixed SEs), read
    at 0.48 / 0.52 with each seed on the same side of 0.50; then C194's launch condition (R-pilot-value, or between with the
    search - greedy lift on M_minus under +0.02)."""
    r = json.loads((OUT / "read.json").read_text(encoding="utf-8"))
    cell = {}
    for pl in ("greedy", "search"):
        for dr in ("minus", "plus"):
            a, b = r.get(f"cells_{pl}_s1_{dr}"), r.get(f"cells_{pl}_s2_{dr}")
            if not (a and b):
                return print(f"not ready: cells_{pl}_s1/s2_{dr}")
            cell[(pl, dr)] = {"M": round((a["M"] + b["M"]) / 2, 4), "se": round(float(np.hypot(a["se_lists_fixed"], b["se_lists_fixed"]) / 2), 4),
                              "s1": a["M"], "s2": b["M"], "same_side": (a["M"] - 0.5) * (b["M"] - 0.5) > 0}
    low = lambda c: c["M"] < 0.48 and c["same_side"] and c["s1"] < 0.5
    high = lambda c: c["M"] >= 0.52 and c["same_side"] and c["s1"] > 0.5
    g, sr = cell[("greedy", "minus")], cell[("search", "minus")]
    band = ("R-depth" if low(g) and high(sr) else "R-pilot-value" if low(g) and low(sr) else "R-field" if high(g) and high(sr) else "between")
    opt = {pl: high(cell[(pl, "minus")]) and high(cell[(pl, "plus")]) for pl in ("greedy", "search")}
    lift = round(sr["M"] - g["M"], 4)
    launch = band == "R-pilot-value" or (band == "between" and lift < 0.02)
    out = {"cells": {f"{k[0]}_{k[1]}": v for k, v in cell.items()}, "band": band, "R_optimum": opt, "lift_minus": lift,
           "lift_se": round(float(np.hypot(g["se"], sr["se"])), 4), "C194_launch": launch}
    (OUT / "pooled.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["gate", "cells"])
    ap.add_argument("--seed", type=int, choices=[1, 2], default=1)
    ap.add_argument("--players", default="greedy,search")
    ap.add_argument("--dirs", default="minus,plus", help="minus, plus, and C196's pplus (L+T', loop decks only)")
    ap.add_argument("--out-dir", default="", help="C194: the record folder written to (default C193's)")
    ap.add_argument("--horizon", type=int, default=1, help="C194: the search's horizon on the searching seats")
    ap.add_argument("--max-steps", type=int, default=0, help="C194: a line's step cap (0: C139's 40)")
    ap.add_argument("--gate-vs", choices=["greedy", "h1"], default="greedy", help="C194: the gate's other seat, greedy or C139's horizon-1 search")
    ap.add_argument("--cap-kill", type=float, default=0, help="C194: stop if more than this share of lines is cut by maxSteps")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--trainer-play", action="store_true", help="C199's rule-9 check: per-seat Trainer play counts in plain (greedy) games")
    ap.add_argument("--decks-from", default="", help="C196: a population_it*.pt whose top --top decks replace the lists")
    ap.add_argument("--top", type=int, default=24)
    ap.add_argument("--c199", action="store_true", help="C199: the off-type basic replacements (dirs offa, offb, Amendment 1's offc), deals keyed by deck and variant")
    ap.add_argument("--games", type=int, default=14, help="deals a pair, even so seats balance")
    ap.add_argument("--draw-mask", type=int, default=-1, help="C206: mask DRAW_NAMES at main-phase decisions with the acting deck at or under N (evaluation only)")
    ap.add_argument("--draw-mask-dry", action="store_true", help="C206's M0: count what --draw-mask would mask, mask nothing")
    ap.add_argument("--pilot", default="", help="C206: the pilot file on both seats (default C49-sd)")
    ap.add_argument("--tag", default="", help="C206: a label in the cell file's name and read key (pilot and mask)")
    ap.add_argument("--chunk", type=int, default=6, help="lists a chunk")
    ap.add_argument("--workers", type=int, default=fixed.EVAL_WORKERS)
    ap.add_argument("--limit", type=int, default=0, help="the first N lists only (the timed pilot)")
    ap.add_argument("--variants-only", action="store_true")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--read-pilot", action="store_true")
    ap.add_argument("--pooled", action="store_true", help="C193's pooled bands and C194's launch condition, from read.json")
    a = ap.parse_args()
    global OUT
    if a.out_dir:
        OUT = ROOT / a.out_dir
    DECKS.update({"from": a.decks_from or None, "top": a.top, "c199": a.c199})
    RUN.update(trainer_play=a.trainer_play)
    RUN.update(tag=a.tag, draw_mask={"n": a.draw_mask, "names": DRAW_NAMES, "dry": a.draw_mask_dry} if a.draw_mask >= 0 else None)
    if a.pilot:
        global PILOT
        PILOT = a.pilot
    RUN.update(horizon=a.horizon, maxSteps=a.max_steps or None, gate_vs=a.gate_vs, device=a.device, cap_kill=a.cap_kill or None)
    if a.pooled:
        return pooled()
    if a.read or a.read_pilot:
        global LIMIT_READ
        LIMIT_READ = a.read_pilot
        return read()
    if a.variants_only:
        for s in (1, 2):
            V = variants(lists(), VAR_SEED[s])
            OUT.mkdir(exist_ok=True)
            (OUT / f"variants_s{s}.json").write_text(json.dumps(V, indent=1), encoding="utf-8")
            print(f"seed {s}: {len(V)} variants, illegal {sum(not x['legal'] for x in V)}, short {sum(len(x['in']) != SWAP for x in V)}")
        return
    run(a.stage, a.seed, a.players.split(","), a.games, a.chunk, a.workers, a.limit, tuple(a.dirs.split(",")))


if __name__ == "__main__":
    main()
