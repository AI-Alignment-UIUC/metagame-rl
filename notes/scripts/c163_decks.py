"""C163 (runs/probe/C163-draw-deck-field/record.md; evaluation decks only): the crossed test's deck sets. L.json and R.json are the fields as
printed (the 24 lists; C162's 99 decks). L_base.json and R_base.json are their bases, every Oak, Bill and Gambler turned into the deck's commonest
basic Energy, each recording its source's name in "src" so it never meets it. c145_run.py then makes the copies (4 basic Energy into 2 Oak + 2 Bill).
--knockouts (C164, runs/probe/C164-list-knockout/record.md): T (a list's body, its non-draw Trainers uniform draws of the same count), C (a list's
body, each distinct non-draw Trainer mapped to a different uniform draw at its copy count), B (a list's Trainers, Pokemon from a wide deck of the
same Pokemon count, its Energy count from that deck's basic Energy) and K (concentrated wide decks in C162's bounds), all draw-free.
Asserts 60 legal cards, no draw cards in a base, and that a scramble differs from its list only in its knocked-out part.
--body-split (C169, runs/probe/C169-body-split/record.md; its own seed, so the files above don't change): E2 (the list's Pokemon, all its Energy on-type basics at the same total, split as the
printed list's basics are), S (the list's name, copy and stage pattern with new Pokemon, lines linked, Energy as E2 on the new types), G (a wide deck's Pokemon at the list's count, Energy as S), each
keeping the list's non-draw Trainers, 4 a list; and F, C127 s16's population at 29 as printed. One list holds Blastoise and Squirtle with no Wartortle, a Pokemon Breeder line; S keeps that skip as a link.
--table-bodies (C170, runs/probe/C170-table-bodies/record.md; seed 170): C169's G with each Pokemon pick weighted by exp(kappa * c / SD(c)), c being C165's coefficient for the name under that pilot (X: kappa 1, Y: kappa 3), for C127 s16 and s17.
--uniform-trainers (C170's Amendment 1; seed 1700): G, X and Y under s16 with their Trainers replaced by uniform draws over the non-draw Trainers at the same count, the copy limit kept.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c163_decks.py [--knockouts | --body-split | --table-bodies | --uniform-trainers]
"""
import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.decks import Pool, deck_shape, wide_deck  # noqa: E402

C163, C164, C169, C170 = ROOT / "runs/probe/C163-draw-deck-field", ROOT / "runs/probe/C164-list-knockout", ROOT / "runs/probe/C169-body-split", ROOT / "runs/probe/C170-table-bodies"
DRAW = ("Professor Oak", "Bill", "Gambler")
SCRAMBLES, N_K, SEED, K_BOUNDS = 4, 99, 163, ((12, 15), (26, 30), (16, 20))


