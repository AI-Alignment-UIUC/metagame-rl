"""Tests for card_latent.patch (cand_latent, cand_latent_zone, cand_latent_gate; rl/token_model.py).

Run (CPU, no GPU):
  CUDA_VISIBLE_DEVICES= CARDREF_BASE=<clean tree at 77fbae0> PYTHONPATH=<tree with the patch applied> \
      <main repo>/.venv/Scripts/python.exe test_card_latent.py [--batch cardref_batch.npz] [--decisions 400]

The patched tree needs ryuu-play and node_modules (junctions to the main repo's) only when --batch does not exist yet: then a few
hundred decisions are collected on CPU with RemotePool, as notes/scripts/probe_prompt_stats.py does (C49-sd, the practice matchups, a
chain-4 grown copy so the batch has chain rows) and saved to the .npz. CARDREF_MAIN = the main repo (checkpoint, card data).
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import torch

MAIN = Path(os.environ.get("CARDREF_MAIN", "C:/Users/evanc/Desktop/333/metagame-rl"))
BASE = Path(os.environ.get("CARDREF_BASE", ""))
CKPT = str(MAIN / "runs/pilot/C49-sd/model_it00199.pt")
OVR = {"cand_latent": 1, "cand_latent_zone": 1, "cand_latent_gate": 1}
OVR2 = {"cand_latent": 2, "cand_latent_zone": 1}
K = 4
PROMPT, HAND, DISCARD = 12, 6, 7
FAIL = []


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        FAIL.append(msg)


def load_module(name, root):
    spec = importlib.util.spec_from_file_location(name, root / "rl" / "token_model.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect(path, n):
    from rl.gpu_matrix import load_policy
    from rl.remote import RemotePool
    from rl.rollouts import read_rollout, concat
    from rl.train import model_inputs
    model, _ = load_policy(CKPT, "cpu", {"chain": K})
    model.eval()
    matchups = __import__("json").loads((MAIN / "runs/pilot/C30/matchups.json").read_text(encoding="utf-8"))
    pool = RemotePool(2)
    out = Path(path).with_suffix("")
    try:
        msgs = [{"cmd": "collect", "encoding": "tokens", "transitions": n // 2, "concurrency": 8, "seed": 91 * 1_000_003 + w,
                 "roundTurns": [20, 45], "deckoutWin": 1.0, "matchups": matchups, "opponents": [{"spec": "self", "weight": 1.0}],
                 "out": f"{out}_w{w}.bin", "history": 0, "chain": K} for w in range(2)]
        replies = pool.collect(msgs, {0: model}, "cpu")
    finally:
        pool.close()
    batch = concat([read_rollout(r["out"]) for r in replies])
    arrs = model_inputs(batch, "tokens")
    np.savez_compressed(path, *arrs)
    print(f"collected {len(arrs[0])} decisions -> {path}")


def make(mod, over=None, chain=0, state=None, seed=0):
    """A model of C49-sd's architecture from module `mod`; `state` (a state_dict) loaded non-strictly."""
    ck = torch.load(CKPT, map_location="cpu", weights_only=False)
    cfg = {**ck["config"], "chain": chain, **(over or {})}
    skip = ("kind", "n_names", "glob_f", "slot_f", "max_tok", "max_cand")
    torch.manual_seed(seed)
    m = mod.build_token_model(str(MAIN / "notes/data/cards/pool.json"), str(MAIN / "notes/data/cards/text_emb.npy"),
                              cfg["n_names"], cfg["glob_f"], cfg["slot_f"], cfg["max_tok"], cfg["max_cand"],
                              **{k: v for k, v in cfg.items() if k not in skip})
    missing, unexpected = m.load_state_dict(state or ck["model"], strict=False)
    assert not unexpected
    return m.eval(), missing


def run(m, inp, grad=False, mb=128):
    """logits, values over the whole batch (micro-batches; tokens trimmed to the longest)."""
    ls, vs = [], []
    for i in range(0, len(inp[0]), mb):
        xs = [t[i:i + mb] for t in inp]
        L = int(((xs[1] > 0).long() * torch.arange(1, xs[1].shape[1] + 1)).amax())
        xs[:3] = [t[:, :L] for t in xs[:3]]
        with torch.set_grad_enabled(grad):
            l, v = m(*xs)
        ls.append(l), vs.append(v)
    w = max(l.shape[1] for l in ls)
    return torch.cat([torch.nn.functional.pad(l, (0, w - l.shape[1]), value=-1e9) for l in ls]), torch.cat(vs)


