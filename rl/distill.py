"""Is the token model a sound policy architecture? (A4.2 check, separate from RL.)

Supervised test on the same rows for both architectures (env/tools/distill_data.js): states from
the A4.1 teacher's self-play, labelled with the teacher's greedy choice and the deciding
player's final result. A token model and a fresh IdentityMLP are trained on the same games and
scored on held-out games (whole games held out, so no state leaks across):
  policy  top-1 agreement with the teacher, overall, by kind of decision (main phase vs prompt)
          and by number of options; chance level = mean of 1 / options
  value   MSE against the final result and sign accuracy on decided games; predicting 0 = 1.0
The identity MLP sees the teacher's own input encoding, so it is the upper reference for the
policy; the value target doesn't depend on the teacher.

Implementation checks on the token model:
  onnx      the ONNX export (what the rollout workers run) against PyTorch on held-out states
  permute   shuffling the candidates of a state shuffles its logits the same way
  trim      cutting padding tokens leaves the outputs unchanged

  python -m rl.distill --data runs/distill --test-seed 8 --epochs 12 --out notes/data/eval/a4_distill.json
"""
import argparse
import contextlib
import glob
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from rl.model import IdentityMLP
from rl.rollouts import read_rollout, concat
from rl.token_model import build_token_model, export_token_onnx, INPUTS
from rl.train import TOKEN_FIELDS, legal_mask

ROOT = Path(__file__).resolve().parent.parent
MAIN_VERBS = set(range(1, 11))   # env/tokens.js VERB: pass .. tip are main-phase actions


def load(data: str, seeds: list) -> tuple:
    tok = concat([read_rollout(f"{data}/d{s}.tok.bin") for s in seeds])
    ide = concat([read_rollout(f"{data}/d{s}.id.bin") for s in seeds])
    assert len(tok["action"]) == len(ide["action"])
    assert np.array_equal(np.diff(tok["legal_offsets"]), np.diff(ide["legal_offsets"])), "rows out of step"
    return tok, ide


def tok_inputs(b: dict) -> list:
    T = len(b["action"])
    return [b[k].reshape(T, -1) if k != "obs.nCand" else b[k] for k in TOKEN_FIELDS]


def to_dev(arrs, device):
    return [torch.from_numpy(np.ascontiguousarray(a)).to(device) for a in arrs]


class Data:
    def __init__(self, b: dict, kind: str, device: str, limit: int = 0):
        self.kind = kind
        n = limit or len(b["action"])         # the first `limit` rows (offsets stay valid for them)
        self.x = to_dev([x[:n] for x in (tok_inputs(b) if kind == "tokens" else [b["obs"]])], device)
        self.act = torch.from_numpy(b["action"][:n].astype(np.int64)).to(device)
        self.z = torch.from_numpy(b["reward"][:n].astype(np.float32)).to(device)
        self.off = torch.from_numpy(b["legal_offsets"].astype(np.int64)).to(device)
        self.ids = torch.from_numpy(b["legal_ids"].astype(np.int64)).to(device)
        self.n = n
        if kind == "tokens":
            kind_ = self.x[1]
            self.tok_len = ((kind_ > 0).long() * torch.arange(1, kind_.shape[1] + 1, device=device)).amax(1)

    def batch(self, idx):
        xs = [x[idx] for x in self.x]
        if self.kind == "tokens":
            L = int(self.tok_len[idx].max())
            xs[:3] = [x[:, :L] for x in xs[:3]]
        return xs


def forward(model, data: Data, idx, amp: bool):
    with torch.autocast("cuda", dtype=torch.bfloat16) if amp else contextlib.nullcontext():
        logits, v = model(*data.batch(idx))
    logits = logits.float().masked_fill(~legal_mask(idx, data.off, data.ids, model.action_size), -1e9)
    return logits, v.float()


def evaluate(model, data: Data, amp: bool, bs: int = 2048) -> dict:
    model.eval()
    pred, vals = [], []
    with torch.no_grad():
        order = torch.argsort(data.tok_len) if data.kind == "tokens" else torch.arange(data.n, device=data.act.device)
        for s in range(0, data.n, bs):
            idx = order[s:s + bs]
            logits, v = forward(model, data, idx, amp)
            pred.append((idx, logits.argmax(1)))
            vals.append((idx, v))
    model.train()
    p = torch.empty(data.n, dtype=torch.long, device=data.act.device)
    vv = torch.empty(data.n, device=data.act.device)
    for idx, x in pred:
        p[idx] = x
    for idx, x in vals:
        vv[idx] = x
    return {"correct": (p == data.act).cpu().numpy(), "value": vv.cpu().numpy()}


