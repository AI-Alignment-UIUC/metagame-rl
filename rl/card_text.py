"""Rules-text embeddings for the card table (plan item A4.2).

Embeds each card's plain-text description (env/tools/card_features.js) with a frozen sentence
encoder, so the token model can represent cards it never trained on. Row 0 is "no card".

Run: .venv/Scripts/python -m rl.card_text [--table notes/data/cards/pool.json]
         [--model sentence-transformers/all-MiniLM-L6-v2] [--out notes/data/cards/text_emb.npy]
"""
import argparse
import json

import numpy as np


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="notes/data/cards/pool.json")
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--out", default="notes/data/cards/text_emb.npy")
    args = ap.parse_args(argv)
    from sentence_transformers import SentenceTransformer
    table = json.load(open(args.table, encoding="utf-8"))["cards"]
    model = SentenceTransformer(args.model, device="cpu")
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


if __name__ == "__main__":
    main()