def same(a, b):
    return torch.equal(a[0], b[0]) and torch.equal(a[1], b[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", default="cardref_batch.npz")
    ap.add_argument("--decisions", type=int, default=400)
    args = ap.parse_args()
    assert BASE.is_dir(), "set CARDREF_BASE to a clean tree at 77fbae0"
    if not Path(args.batch).exists():
        collect(args.batch, args.decisions)
    z = np.load(args.batch)
    inp = [torch.from_numpy(z[f"arr_{i}"].astype(np.int64)) for i in range(7)]
    tok_card, tok_kind, cand, n_cand = inp[0], inp[1], inp[5].view(len(inp[0]), -1, 6), inp[6]
    print(f"batch: {len(tok_card)} decisions")
    new, base = load_module("tm_new", Path(os.environ["PYTHONPATH"].split(os.pathsep)[0])), load_module("tm_base", BASE)
    has_chain = bool((cand[:, -K:, 0] > 0).any())
    print(f"chain rows in the batch: {has_chain} ({int((cand[:, -K:, 0] > 0).sum())} rows)")

    # (a) keys off: the same state_dict keys and every output, with and without the chain head
    for ch in (0, K):
        b, _ = make(base, chain=ch)
        if ch:                                   # make the chain rows matter: a nonzero chain_cross
            g = torch.Generator().manual_seed(5)
            for p in (b.chain_cross.proj.weight, b.chain_cross.ff[-1].weight):
                p.data = torch.randn(p.shape, generator=g) * 0.05
        n, _ = make(new, chain=ch, state=b.state_dict())
        check(list(b.state_dict()) == list(n.state_dict()), f"(a) chain={ch}: state_dict keys equal ({len(b.state_dict())})")
        check(n.config() == b.config(), f"(a) chain={ch}: config() equal")
        ob = run(b, inp)
        check(same(ob, run(n, inp)), f"(a) chain={ch}: logits and values bit-identical on {len(tok_card)} decisions")
        if ch:
            check((run(make(base, chain=ch)[0], inp)[0] != ob[0]).any().item(), "(a) chain rows matter in this test (outputs differ from zero chain_cross)")

        # (b) each key on, g = 0: bit-identical to off
        for over in (OVR, OVR2, {"cand_latent": 1}, {"cand_latent": 1, "cand_latent_zone": 1}):
            m, miss = make(new, {**over}, chain=ch, state=b.state_dict())
            new_names = {k for k in m.state_dict() if k.startswith(("g_", "lat_", "ptr_"))}
            assert set(miss) == new_names, miss
            g = m.g_lat if m.cand_latent == 1 else m.g_ptr
            check(float(g) == 0.0 and same(ob, run(m, inp)), f"(b) chain={ch} {over}: g=0 logits and values bit-identical to off")

    # (c) g = 1: logits move at prompt-pick rows; gradients reach g_lat, lat_proj, lat_verb (and g_ptr, ptr_q)
    pick = ((cand[:, :-K, 0] >= 11) & (cand[:, :-K, 0] <= 15) & (cand[:, :-K, 1] > 0)).any(1)
    valid = torch.arange(cand.shape[1] - K)[None] < n_cand.view(-1, 1)
    print(f"(c) rows with a card-naming prompt pick: {int(pick.sum())} of {len(pick)}")
    b, _ = make(base, chain=K)
    off = run(b, inp)[0][:, :cand.shape[1] - K]
    for over, params in ((OVR, ("g_lat", "lat_proj.weight", "lat_verb.weight")), (OVR2, ("g_ptr", "ptr_q.weight"))):
        m, _ = make(new, over, chain=K, state=b.state_dict())
        with torch.no_grad():
            (m.g_lat if m.cand_latent == 1 else m.g_ptr).fill_(1.0)
        on = run(m, inp)[0][:, :cand.shape[1] - K]
        diff = ((on - off).abs() * valid).amax(1)
        check(bool((diff[pick] > 0).any()) and float(diff[pick].mean()) > 0, f"(c) {over}: logits change at pick rows "
              f"(mean max |d| {float(diff[pick].mean()):.4f}, changed rows {int((diff[pick] > 0).sum())}/{int(pick.sum())})")
        m.zero_grad()
        sub = [t[:128] for t in inp]
        l, v = run(m, sub, grad=True)
        w = torch.randn(l.shape, generator=torch.Generator().manual_seed(1))
        (((l.clamp(min=-50) * w) * (l > -1e8)).sum() + v.sum()).backward()
        for name in params:
            gr = dict(m.named_parameters())[name].grad
            check(gr is not None and float(gr.abs().sum()) > 0, f"(c) {over}: nonzero grad on {name} ({0 if gr is None else float(gr.abs().sum()):.3e})")

    # (d) the zone filter resolves to the right zone (card_tokens is the code heads() uses)
    m, _ = make(new, OVR, chain=K, state=b.state_dict())
    mask = tok_kind > 0
    o = cand[:, :-K]
    verb, card, s1, s2 = o[..., 0], o[..., 1], o[..., 2], o[..., 3]
    kept = m.card_tokens(tok_card, tok_kind, mask, verb, card, s1, s2)
    allm = make(new, {"cand_latent": 1}, chain=K, state=b.state_dict())[0].card_tokens(tok_card, tok_kind, mask, verb, card, s1, s2)
    ok = valid & (card > 0)

    def share(sel, zone, label):
        sel = sel & ok
        got = (kept & (tok_kind[:, None, :] == zone)).any(-1) & (kept.sum(-1) == (kept & (tok_kind[:, None, :] == zone)).sum(-1))
        anym = allm.any(-1)
        n = int(sel.sum())
        print(f"(d) {label}: {n} candidates; {float((got & sel).sum()) / max(n, 1):.1%} resolve to a {zone}-kind token only "
              f"({float((anym & sel).sum()) / max(n, 1):.1%} have any matching token)")
        return float((got & sel).sum()) / max(n, 1)

    pk = share((verb >= 11) & (verb <= 15), PROMPT, "pick from prompt, card named")
    hp = share((s1 == 14), HAND, "power from hand (slot 14)")
    hv = share((verb >= 2) & (verb <= 5), HAND, "attach / basic / evolve / trainer from hand")
    dc = share((s1 == 15), DISCARD, "power from discard (slot 15)")
    check(pk >= 0.9, f"(d) >= 90% of pick-from-prompt candidates resolve to a PROMPT token ({pk:.1%})")
    hand_sel = ok & ((s1 == 14) | ((verb >= 2) & (verb <= 5)))
    hh = float(((kept & (tok_kind[:, None, :] == HAND)).any(-1) & hand_sel).sum()) / max(int(hand_sel.sum()), 1)
    check(hh >= 0.9, f"(d) >= 90% of from-hand candidates resolve to a HAND token ({hh:.1%}, {int(hand_sel.sum())} candidates)")

    # (e) the C49-sd checkpoint with the overrides, through load_policy (also what ar/fixed.py start_model calls)
    from rl.gpu_matrix import load_policy
    ref, _ = load_policy(CKPT, "cpu")
    for over in (OVR, OVR2):
        m, _ = load_policy(CKPT, "cpu", over)
        gname = "g_lat" if over["cand_latent"] == 1 else "g_ptr"
        fresh = [k for k in m.state_dict() if k not in ref.state_dict()]
        check(sorted(fresh) == sorted(k for k in m.state_dict() if k.startswith(("lat_", "ptr_", "g_"))) and gname in fresh,
              f"(e) load_policy {over}: fresh params {fresh}")
        check(m.config()["cand_latent"] == over["cand_latent"], "(e) config() records the keys")
        oref, om = run(ref, inp), run(m, inp)
        check(same(oref, om), f"(e) {over}: step 0 logits and values identical to the checkpoint")
        check(bool((oref[0].argmax(1) == om[0].argmax(1)).all()), "(e) step 0 greedy actions identical")
    print("\nALL PASS" if not FAIL else f"\n{len(FAIL)} FAILED: {FAIL}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
