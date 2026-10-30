"""BENCH-P2 mechanism gates (runs/probe/BENCH/P2/record.md): how much the key-1 path at picks carries, on stored prompt rows
(probe_target_signal's raw probes). Evaluation only. Four passes of the pilot per chunk, through hooks on lat_proj:
  normal       L_c (lat_proj's input, centred), W L_c (its output; g_lat is 1) and the option embedding (cand_in's input)
  path off     lat_proj's output zeroed: the logits without the path
  shuffled     L_c permuted among the decision's pick options: the latent-shuffle TV of the policy
  uncentred    cand_latent_center off: mean L, for |cos| with W's top input direction (the C87 "names a card" check)
Readouts, on Computer Search fetches (CHOOSE_CARD_TO_HAND inside Computer Search) and on every pick prompt: the path ratio
||W L_c|| / ||embed|| at pick options, the path's logit sd / the logit sd within a prompt, the TV, and |cos|.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/p2_gates.py --pilot runs/probe/BENCH/arm-p2-s1/pilot.pt \
      --raw runs/probe/BENCH/O_B.json.probes.json.gz --out runs/probe/BENCH/arm-p2-s1/gates.json
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.gpu_matrix import load_policy      # noqa: E402
from rl.remote import trim_inputs          # noqa: E402

DT = {"tok_card": np.int16, "tok_kind": np.uint8, "tok_aux": np.uint8, "glob": np.uint8, "slots": np.uint8, "cand": np.int16}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--raw", default="runs/probe/BENCH/O_B.json.probes.json.gz")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    model, _ = load_policy(a.pilot, a.device)
    model.eval()
    assert getattr(model, "cand_latent_pick", 0), "the pilot has no cand_latent_pick path"
    probes = [p for p in json.loads(gzip.open(ROOT / a.raw, "rt").read())["probes"] if p.get("prompt")]
    rng = torch.Generator().manual_seed(a.seed)
    mode, cap = {"m": "normal"}, {}

    def pre(mod, inp):
        L = inp[0]
        cap.setdefault("L", L.detach())
        if mode["m"] == "shuffled":                      # permute L among each decision's pick rows (non-picks are 0)
            pick = (L.abs().sum(-1) > 0)
            out = L.clone()
            for b in range(L.shape[0]):
                idx = torch.nonzero(pick[b]).flatten()
                if len(idx) > 1:
                    out[b, idx] = L[b, idx[torch.randperm(len(idx), generator=rng)]]
            return (out,)

    def post(mod, inp, out):
        cap.setdefault("WL", out.detach())
        return torch.zeros_like(out) if mode["m"] == "off" else None

    hooks = [model.lat_proj.register_forward_pre_hook(pre), model.lat_proj.register_forward_hook(post),
             model.cand_in.register_forward_pre_hook(lambda mod, inp: cap.setdefault("E", inp[0].detach()))]
    rows = {"cs_fetch": [], "picks": []}
    meanL = []
    try:
        with torch.no_grad():
            for s in range(0, len(probes), 32):
                chunk = probes[s:s + 32]
                ins = [torch.from_numpy(np.stack([np.array(p["obs"][k], dtype=DT[k]) for p in chunk])).to(a.device) for k in DT]
                ins.append(torch.tensor([p["obs"]["n_cand"] for p in chunk], dtype=torch.int32, device=a.device))
                ins = trim_inputs(ins, model)
                out = {}
                for m in ("normal", "off", "shuffled", "uncentred"):
                    mode["m"] = m
                    cap.clear()
                    model.cand_latent_center = 0 if m == "uncentred" else 1
                    out[m] = (model(*ins)[0].float().cpu().numpy(), {k: v.float().cpu().numpy() for k, v in cap.items()})
                model.cand_latent_center = 1
                lg, c = out["normal"]
                L = out["uncentred"][1]["L"]
                for i, p in enumerate(chunk):
                    legal = np.array(p["legal"])
                    verb = c["E"].shape and np.array(p["obs"]["cand"], dtype=np.int64).reshape(-1, 6)[:len(p["legal"]), 0]
                    pk = legal[(verb >= 11) & (verb <= 15)]
                    if len(pk) < 2:
                        continue
                    soft = lambda z: (lambda e: e / e.sum())(np.exp(z - z.max()))
                    full, off, shuf = lg[i, legal], out["off"][0][i, legal], out["shuffled"][0][i, legal]
                    r = {"path_ratio": float(np.mean(np.linalg.norm(c["WL"][i, pk], axis=-1) /
                                                     np.maximum(np.linalg.norm(c["E"][i, pk], axis=-1), 1e-9))),
                         "logit_sd_ratio": float(np.std(full - off) / max(np.std(full), 1e-9)),
                         "tv": float(0.5 * np.abs(soft(full) - soft(shuf)).sum())}
                    meanL.append(L[i, pk].mean(0))
                    rows["picks"].append(r)
                    if p.get("trainer", "").startswith("Computer Search") and p.get("message") == "CHOOSE_CARD_TO_HAND":
                        rows["cs_fetch"].append(r)
    finally:
        for h in hooks:
            h.remove()
    W = model.lat_proj.weight.detach().float().cpu().numpy()
    v1 = np.linalg.svd(W)[2][0]                          # W's top input direction
    mL = np.mean(meanL, 0) if meanL else np.zeros(W.shape[1])
    cos = float(abs(v1 @ mL) / max(np.linalg.norm(mL), 1e-9))
    res = {"pilot": a.pilot, "raw": a.raw, "abs_cos_top_meanL": round(cos, 4)}
    for k, rs in rows.items():
        res[k] = {"n": len(rs), **{m: round(float(np.mean([r[m] for r in rs])), 4) if rs else None
                                    for m in ("path_ratio", "logit_sd_ratio", "tv")}}
    (ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
