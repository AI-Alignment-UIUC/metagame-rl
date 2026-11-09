"""C110's floor check (research, written in C110's record): on C110's conversion and no-KO states, with the same 5 folds by
game and 500-resample game bootstrap, logistic probes on hand-built features in place of the encoder state.
  B1: the Defending Pokémon's HP left (slot oA's HP minus damage, from the slot features)
  B2: B1 + the Active's largest printed attack damage + Weakness and Resistance flags (Active's types against the Defender's)
Bands: margin encoded if B1 <= 0.75 and B2 >= 0.90; HP only if B1 >= 0.81. Evaluation only, CPU.
  CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=. .venv/Scripts/python notes/scripts/c110_floor.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
from c110_probe import auc, boot_games, ci, oof_scores   # noqa: E402

OUT = ROOT / "runs" / "probe" / "C110-ko-math"
SLOT_F, SLOT_KIND = 20, 2                       # env/tokens.js: SLOT_F, KIND.SLOT; slot 0 = own Active, 6 = opponent's Active
tens = lambda b: int(round(float(b) / 48 * 12))  # tokens.js q(round(x / 10) / 12) with q(v) = round(48 v)


def main():
    table = json.loads((ROOT / "notes/data/cards/pool.json").read_text(encoding="utf-8"))["cards"]
    rows = [r for r in torch.load(OUT / "states.pt", weights_only=False)["rows"] if r.get("label") in ("conv", "noko")]
    X1, X2, y, game = [], [], [], []
    for r in rows:
        o = r["obs"]
        tc, tk, ta = (np.asarray(o[k]) for k in ("tok_card", "tok_kind", "tok_aux"))
        sl = np.asarray(o["slots"]).reshape(-1, SLOT_F)
        card = lambda s: next((int(c) for c, k, a in zip(tc, tk, ta) if k == SLOT_KIND and a == s), 0)
        att, dfn = card(0), card(6)
        hp_left = 10 * (tens(sl[6, 2]) - tens(sl[6, 3]))
        a = table[att - 1] if att else {}
        d = table[dfn - 1] if dfn else {}
        dmg = max([x.get("damage", 0) or 0 for x in a.get("attacks", [])] or [0])
        typ = np.array(a.get("types", [0] * 11))
        weak = float((np.array(d.get("weakness", [0] * 11)) * typ).sum() > 0)
        res = float((np.array(d.get("resistance", [0] * 11)) * typ).sum() > 0)
        X1.append([hp_left]); X2.append([hp_left, dmg, weak, res]); y.append(int(r["label"] == "conv")); game.append(r["game"])
    X1, X2, y, game = np.array(X1, float), np.array(X2, float), np.array(y), np.array(game)
    out = {"n": int(len(y)), "conversion": int(y.sum()), "no_ko": int(len(y) - y.sum()), "games": int(len(np.unique(game)))}
    for name, X in (("B1_hp_left", X1), ("B2_hp_dmg_wr", X2)):
        s = oof_scores(X, y, game)
        b = boot_games(game, [lambda ii, s=s: auc(y[ii], s[ii])])[:, 0]
        out[name] = {"auc": round(auc(y, s), 4), "ci": [round(x, 4) for x in ci(b)]}
    b1, b2 = out["B1_hp_left"]["auc"], out["B2_hp_dmg_wr"]["auc"]
    out["band"] = "margin encoded (credit)" if b1 <= 0.75 and b2 >= 0.90 else "HP only (leans representation)" if b1 >= 0.81 else "between"
    (OUT / "floor.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