def body_split(pool, card, lists):
    """C169's E2, S and G, and the drafted field F."""
    import torch
    rng = np.random.default_rng(169)
    ok = [c for c in pool.cards if pool.allowed[c["id"]]]
    prints = collections.defaultdict(list)
    for c in ok:
        prints[c["name"]].append(c["fullName"])
    mon = {c["name"]: c for c in ok if c["superType"] == 1}
    kids = collections.defaultdict(list)
    for n, c in mon.items():
        if c.get("evolvesFrom"):
            kids[c["evolvesFrom"]].append(n)
    energies = [c for c in ok if c["superType"] == 3 and c["energyType"] == 0]
    basics = sorted(n for n, c in mon.items() if c["stage"] == 2)
    draw = lambda x: card[x]["name"] in DRAW
    choice = lambda xs: xs[int(rng.integers(len(xs)))]

    def down(name, steps):                             # the names steps evolutions below a name
        out = [name]
        for _ in range(steps):
            out = [k for n in out for k in kids.get(n, [])]
        return out

    def structure(mons):
        """The list's names as a forest: copies, and each name's nearest ancestor in the list with the steps to it."""
        count = collections.Counter(card[x]["name"] for x in mons)
        nodes = {}
        for n in count:
            p, up = mon[n].get("evolvesFrom"), 1
            while p and p not in count and p in mon:
                p, up = mon[p].get("evolvesFrom"), up + 1
            nodes[n] = {"copies": count[n], "parent": p if p in count else None, "steps": up}
        return nodes

    def on_type(mons):
        types = {t for x in mons for t, v in enumerate(card[x]["types"]) if v}
        return [e["fullName"] for e in energies if any(e["provides"][t] for t in types)]

    def split(total, weights, kinds):
        """total basics over kinds: the weights, largest first, go to kinds in a random order, spare weights to the last kind, by largest remainder."""
        order = [kinds[int(i)] for i in rng.permutation(len(kinds))]
        w = sorted(weights, reverse=True)
        if len(w) > len(order):
            w = w[:len(order) - 1] + [sum(w[len(order) - 1:])]
        share = np.array(w, dtype=float) / sum(w) * total
        got = np.floor(share).astype(int)
        for i in np.argsort(-(share - got))[:total - int(got.sum())]:
            got[i] += 1
        return [e for e, k in zip(order, got) for _ in range(int(k))]

    def new_pokemon(nodes):
        """New names with the list's pattern: each root a Basic that can carry its line, each child drawn at its steps, all names distinct."""
        while True:
            used, out, fine = set(), {}, True

            def place(n, new):
                nonlocal fine
                used.add(new)
                out[n] = new
                for k, v in nodes.items():
                    if v["parent"] == n:
                        opts = [x for x in down(new, v["steps"]) if x not in used]
                        if not opts:
                            fine = False
                            return
                        place(k, choice(opts))
            for n, v in nodes.items():
                if v["parent"] is None:
                    if mon[n]["stage"] != 2:               # no root below Basic in these lists; kept general
                        opts = sorted(x for x, c in mon.items() if c["stage"] == mon[n]["stage"] and x not in used)
                    else:
                        opts = [b for b in basics if b not in used]
                    if not opts:
                        fine = False
                        break
                    place(n, choice(opts))
                if not fine:
                    break
            if fine and len(out) == len(nodes):
                cards = []
                for n, v in nodes.items():
                    cards += [choice(prints[out[n]])] * v["copies"]
                if on_type(cards):
                    return cards, out

    sets = {"E2": [], "S": [], "G": []}
    for d in lists:
        printed = d["cards"]
        mons = [x for x in printed if card[x]["superType"] == 1]
        keep = [x for x in printed if card[x]["superType"] == 2 and not draw(x)]
        total = 60 - len(mons) - len(keep)                 # the draw-free list's Energy, draw turned into Energy
        basics_printed = collections.Counter(x for x in printed if card[x]["superType"] == 3 and card[x]["energyType"] == 0)
        w = list(basics_printed.values())
        nodes = structure(mons)
        on = on_type(mons)
        assert all(x in on for x in basics_printed), d["name"]
        for r in range(SCRAMBLES):
            kinds = list(basics_printed)
            order = sorted(kinds, key=lambda e: -basics_printed[e])
            share = np.array([basics_printed[e] for e in order], dtype=float) / sum(w) * total
            got = np.floor(share).astype(int)
            for i in np.argsort(-(share - got))[:total - int(got.sum())]:
                got[i] += 1
            e2 = keep + mons + [e for e, k in zip(order, got) for _ in range(int(k))]
            sets["E2"].append({"name": f"E2{len(sets['E2'])}", "src": d["name"], "cards": e2})
            s_mons, mapped = new_pokemon(nodes)
            assert sorted(collections.Counter(card[x]["name"] for x in s_mons).values()) == sorted(v["copies"] for v in nodes.values())
            assert all(mon[mapped[n]]["stage"] == mon[n]["stage"] for n in nodes), (d["name"], mapped)
            sets["S"].append({"name": f"S{len(sets['S'])}", "src": d["name"], "cards": keep + s_mons + split(total, w, on_type(s_mons))})
            while True:
                g_mons = [x for x in pool.names(wide_deck(pool, rng)) if card[x]["superType"] == 1]
                if len(g_mons) == len(mons) and on_type(g_mons):
                    break
            sets["G"].append({"name": f"G{len(sets['G'])}", "src": d["name"], "cards": keep + g_mons + split(total, w, on_type(g_mons))})
    orphans = lambda cs: sum(1 for x in cs if card[x]["superType"] == 1 and card[x].get("evolvesFrom") and card[x]["evolvesFrom"] not in {card[y]["name"] for y in cs})
    for tag, ds in sets.items():
        for x in ds:
            cs = x["cards"]
            assert len(cs) == 60 and not any(draw(y) for y in cs) and pool.legal(pool.vector(cs)), x["name"]
            mons_here = [y for y in cs if card[y]["superType"] == 1]
            es = [y for y in cs if card[y]["superType"] == 3]
            assert all(card[y]["energyType"] == 0 for y in es), x["name"]         # no special Energy
            types = {t for y in mons_here for t, v in enumerate(card[y]["types"]) if v}
            assert all(any(card[y]["provides"][t] for t in types) for y in es), x["name"]   # on-type only
        print(f"{tag}: {len(ds)} decks, legal, 60 cards, no draw, no special Energy, on-type only; decks with an orphan evolution {sum(orphans(x['cards']) > 0 for x in ds)}")
    pop = torch.load(ROOT / "runs/screens/C127-R1-K-paired-ledger-s16/population_it0029.pt", map_location="cpu", weights_only=False)["population"]
    sets["F"] = [{"name": f"pop{p['id']}", "cards": list(p["deck"])} for p in pop]
    for tag, ds in sets.items():
        (C169 / f"{tag}.json").write_text(json.dumps(ds), encoding="utf-8")
    print(f"F: {len(sets['F'])} decks, C127 s16 at 29")


