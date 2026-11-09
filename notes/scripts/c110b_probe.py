"""C110b (research, in C110's record): where along the path is the knockout margin lost? On C110's conversion and no-KO
states (the same folds by game and game bootstrap), per pilot, two detached tensors:
  D: the encoder output at the opponent's Active board token (net.encode()[0] at the SLOT token with aux 6);
  C: the input to the policy's score layer at the "play PlusPower" option (rl/token_model.py heads: logits = self.score(c)).
For each: AUC for conversion against no-KO; out-of-fold R^2 for the Defender's HP left (ridge); and the AUC of
[HP left + embedding] minus B1 (HP alone, c110_floor). Evaluation only, CPU.
  CUDA_VISIBLE_DEVICES=-1 PYTHONPATH=. .venv/Scripts/python notes/scripts/c110b_probe.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
from c110_probe import auc, boot_games, ci, oof_scores   # noqa: E402
from c110_floor import SLOT_F, tens                       # noqa: E402
from rl.gpu_matrix import load_policy                     # noqa: E402
from rl.remote import trim_inputs                         # noqa: E402

OUT = ROOT / "runs" / "probe" / "C110-ko-math"
DT = {"tok_card": np.int16, "tok_kind": np.uint8, "tok_aux": np.uint8, "glob": np.uint8, "slots": np.uint8, "cand": np.int16}
PILOTS = {"start": "ar/data/start.pt", "arm0_s1": "runs/probe/BENCH/arm-arm0-s1/pilot.pt",
          "p5_s1": "runs/probe/BENCH/arm-p5-s1/pilot.pt", "p5_s2": "runs/probe/BENCH/arm-p5-s2/pilot.pt"}


def tensors(path, rows):
    net, _ = load_policy(path, "cpu")
    net.eval()
    grab = {}
    h = net.score.register_forward_hook(lambda m, i, o: grab.__setitem__("c", i[0].detach()))
    D, C = [], []
    with torch.no_grad():
        for st in range(0, len(rows), 64):
            ch = rows[st:st + 64]
            ins = [torch.from_numpy(np.stack([np.asarray(r["obs"][k], dtype=DT[k]) for r in ch])) for k in DT]
            ins.append(torch.tensor([int(r["obs"]["n_cand"]) for r in ch], dtype=torch.int32))
            ins = trim_inputs(ins, net)
            x = net.encode(*ins[:5])[0]
            net(*ins)
            tk, ta = ins[1].long(), ins[2].long()
            for b, r in enumerate(ch):
                pos = torch.nonzero((tk[b] == 2) & (ta[b] == 6)).flatten()
                D.append(x[b, int(pos[0])].float().numpy() if len(pos) else np.zeros(x.shape[-1], np.float32))
                C.append(grab["c"][b, int(r["pp_opt"])].float().numpy())
    h.remove()
    return np.array(D), np.array(C)


def r2_oof(Z, t, game):
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    ug = np.unique(game)
    fold = {g: i % 5 for i, g in enumerate(np.random.default_rng(0).permutation(ug))}
    f = np.array([fold[g] for g in game])
    p = np.zeros(len(t))
    for k in range(5):
        tr, te = f != k, f == k
        s = StandardScaler().fit(Z[tr])
        p[te] = Ridge(alpha=1.0).fit(s.transform(Z[tr]), t[tr]).predict(s.transform(Z[te]))
    return float(1 - ((t - p) ** 2).sum() / ((t - t.mean()) ** 2).sum())


def main():
    rows = [r for r in torch.load(OUT / "states.pt", weights_only=False)["rows"] if r.get("label") in ("conv", "noko")]
    y = np.array([int(r["label"] == "conv") for r in rows])
    game = np.array([r["game"] for r in rows])
    hp = np.array([10 * (tens(np.asarray(r["obs"]["slots"]).reshape(-1, SLOT_F)[6, 2])
                         - tens(np.asarray(r["obs"]["slots"]).reshape(-1, SLOT_F)[6, 3])) for r in rows], float)
    s_b1 = oof_scores(hp[:, None], y, game)
    b1 = auc(y, s_b1)
    res = {"n": int(len(y)), "B1_hp_auc": round(b1, 4), "tensors": {"D": "net.encode(...)[0] at the SLOT token with tok_aux 6 (opponent's Active)",
           "C": "input to net.score (heads: logits = self.score(c)) at row pp_opt (the play-PlusPower option)"}, "pilots": {}}
    for name, path in PILOTS.items():
        D, C = tensors(path, rows)
        out = {}
        for tag, Z in (("D", D), ("C", C)):
            s = oof_scores(Z, y, game)
            sh = oof_scores(np.hstack([hp[:, None], Z]), y, game)
            bs = boot_games(game, [lambda ii, s=s: auc(y[ii], s[ii]), lambda ii, sh=sh: auc(y[ii], sh[ii]) - auc(y[ii], s_b1[ii])])
            out[tag] = {"auc": round(auc(y, s), 4), "auc_ci": [round(v, 4) for v in ci(bs[:, 0])],
                        "r2_hp_left": round(r2_oof(Z, hp, game), 4),
                        "hp_plus_emb_minus_B1": round(auc(y, sh) - b1, 4), "inc_ci": [round(v, 4) for v in ci(bs[:, 1])]}
        res["pilots"][name] = out
        print(name, json.dumps(out), flush=True)
    c_ok = all(res["pilots"][k]["C"]["auc"] >= 0.88 for k in ("arm0_s1", "p5_s1", "p5_s2"))
    d = np.mean([v["D"]["auc"] for v in res["pilots"].values()])
    c = np.mean([v["C"]["auc"] for v in res["pilots"].values()])
    res["band"] = ("R-readable" if c_ok else "R-lost-in-path" if d >= 0.88 and c < 0.80 else "R-blurred" if d < 0.80 else "between")
    res["mean_auc"] = {"D": round(float(d), 4), "C": round(float(c), 4)}
    (OUT / "c110b.json").write_text(json.dumps(res, indent=1))
    print("band", res["band"], res["mean_auc"])


if __name__ == "__main__":
    main()