def train(model, tr: Data, te: Data, epochs: int, bs: int, lr: float, amp: bool, name: str) -> list:
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    steps = epochs * math.ceil(tr.n / bs)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps, pct_start=0.1)
    curve = []
    for ep in range(epochs):
        t0 = time.time()
        perm = torch.randperm(tr.n, device=tr.act.device)
        tot = 0.0
        for s in range(0, tr.n, bs):
            idx = perm[s:s + bs]
            if tr.kind == "tokens":
                idx = idx[torch.argsort(tr.tok_len[idx])]
            logits, v = forward(model, tr, idx, amp)
            loss = F.cross_entropy(logits, tr.act[idx]) + 0.5 * F.mse_loss(v, tr.z[idx])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            tot += loss.item() * len(idx)
        r = evaluate(model, te, amp)
        acc, vmse = float(r["correct"].mean()), float(np.mean((r["value"] - te.z.cpu().numpy()) ** 2))
        curve.append({"epoch": ep + 1, "train_loss": tot / tr.n, "test_acc": acc, "test_value_mse": vmse, "s": round(time.time() - t0, 1)})
        print(f"  {name} epoch {ep + 1:2d}: train loss {tot / tr.n:.4f}  held-out top-1 {100 * acc:.2f}%  value MSE {vmse:.4f}  ({time.time() - t0:.0f} s)", flush=True)
    return curve


def report(r: dict, te_tok: dict, z: np.ndarray) -> dict:
    nleg = np.diff(te_tok["legal_offsets"])
    cand = te_tok["obs.cand"].reshape(len(nleg), -1, 6)
    verb = cand[np.arange(len(nleg)), te_tok["action"], 0]
    main = np.isin(verb, list(MAIN_VERBS))
    c = r["correct"]
    dec = z != 0
    out = {"top1": float(c.mean()), "top1_main": float(c[main].mean()), "top1_prompt": float(c[~main].mean()),
           "value_mse": float(np.mean((r["value"] - z) ** 2)),
           "value_sign_acc": float(np.mean(np.sign(r["value"][dec]) == z[dec]))}
    for lo, hi in ((2, 2), (3, 5), (6, 10), (11, 99)):
        m = (nleg >= lo) & (nleg <= hi)
        if m.any():
            out[f"top1_opts_{lo}-{hi}"] = float(c[m].mean())
    return out