def table_bodies(pool, card, lists, tables=None, kappas=(("X", 1.0), ("Y", 3.0)), where=None, seed=170):
    """C170's X and Y for each C127 seed's table, with the draws each deck took; C171's gate passes its own tables, kappa, folder and seed."""
    rng = np.random.default_rng(seed)
    where = where or C170
    energies = [c for c in pool.cards if pool.allowed[c["id"]] and c["superType"] == 3 and c["energyType"] == 0]
    draw = lambda x: card[x]["name"] in DRAW
    if tables is None:
        got = json.loads((ROOT / "runs/probe/C165-trainer-factorial/summary.json").read_text(encoding="utf-8"))["pilots"]
        tables = {q: got[q]["pokemon"]["all"] for q in ("s16", "s17")}

    def on_type(mons):
        types = {t for x in mons for t, v in enumerate(card[x]["types"]) if v}
        return [e["fullName"] for e in energies if any(e["provides"][t] for t in types)]

    def split(total, weights, kinds):                  # as body_split's: the list's Energy shares, largest first, onto the new types in a random order
        order = [kinds[int(i)] for i in rng.permutation(len(kinds))]
        w = sorted(weights, reverse=True)
        if len(w) > len(order):
            w = w[:len(order) - 1] + [sum(w[len(order) - 1:])]
        share = np.array(w, dtype=float) / sum(w) * total
        got = np.floor(share).astype(int)
        for i in np.argsort(-(share - got))[:total - int(got.sum())]:
            got[i] += 1
        return [e for e, k in zip(order, got) for _ in range(int(k))]

    report = {}
    for pilot, coef in tables.items():
        sd = float(np.std(list(coef.values())))
        for tag, kappa in kappas:
            weight = {n: float(np.exp(kappa * c / sd)) for n, c in coef.items()}
            ds, tries, no_type, wrong_count, hardest = [], 0, 0, 0, 0
            for d in lists:
                printed = d["cards"]
                n_mons = sum(card[x]["superType"] == 1 for x in printed)
                keep = [x for x in printed if card[x]["superType"] == 2 and not draw(x)]
                total = 60 - n_mons - len(keep)
                w = list(collections.Counter(x for x in printed if card[x]["superType"] == 3 and card[x]["energyType"] == 0).values())
                for r in range(SCRAMBLES):
                    here = 0
                    while True:
                        here += 1
                        assert here < 200000, f"can't hit {n_mons} Pokemon for {d['name']} at {tag} {pilot}"
                        mons = [x for x in pool.names(wide_deck(pool, rng, name_weight=weight)) if card[x]["superType"] == 1]
                        if len(mons) != n_mons:
                            wrong_count += 1
                            continue
                        if not on_type(mons):
                            no_type += 1
                            continue
                        break
                    tries += here
                    hardest = max(hardest, here)
                    cards = keep + mons + split(total, w, on_type(mons))
                    assert len(cards) == 60 and not any(draw(y) for y in cards) and pool.legal(pool.vector(cards))
                    ds.append({"name": f"{tag}{pilot}.{len(ds)}", "src": d["name"], "cards": cards})
            (where / f"{tag}_{pilot}.json").write_text(json.dumps(ds), encoding="utf-8")
            report[f"{tag}_{pilot}"] = {"decks": len(ds), "wide_decks_drawn": tries, "rejected_wrong_count": wrong_count, "rejected_no_on_type_energy": no_type, "most_draws_for_one_deck": hardest}
            print(f"{tag} {pilot}: {report[f'{tag}_{pilot}']}")
    (where / "build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


def uniform_trainers(pool, card):
    rng = np.random.default_rng(1700)
    by_name = collections.defaultdict(list)
    for c in pool.cards:
        if pool.allowed[c["id"]] and c["superType"] == 2 and c["name"] not in DRAW:
            by_name[c["name"]].append(c["fullName"])
    names = sorted(by_name)
    for tag, src in (("Gu", C169 / "G.json"), ("Xu", C170 / "X_s16.json"), ("Yu", C170 / "Y_s16.json")):
        out = []
        for d in json.loads(src.read_text(encoding="utf-8")):
            keep = [x for x in d["cards"] if card[x]["superType"] != 2]
            used, new = collections.Counter(), []
            while len(new) < len(d["cards"]) - len(keep):
                m = names[int(rng.integers(len(names)))]
                if used[m] < 4:
                    used[m] += 1
                    new.append(by_name[m][int(rng.integers(len(by_name[m])))])
            cards = keep + new
            assert len(cards) == 60 and pool.legal(pool.vector(cards))
            out.append({"name": d["name"] + "u", "src": d["src"], "cards": cards})
        (C170 / f"{tag}_s16.json").write_text(json.dumps(out), encoding="utf-8")
        print(f"{tag}_s16: {len(out)} decks, legal")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uniform-trainers", action="store_true")
    ap.add_argument("--knockouts", action="store_true")
    ap.add_argument("--body-split", action="store_true")
    ap.add_argument("--table-bodies", action="store_true")
    a = ap.parse_args()
    pool = Pool()
    card = {c["fullName"]: c for c in pool.cards}
    tr = lambda x: card[x]["superType"] == 2
    basic_e = lambda x: card[x]["superType"] == 3 and card[x]["energyType"] == 0
    draw = lambda x: card[x]["name"] in DRAW
    by_name = collections.defaultdict(list)
    for c in pool.cards:
        if pool.allowed[c["id"]] and c["superType"] == 2 and c["name"] not in DRAW:
            by_name[c["name"]].append(c["fullName"])
    names = sorted(by_name)
    rng = np.random.default_rng(SEED)

    def free(cards):
        fill = collections.Counter(x for x in cards if basic_e(x)).most_common(1)[0][0]
        return [fill if draw(x) else x for x in cards]

    def check(cards):
        assert len(cards) == 60 and not any(draw(x) for x in cards) and pool.legal(pool.vector(cards))
        return cards

    def pick(name):
        p = by_name[name]
        return p[int(rng.integers(len(p)))]

    def scramble_t(d):                                 # uniform draws of the same count, copy limit kept
        keep, out, used = [x for x in d if not tr(x)], [], collections.Counter()
        while len(out) < len(d) - len(keep):
            m = names[int(rng.integers(len(names)))]
            if used[m] < 4:
                used[m] += 1
                out.append(pick(m))
        return keep + out

    def scramble_c(d):                                 # the copy pattern kept, identities drawn without replacement
        counts = collections.Counter(card[x]["name"] for x in d if tr(x))
        out = [x for x in d if not tr(x)]
        for k, j in zip(counts.values(), rng.choice(len(names), size=len(counts), replace=False)):
            out += [pick(names[int(j)])] * k
        return out

    def scramble_b(d):                                 # a wide deck's Pokemon and basic Energy at the list's counts
        p = sum(card[x]["superType"] == 1 for x in d)
        e = sum(card[x]["superType"] == 3 for x in d)
        while True:
            w = pool.names(wide_deck(pool, rng))
            mons, es = [x for x in w if card[x]["superType"] == 1], [x for x in w if basic_e(x)]
            if len(mons) == p and es:
                return [x for x in d if tr(x)] + mons + [es[int(j)] for j in rng.integers(len(es), size=e)]

    out = subprocess.run(["node", "-e", "const {archivedDecks}=require('./env/decks.js');console.log(JSON.stringify(archivedDecks()))"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    lists = [{"name": d["name"], "cards": list(d["cards"])} for d in json.loads(out.stdout)]
    rules = [{"name": d["name"], "cards": list(d["cards"])} for d in json.loads((ROOT / "runs/probe/C162-draw-shape/decks.json").read_text(encoding="utf-8"))]
    assert len(lists) == 24 and len(rules) == 99
    if a.body_split:
        return body_split(pool, card, lists)
    if a.table_bodies:
        return table_bodies(pool, card, lists)
    if a.uniform_trainers:
        return uniform_trainers(pool, card)
    base = lambda ds: [{"name": d["name"] + "-base", "src": d["name"], "cards": check(free(d["cards"]))} for d in ds]
    sets = {"L": lists, "R": rules, "L_base": base(lists), "R_base": base(rules)}
    where = C163
    if a.knockouts:
        where, sets = C164, {}
        free_lists = [free(d["cards"]) for d in lists]
        for tag, fn, part in (("T", scramble_t, lambda x: not tr(x)), ("C", scramble_c, lambda x: not tr(x)), ("B", scramble_b, tr)):
            sets[tag] = [{"name": f"{tag}{k}.{r}", "src": lists[k]["name"], "cards": check(fn(free_lists[k]))} for k in range(24) for r in range(SCRAMBLES)]
            for d in sets[tag]:                        # only the knocked-out part differs
                k = next(i for i, x in enumerate(lists) if x["name"] == d["src"])
                assert collections.Counter(filter(part, d["cards"])) == collections.Counter(filter(part, free_lists[k])), d["name"]
        kept, tried = [], 0
        while len(kept) < N_K:
            tried += 1
            v = wide_deck(pool, rng, concentrated=True)
            s = deck_shape(pool, v)
            pte = (s["pokemon"], s["trainer"], s["basic_energy"] + s["special_energy"])
            if all(x <= y <= z for y, (x, z) in zip(pte, K_BOUNDS)):
                kept.append({"name": f"K{len(kept)}", "src": None, "cards": check(free(pool.names(v))), "pte": list(pte)})
        sets["K"] = kept
        print(f"K: {tried} concentrated decks drawn for {len(kept)} kept; mean P/T/E {np.round(np.mean([k['pte'] for k in kept], 0), 2).tolist()}")
    for tag, ds in sets.items():
        (where / f"{tag}.json").write_text(json.dumps(ds), encoding="utf-8")
        tn = [sum(tr(x) for x in d["cards"]) for d in ds]
        en = [sum(basic_e(x) for x in d["cards"]) for d in ds]
        mx = [max(collections.Counter(card[x]["name"] for x in d["cards"] if tr(x)).values(), default=0) for d in ds]
        dc = [sum(draw(x) for x in d["cards"]) for d in ds]
        print(f"{tag}: {len(ds)} decks; mean Trainers {np.mean(tn):.1f}, basic Energy {np.mean(en):.1f} (min {min(en)}), top Trainer copies {np.mean(mx):.2f}, draw copies {np.mean(dc):.2f}")


if __name__ == "__main__":
    main()
