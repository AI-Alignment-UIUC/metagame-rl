"""Tests for card_state.patch (state_canon, state_key; env/tokens.js canon, rl/token_model.py, rl/remote.py guard). Apply
card_latent.patch, then card_state.patch, on a tree at 77fbae0. The encoder's own checks are in test_card_state.js.

Run (CPU, no GPU):
  CUDA_VISIBLE_DEVICES= CARDREF_BASE=<tree at 77fbae0 + card_latent.patch only> PYTHONPATH=<tree with both patches> \
      <main repo>/.venv/Scripts/python.exe test_card_state.py [--batch cardref_batch.npz] [--canon-batch cardref_canon.npz]

--batch is the plain-token batch of test_card_latent.py (1,111 C49-sd decisions, chain rows included). --canon-batch is collected
here when missing (the patched tree needs ryuu-play and node_modules, junctions to the main repo's): C49-sd with state_canon on
plays itself with "canon": 1 in the command, as the practice matchups of runs/pilot/C30. CARDREF_MAIN = the main repo.
"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

MAIN = Path(os.environ.get("CARDREF_MAIN", "C:/Users/evanc/Desktop/333/metagame-rl"))
BASE = Path(os.environ.get("CARDREF_BASE", ""))
CKPT = str(MAIN / "runs/pilot/C49-sd/model_it00199.pt")
K = 4
CANON = {"state_canon": 1}
CANON_LAT = {"state_canon": 1, "cand_latent": 1, "cand_latent_zone": 1, "cand_latent_gate": 1}
ZONE_NAMES = {6: "HAND", 7: "MY_DISCARD", 8: "OPP_DISCARD", 9: "MY_UNSEEN", 10: "OPP_DECKLIST", 12: "PROMPT", 13: "PICKED"}
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
    model, _ = load_policy(CKPT, "cpu", {"chain": K, **CANON})
    model.eval()
    matchups = json.loads((MAIN / "runs/pilot/C30/matchups.json").read_text(encoding="utf-8"))
    pool = RemotePool(2)
    out = Path(path).with_suffix("")
    try:
        msgs = [{"cmd": "collect", "encoding": "tokens", "transitions": n // 2, "concurrency": 8, "seed": 93 * 1_000_003 + w,
                 "roundTurns": [20, 45], "deckoutWin": 1.0, "matchups": matchups, "opponents": [{"spec": "self", "weight": 1.0}],
                 "out": f"{out}_w{w}.bin", "history": 0, "chain": K, "canon": 1} for w in range(2)]
        replies = pool.collect(msgs, {0: model}, "cpu")
    finally:
        pool.close()
    batch = concat([read_rollout(r["out"]) for r in replies])
    np.savez_compressed(path, *model_inputs(batch, "tokens"))
    print(f"collected {len(batch['action'])} canon decisions -> {path}")


def make(mod, over=None, chain=0, state=None, seed=0):
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


def maxdiff(a, b):
    return float(((a[0] - b[0]).abs() * (a[0] > -1e8)).max()), float((a[1] - b[1]).abs().max())


def tensors(path):
    z = np.load(path)
    return [torch.from_numpy(z[f"arr_{i}"].astype(np.int64)) for i in range(7)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", default="cardref_batch.npz")
    ap.add_argument("--canon-batch", default="cardref_canon.npz")
    ap.add_argument("--decisions", type=int, default=600)
    args = ap.parse_args()
    assert BASE.is_dir(), "set CARDREF_BASE to a tree at 77fbae0 + card_latent.patch"
    root = Path(os.environ["PYTHONPATH"].split(os.pathsep)[0])
    new, base = load_module("tm_new", root), load_module("tm_base", BASE)
    inp = tensors(args.batch)
    print(f"plain batch: {len(inp[0])} decisions")

    # (a) both keys off: state_dict keys, config and every output equal to 77fbae0 + card_latent, with and without the chain head,
    #     and with cand_latent on (heads() now also gets tok_aux)
    for ch in (0, K):
        for lat in ({}, {"cand_latent": 1, "cand_latent_zone": 1, "cand_latent_gate": 1}):
            b, _ = make(base, lat, chain=ch)
            if ch:
                g = torch.Generator().manual_seed(5)
                for p in (b.chain_cross.proj.weight, b.chain_cross.ff[-1].weight):
                    p.data = torch.randn(p.shape, generator=g) * 0.05
            if lat:
                with torch.no_grad():
                    b.g_lat.fill_(0.7)
            n, _ = make(new, lat, chain=ch, state=b.state_dict())
            check(list(b.state_dict()) == list(n.state_dict()) and n.config() == b.config(),
                  f"(a) chain={ch} cand_latent={bool(lat)}: state_dict keys and config() equal")
            check(same(run(b, inp), run(n, inp)), f"(a) chain={ch} cand_latent={bool(lat)}: logits and values bit-identical on {len(inp[0])} decisions")

    # (b) state_key: gate (key_bias) 0 = identical; 1 = outputs change and key_bias gets a gradient
    b, _ = make(base, chain=K)
    ob = run(b, inp)
    sk, miss = make(new, {"state_key": 1}, chain=K, state=b.state_dict())
    check(set(miss) == {"key_bias"} and float(sk.key_bias.detach().abs().sum()) == 0, f"(b) state_key: only key_bias is new, all zero (shape {tuple(sk.key_bias.shape)})")
    o0 = run(sk, inp)
    check(same(ob, o0), f"(b) state_key, key_bias = 0: bit-identical (max |d| logits, values = {maxdiff(ob, o0)})")
    sk.zero_grad()
    sub = [t[:128] for t in inp]
    l, v = run(sk, sub, grad=True)
    w = torch.randn(l.shape, generator=torch.Generator().manual_seed(1))
    (((l.clamp(min=-50) * w) * (l > -1e8)).sum() + v.sum()).backward()
    gr = sk.key_bias.grad
    check(gr is not None and float(gr.abs().sum()) > 0, f"(b) state_key: gradient on key_bias at 0 ({0 if gr is None else float(gr.abs().sum()):.3e})")
    with torch.no_grad():
        sk.key_bias.fill_(1.0)
    o1 = run(sk, inp)
    dl, dv = maxdiff(ob, o1)
    check(dl > 0 and dv > 0, f"(b) state_key, key_bias = 1: outputs change (max |d| logits {dl:.4f}, values {dv:.4f})")
    tc, tk = inp[0], inp[1]
    pairs = ((tc[:, :, None] == tc[:, None, :]) & (tc[:, :, None] > 0) & (tk[:, :, None] != tk[:, None, :])).any(-1)
    print(f"    tokens with a same-card partner in another kind: {float(pairs.float().sum() / (tk > 0).sum()):.1%} of tokens")
    # state_key together with slot_bind (both biases are summed)
    sb, _ = make(new, {"slot_bind": True, "state_key": 1}, chain=0)
    out = run(sb, [t[:16] for t in inp])
    check(bool(torch.isfinite(out[1]).all()), "(b) state_key + slot_bind builds and runs (biases summed)")

    # canon batch
    if not Path(args.canon_batch).exists():
        collect(args.canon_batch, args.decisions)
    ci = tensors(args.canon_batch)
    ck_, ak_, an_ = ci[0], ci[1], ci[2]
    print(f"canon batch: {len(ck_)} decisions, mean tokens {float((ak_ > 0).sum(1).float().mean()):.1f} "
          f"(plain batch {float((tk > 0).sum(1).float().mean()):.1f}; different games)")
    # (c) the token side, from real worker output: flags per kind, PROMPT / PICKED leftovers (test_card_state.js has the per-prompt table)
    live = ak_ > 0
    zone = torch.zeros_like(live)
    for k in ZONE_NAMES:
        zone |= ak_ == k
    flags = {n: ((an_ >> bit) & 1).bool() & zone for n, bit in (("listed", 5), ("picked", 6), ("source", 7))}
    for n, f in flags.items():
        by = {ZONE_NAMES[k]: int((f & (ak_ == k)).sum()) for k in ZONE_NAMES if int((f & (ak_ == k)).sum())}
        print(f"    {n}-flag tokens: {int(f.sum())} {by}")
    check(int(flags["listed"].sum()) > 0 and int(flags["picked"].sum()) > 0 and int(flags["source"].sum()) > 0,
          "(c) the worker's canon encoding sets listed, picked and source flags")
    print(f"    PICKED-kind tokens left: {int((ak_ == 13).sum())}; PROMPT-kind: {int((ak_ == 12).sum())} (listed cards with no zone token, sources in neither HAND nor MY_DISCARD)")
    counted = (ak_ >= 6) & (ak_ <= 10)
    check(bool((((an_ & 31) > 0) | ~counted).all()) and int(an_[counted].max() & 31) <= 31, "(c) every HAND / discard / unseen / decklist token keeps a copy count in bits 0-4")

    # (c2) canon model: flag gates 0 -> flags unread (only the aux & 31 change); gates 1 -> outputs move; gradients reach the new weights
    cm, miss = make(new, CANON, chain=K, state=b.state_dict())
    check(set(miss) == {"flag_emb", "g_flag"} and float(cm.g_flag.abs().sum()) == 0 and float(cm.flag_emb.abs().sum()) > 0,
          f"(c2) state_canon: new params {sorted(miss)}; gates 0, vectors nonzero")
    x0 = run(cm, ci)
    cm2 = make(new, CANON, chain=K, state=b.state_dict())[0]
    cm2.load_state_dict(cm.state_dict())
    with torch.no_grad():
        cm2.g_flag.fill_(1.0)
    x1 = run(cm2, ci)
    dl, dv = maxdiff(x0, x1)
    check(dl > 0 and dv > 0, f"(c2) gates 1: outputs change (max |d| logits {dl:.4f}, values {dv:.4f})")
    cm.zero_grad()
    sub = [t[:128] for t in ci]
    l, v = run(cm, sub, grad=True)
    w = torch.randn(l.shape, generator=torch.Generator().manual_seed(2))
    (((l.clamp(min=-50) * w) * (l > -1e8)).sum() + v.sum()).backward()
    check(float(cm.g_flag.grad.abs().sum()) > 0, f"(c2) gradient on g_flag at 0: {cm.g_flag.grad.tolist()}")
    # aux & 31 matters: a flag bit with all gates 0 changes nothing
    flipped = [t.clone() for t in ci]
    flipped[2] = torch.where(zone & (ak_ != 12) & (ak_ != 13), an_ | 32, an_)
    check(same(run(cm, ci), run(cm, flipped)), "(c2) gates 0: setting the listed bit on every zone token changes nothing (flags are read only through the gates)")

    # (d) canon + cand_latent + zone: a pick-from-prompt candidate gathers the tokens flagged listed
    cl, _ = make(new, CANON_LAT, chain=K, state=b.state_dict())
    cand = ci[5].view(len(ci[0]), -1, 6)[:, :-K]
    valid = torch.arange(cand.shape[1])[None] < ci[6].view(-1, 1)
    verb, card, s1, s2 = cand[..., 0], cand[..., 1], cand[..., 2], cand[..., 3]
    kept = cl.card_tokens(ck_, ak_, ak_ > 0, verb, card, s1, s2, an_)
    flag_tok = (((an_ >> 5) & 1).bool() & zone)[:, None, :]
    left_tok = (ak_ == 12)[:, None, :]
    on_flag, on_left = (kept & flag_tok).any(-1), (kept & left_tok).any(-1)
    on_energy = (kept & (ak_ == 4)[:, None, :]).any(-1)
    for name, sel in (("all pick verbs (11-15)", valid & (verb >= 11) & (verb <= 15) & (card > 0)),
                      ("pick_card (verb 11)", valid & (verb == 11) & (card > 0)), ("pick_move_energy (verb 14)", valid & (verb == 14) & (card > 0))):
        n = max(int(sel.sum()), 1)
        print(f"(d) {name}: {int(sel.sum())} candidates naming a card; listed-flag token {float((on_flag & sel).sum()) / n:.1%}, "
              f"PROMPT leftover {float((on_left & ~on_flag & sel).sum()) / n:.1%}, attached-Energy token only {float((on_energy & ~on_flag & ~on_left & sel).sum()) / n:.1%}, "
              f"any token {float((kept.any(-1) & sel).sum()) / n:.1%}")
    sel = valid & (verb == 11) & (card > 0)
    p_ok = float(((on_flag | on_left) & sel).sum()) / max(int(sel.sum()), 1)
    check(p_ok >= 0.9, f"(d) >= 90% of pick_card candidates resolve to a listed-flag token or a PROMPT leftover ({p_ok:.1%}); the rest are Choose-energy picks (ENERGY tokens)")
    sel = valid & (verb >= 11) & (verb <= 15) & (card > 0)
    check(float((kept.any(-1) & sel).sum()) / max(int(sel.sum()), 1) >= 0.99, "(d) every pick candidate naming a card finds some token")
    with torch.no_grad():
        cl.g_lat.fill_(1.0)
    cl.zero_grad()
    l, v = run(cl, [t[:128] for t in ci], grad=True)
    (((l.clamp(min=-50) * torch.randn(l.shape, generator=torch.Generator().manual_seed(3))) * (l > -1e8)).sum() + v.sum()).backward()
    check(float(cl.lat_proj.weight.grad.abs().sum()) > 0, "(d) canon + cand_latent: lat_proj gets gradient through the flagged-token gather")

    # (e) the C49-sd checkpoint through load_policy (also what ar/fixed.py start_model calls)
    from rl.gpu_matrix import load_policy, canon_of
    ref, _ = load_policy(CKPT, "cpu")
    for over, fresh_ok in ((CANON, {"flag_emb", "g_flag"}), ({"state_key": 1}, {"key_bias"}), ({**CANON, "state_key": 1}, {"flag_emb", "g_flag", "key_bias"})):
        m, _ = load_policy(CKPT, "cpu", over)
        fresh = {k for k in m.state_dict() if k not in ref.state_dict()}
        check(fresh == fresh_ok, f"(e) load_policy {over}: fresh params {sorted(fresh)}")
        check(all(m.config().get(k) == v for k, v in over.items()), "(e) config() records the keys")
        if "state_canon" not in over:
            check(same(run(ref, inp), run(m, inp)), f"(e) {over}: step 0 logits and values identical to the checkpoint")
            check(bool((run(ref, inp)[0].argmax(1) == run(m, inp)[0].argmax(1)).all()), "(e) step 0 greedy actions identical")
        else:
            lg, _ = run(m, ci)
            ok = bool(torch.isfinite(lg[lg > -1e8]).all())
            lp, _ = run(ref, ci)      # the checkpoint on the canon tokens: informational, canon is not an identity start
            agree = float((lg.argmax(1) == lp.argmax(1)).float().mean())
            check(ok, f"(e) {over}: runs on canon tokens; greedy action agrees with the unmodified model on {agree:.1%} of rows (not an identity start)")
    from rl.train import load_grown
    st = torch.load(CKPT, map_location="cpu", weights_only=False)["model"]
    gm, _ = make(new, {**CANON, "state_key": 1})
    miss = load_grown(gm, st)
    check(set(miss) == {"flag_emb", "g_flag", "key_bias"} and float(gm.flag_emb.abs().sum()) > 0 and float(gm.g_flag.abs().sum()) == 0,
          f"(e) rl.train.load_grown accepts the new weights ({sorted(miss)}), gates stay 0, flag_emb keeps its init")
    check(canon_of({0: m}) == 1 and canon_of({0: ref}) == 0, "(e) gpu_matrix.canon_of reads the config")

    # (f) remote.py: the canon guard
    from rl.remote import RemotePool
    guard = RemotePool._canon_guard

    def raises(msgs, models):
        try:
            guard(msgs, models)
        except RuntimeError as e:
            return str(e)[:70]
        return None

    cmsg = lambda **kw: {"cmd": "collect", "encoding": "tokens", **kw}
    mc, mo = load_policy(CKPT, "cpu", CANON)[0], ref
    check(raises([cmsg()], {0: mc}) is not None, "(f) canon model, command without canon: refused")
    check(raises([cmsg(canon=0)], {0: mc}) is not None, "(f) canon model, canon = 0: refused")
    check(raises([cmsg(canon=1), cmsg()], {0: mc}) is not None, "(f) canon model, one of two commands without canon: refused")
    check(raises([cmsg(canon=1)], {0: mc}) is None, "(f) canon model, canon = 1: accepted")
    check(raises([cmsg(canon=1)], {0: mo}) is not None, "(f) non-canon model, canon = 1: refused")
    check(raises([cmsg(), cmsg(canon=0)], {0: mo}) is None, "(f) non-canon model, no canon: accepted")
    check(raises([cmsg(canon=1)], {0: mc, 1: mo}) is not None, "(f) canon and non-canon models in one round: refused")
    check(raises([{"cmd": "info"}], {0: mc}) is None, "(f) a command that plays no tokens (info) is not checked")
    pool = object.__new__(RemotePool)           # collect() runs the guard before it sends anything
    try:
        pool.collect([cmsg()], {0: mc}, "cpu")
        check(False, "(f) RemotePool.collect with a mismatched command raises before sending")
    except RuntimeError as e:
        check("canon" in str(e), "(f) RemotePool.collect with a mismatched command raises before sending")
    print("\nALL PASS" if not FAIL else f"\n{len(FAIL)} FAILED: {FAIL}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