def checks(model, te: Data, device: str, tmp: Path) -> dict:
    """ONNX parity, candidate permutation equivariance, padding trim, on held-out states."""
    import onnxruntime as ort
    model.eval()
    n = min(2000, te.n)
    idx = torch.arange(n, device=device)
    full = [x[idx] for x in te.x]
    with torch.no_grad():
        lt, vt = model(*full)
    valid = lt > -1e8
    export_token_onnx(model, str(tmp))
    model.to(device)
    sess = ort.InferenceSession(str(tmp))
    feeds = dict(zip(INPUTS, [x.cpu().numpy() for x in full]))
    lo, vo = sess.run(["logits", "value"], feeds)
    onnx_logit = float((torch.from_numpy(lo).to(device) - lt)[valid].abs().max())
    onnx_value = float((torch.from_numpy(vo).to(device) - vt).abs().max())
    onnx_argmax = float((torch.from_numpy(lo).to(device).argmax(1) == lt.argmax(1)).float().mean())
    # Permutation: shuffle each state's first nCand candidates.
    g = torch.Generator(device="cpu").manual_seed(0)
    nc = full[6].long().cpu()
    M = model.max_cand
    perm = torch.arange(M).repeat(n, 1)
    for i in range(n):
        k = int(nc[i])
        perm[i, :k] = torch.randperm(k, generator=g)
    perm = perm.to(device)
    cand = full[5].view(n, M, 6)
    pc = torch.gather(cand, 1, perm[..., None].expand(-1, -1, 6)).reshape(n, M * 6)
    with torch.no_grad():
        lp, vp = model(*full[:5], pc, full[6])
    expect = torch.gather(lt, 1, perm)
    perm_diff = float((lp - expect)[valid].abs().max())
    # Trim: cut padding to the longest state in the sample.
    L = int(te.tok_len[idx].max())
    with torch.no_grad():
        lr_, vr = model(*[x[:, :L] for x in full[:3]], *full[3:])
    trim_diff = float((lr_ - lt)[valid].abs().max())
    model.train()
    return {"n": n, "onnx_max_logit_diff": onnx_logit, "onnx_max_value_diff": onnx_value, "onnx_argmax_agree": onnx_argmax,
            "permute_max_logit_diff": perm_diff, "permute_value_diff": float((vp - vt).abs().max()),
            "trim_max_logit_diff": trim_diff}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="runs/distill")
    ap.add_argument("--test-seed", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--bs", type=int, default=1024)
    ap.add_argument("--lr-tok", type=float, default=5e-4)
    ap.add_argument("--lr-mlp", type=float, default=5e-4)
    ap.add_argument("--d", type=int, default=192)
    ap.add_argument("--tok-layers", type=int, default=3)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="use only this many training rows (smoke test)")
    ap.add_argument("--models", default="tokens,identity")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    device = args.device
    amp = device == "cuda"
    torch.manual_seed(0)
    seeds = sorted(int(Path(f).name[1:].split(".")[0]) for f in glob.glob(f"{args.data}/d*.tok.bin"))
    train_seeds = [s for s in seeds if s != args.test_seed]
    tr_tok, tr_id = load(args.data, train_seeds)
    te_tok, te_id = load(args.data, [args.test_seed])
    z = te_tok["reward"].astype(np.float32)
    nleg = np.diff(te_tok["legal_offsets"])
    print(f"train rows {len(tr_tok['action'])} (seeds {train_seeds}), held-out rows {len(z)} (seed {args.test_seed}); "
          f"chance top-1 {100 * np.mean(1 / nleg):.1f}%", flush=True)
    out = {"train_rows": args.limit or int(len(tr_tok["action"])), "test_rows": int(len(z)), "chance_top1": float(np.mean(1 / nleg)),
           "value_mse_predict_0": float(np.mean(z ** 2))}
    meta = json.load(open(ROOT / "runs/a4/config.json"))["model_config"]
    for kind in args.models.split(","):
        tr, te = Data(tr_tok if kind == "tokens" else tr_id, kind, device, args.limit), Data(te_tok if kind == "tokens" else te_id, kind, device)
        if kind == "tokens":
            info = json.load(open(ROOT / "runs/a4-tok/config.json"))["model_config"] if (ROOT / "runs/a4-tok/config.json").exists() else None
            model = build_token_model(str(ROOT / "notes/data/cards/pool.json"), str(ROOT / "notes/data/cards/text_emb.npy"),
                                      info["n_names"], info["glob_f"], info["slot_f"], info["max_tok"], info["max_cand"],
                                      d=args.d, layers=args.tok_layers, heads=args.heads).to(device)
            lr = args.lr_tok
        else:
            model = IdentityMLP(meta["obs_size"], meta["action_size"], meta["hidden"], meta["layers"]).to(device)
            lr = args.lr_mlp
        params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"{kind}: {params} parameters", flush=True)
        t0 = time.time()
        curve = train(model, tr, te, args.epochs, args.bs, lr, amp, kind)
        res = report(evaluate(model, te, amp), te_tok, z)
        res.update({"params": params, "train_s": round(time.time() - t0), "curve": curve})
        if kind == "tokens":
            res["checks"] = checks(model, te, device, ROOT / "runs/distill/token_check.onnx")
            print(f"  checks: {res['checks']}", flush=True)
        print(f"  {kind}: " + ", ".join(f"{k} {100 * v:.2f}%" if k.startswith("top1") or k.endswith("acc") else f"{k} {v:.4f}"
                                        for k, v in res.items() if isinstance(v, float)), flush=True)
        out[kind] = res
        del tr, te, model
        torch.cuda.empty_cache()
    if args.out:
        json.dump(out, open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
