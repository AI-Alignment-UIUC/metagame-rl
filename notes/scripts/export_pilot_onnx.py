"""Export a metagame / lab checkpoint's pilot (keys net/config, or model/config) to ONNX for env/agents.js
OnnxTokenAgent / PolicySearchAgent, on the CPU, and check the export against the PyTorch model (evaluation only,
log #137's "stronger play of the human lists" diagnostic).

  CUDA_VISIBLE_DEVICES= .venv/Scripts/python notes/scripts/export_pilot_onnx.py \
      --ckpt runs/screens/scr-resetcap/checkpoint.pt --out runs/probe/resetcap499.onnx [--check runs/probe/obs_dump.json]

--check: a JSON file of real observations dumped by notes/scripts/walls_vs_humans.js --dump-obs (the token fields of
each state, and the ONNX logits / value Node computed for it); compares the PyTorch model's outputs on the same inputs.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.gpu_matrix import load_policy  # noqa: E402
from rl.token_model import export_token_onnx  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", default="")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--dyn-tok", action="store_true",
                    help="also make the token axis dynamic (dim 1 of tok_card / tok_kind / tok_aux), so a caller can trim "
                         "the padding to the batch's longest state (notes/scripts/walls_vs_humans.js --trim)")
    args = ap.parse_args(argv)
    torch.set_num_threads(args.threads)
    model, enc = load_policy(args.ckpt, "cpu")
    assert enc == "tokens", enc
    print("config", {k: model.cfg[k] for k in ("d", "layers", "heads", "deck_mode", "deck_layers", "history", "memory",
                                                "n_agents", "max_tok", "max_cand")})
    out = ROOT / args.out
    if not args.check:
        out.parent.mkdir(parents=True, exist_ok=True)
        if args.dyn_tok:
            from rl.token_model import INPUTS
            B = 2
            dummy = (torch.zeros(B, model.max_tok, dtype=torch.int16), torch.ones(B, model.max_tok, dtype=torch.uint8),
                     torch.zeros(B, model.max_tok, dtype=torch.uint8), torch.zeros(B, model.glob_f, dtype=torch.uint8),
                     torch.zeros(B, 12 * model.slot_f, dtype=torch.uint8),
                     torch.zeros(B, model.max_cand * 6, dtype=torch.int16), torch.ones(B, dtype=torch.int32))
            axes = {n: {0: "batch"} for n in INPUTS + ["logits", "value"]}
            for n in ("tok_card", "tok_kind", "tok_aux"):
                axes[n] = {0: "batch", 1: "tok"}
            torch.onnx.export(model.eval(), dummy, str(out), input_names=INPUTS, output_names=["logits", "value"],
                              dynamic_axes=axes, opset_version=17, dynamo=False)
        else:
            export_token_onnx(model, str(out))
        print("exported", out, out.stat().st_size, "bytes")
    # synthetic check: torch against onnxruntime (Python) on random token inputs with real-looking kinds
    import onnxruntime as ort
    sess = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"])
    cfg = model.cfg
    T, M = cfg["max_tok"], cfg["max_cand"]
    if args.check:
        d = json.load(open(ROOT / args.check))
        rows = d["rows"]
        B = len(rows)
        f = lambda k, dt: np.array([r[k] for r in rows], dtype=dt)
        feeds = {"tok_card": f("tokCard", np.int16), "tok_kind": f("tokKind", np.uint8), "tok_aux": f("tokAux", np.uint8),
                 "glob": f("glob", np.uint8), "slots": f("slots", np.uint8), "cand": f("cand", np.int16),
                 "n_cand": f("nCand", np.int32)}
    else:
        rng = np.random.default_rng(0)
        B = 16
        kind = np.zeros((B, T), np.uint8)
        for b in range(B):
            n = rng.integers(40, 200)
            kind[b, :n] = rng.integers(1, 14, n)
            kind[b, 0] = 1
        feeds = {"tok_card": rng.integers(0, model.card_feats.shape[0], (B, T)).astype(np.int16), "tok_kind": kind,
                 "tok_aux": rng.integers(0, 8, (B, T)).astype(np.uint8), "glob": rng.integers(0, 48, (B, cfg["glob_f"])).astype(np.uint8),
                 "slots": rng.integers(0, 48, (B, 12 * cfg["slot_f"])).astype(np.uint8),
                 "cand": np.stack([np.concatenate([rng.integers(0, 12, (M, 1)), rng.integers(0, model.card_feats.shape[0], (M, 1)),
                                                   rng.integers(0, 16, (M, 2)), rng.integers(0, 200, (M, 1)),
                                                   rng.integers(0, 8, (M, 1))], 1).reshape(-1) for _ in range(B)]).astype(np.int16),
                 "n_cand": rng.integers(2, 20, B).astype(np.int32)}
    lo, vo = sess.run(["logits", "value"], feeds)
    with torch.no_grad():
        lt, vt = model(*[torch.from_numpy(feeds[k].astype(np.int64 if feeds[k].dtype == np.int16 else feeds[k].dtype))
                         for k in ("tok_card", "tok_kind", "tok_aux", "glob", "slots", "cand", "n_cand")])
    lt, vt = lt.numpy(), vt.numpy()
    nc = feeds["n_cand"]
    dl = max(float(np.abs(lo[b, :nc[b]] - lt[b, :nc[b]]).max()) for b in range(B))
    agree = np.mean([lo[b, :nc[b]].argmax() == lt[b, :nc[b]].argmax() for b in range(B)])
    print(f"python onnxruntime vs torch, {B} states: max |logit diff| {dl:.2e}, max |value diff| "
          f"{float(np.abs(vo - vt).max()):.2e}, argmax agreement {agree:.3f}")
    if args.dyn_tok:
        T2 = max(13, int((feeds["tok_kind"] > 0).nonzero()[1].max()) + 1)
        trimmed = dict(feeds, tok_card=feeds["tok_card"][:, :T2], tok_kind=feeds["tok_kind"][:, :T2], tok_aux=feeds["tok_aux"][:, :T2])
        l2, v2 = sess.run(["logits", "value"], trimmed)
        d2 = max(float(np.abs(l2[b, :nc[b]] - lt[b, :nc[b]]).max()) for b in range(B))
        print(f"trimmed to {T2} tokens vs torch (full): max |logit diff| {d2:.2e}, max |value diff| {float(np.abs(v2 - vt).max()):.2e}")
    if args.check:
        ln = np.array([r["logits"] for r in rows], np.float32)
        vn = np.array([r["value"] for r in rows], np.float32)
        dn = max(float(np.abs(ln[b, :nc[b]] - lt[b, :nc[b]]).max()) for b in range(B))
        an = np.mean([ln[b, :nc[b]].argmax() == lt[b, :nc[b]].argmax() for b in range(B)])
        print(f"node onnxruntime vs torch, {B} states: max |logit diff| {dn:.2e}, max |value diff| "
              f"{float(np.abs(vn - vt).max()):.2e}, argmax agreement {an:.3f}")


if __name__ == "__main__":
    main()
