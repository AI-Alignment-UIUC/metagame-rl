"""Rules-text embeddings for the card table (plan item A4.2).

Embeds each card's plain-text description (env/tools/card_features.js) with a frozen sentence
encoder, so the token model can represent cards it never trained on. Row 0 is "no card".

With --abilities it embeds each attack's and Pokemon Power's own text instead (log #71), for the token
model's ability_text option: notes/data/cards/ability_text.npz holds `emb` (one row per ability, row 0 =
none) and `index` [cards + 1, names + 1], the row of card c's ability with name id n (the name ids of
env/tokens.js: every attack and Power name in table order, first occurrence, from 1), 0 if it has none.

Run: .venv/Scripts/python -m rl.card_text [--table notes/data/cards/pool.json]
         [--model sentence-transformers/all-MiniLM-L6-v2] [--out notes/data/cards/text_emb.npy] [--abilities]
"""
import argparse
import json

import numpy as np


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="notes/data/cards/pool.json")
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--out", default="notes/data/cards/text_emb.npy")
    ap.add_argument("--abilities", action="store_true", help="embed each attack and Power (ability_text.npz)")
    args = ap.parse_args(argv)
    from sentence_transformers import SentenceTransformer
    table = json.load(open(args.table, encoding="utf-8"))["cards"]
    model = SentenceTransformer(args.model, device="cpu")
    if args.abilities:
        return abilities(table, model, args.out if args.out.endswith(".npz") else "notes/data/cards/ability_text.npz")
    emb = model.encode([c["description"] for c in table], normalize_embeddings=True, batch_size=64)
    out = np.zeros((len(table) + 1, emb.shape[1]), dtype=np.float32)
    out[1:] = emb
    np.save(args.out, out)
    # A sanity check: the nearest neighbours of a few cards by text.
    sim = emb @ emb.T
    names = [c["fullName"] for c in table]
    for probe in ["Gust of Wind BS", "Wigglytuff JU", "Energy Removal BS", "Electabuzz BS"]:
        i = names.index(probe)
        nn = [names[j] for j in np.argsort(-sim[i])[1:4]]
        print(f"{probe:22s} -> {', '.join(nn)}")
    print(f"{len(table)} cards, dim {emb.shape[1]} -> {args.out}")


def ability_texts(table: list) -> tuple:
    """(names, rows): the attack / Power name list in env/tokens.js order, and one (card id, name, text) per
    ability, the text as the card description writes it."""
    names, rows = [], []
    for c in table:
        for kind, abilities in (("Attack", c["attacks"]), ("Pokemon Power", c["powers"])):
            for a in abilities:
                if a["name"] not in names:
                    names.append(a["name"])
                dmg = f", {a['damageText'] or a['damage']} damage" if kind == "Attack" and (a.get("damageText") or a.get("damage")) else ""
                rows.append((c["id"], a["name"], f"{kind} {a['name']}{dmg}: {a.get('text', '')}".strip()))
    return names, rows


def abilities(table: list, model, out: str):
    names, rows = ability_texts(table)
    emb = model.encode([t for _, _, t in rows], normalize_embeddings=True, batch_size=64)
    nid = {n: i + 1 for i, n in enumerate(names)}
    index = np.zeros((len(table) + 1, len(names) + 1), dtype=np.int32)
    for r, (cid, name, _) in enumerate(rows):
        if index[cid, nid[name]] == 0:
            index[cid, nid[name]] = r + 1
    np.savez(out, emb=np.concatenate([np.zeros((1, emb.shape[1]), np.float32), emb.astype(np.float32)]), index=index)
    print(f"{len(rows)} abilities, {len(names)} names, dim {emb.shape[1]} -> {out}; e.g. {rows[0][2]!r}")


if __name__ == "__main__":
    main()
