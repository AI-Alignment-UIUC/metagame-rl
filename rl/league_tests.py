"""Checks of the agent-conditioned network used by the league (log #53).
Run: .venv/Scripts/python -m rl.league_tests [checkpoint]

- a population network loaded from a plain checkpoint plays exactly as that checkpoint, for every
  agent (embedding zero, value heads copied from the base head)
- per-row agent ids give each row its agent's output; agent=None is agent `fixed_agent`
- changing one agent changes only that agent's rows
- copy_agent makes one agent a copy of another
- the ONNX export of one agent matches PyTorch for that agent
- AgentView requests of one network are served in one forward pass with the same outputs as
  separate passes (rl/remote.py)
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

from rl.token_model import build_token_model, export_token_onnx

ROOT = Path(__file__).resolve().parent.parent


def build(cfg, n_agents):
    return build_token_model(str(ROOT / "notes/data/cards/pool.json"), str(ROOT / "notes/data/cards/text_emb.npy"),
                             cfg["n_names"], cfg["glob_f"], cfg["slot_f"], cfg["max_tok"], cfg["max_cand"],
                             d=cfg["d"], layers=cfg["layers"], heads=cfg["heads"],
                             count_features=cfg.get("count_features", False), cross_layers=cfg.get("cross_layers", 1),
                             cand_self=cfg.get("cand_self", 0), n_agents=n_agents)


def fake_states(m, B, rng):
    """Token inputs shaped like env/tokens.js output (random content, valid ranges)."""
    T, M = m.max_tok, m.max_cand
    n_cards = m.card_feats.shape[0]
    L = rng.integers(20, T, size=B)
    kind = np.zeros((B, T), np.uint8)
    for b in range(B):
        kind[b, :L[b]] = rng.integers(1, 16, size=L[b])
    card = (rng.integers(0, n_cards, size=(B, T)) * (kind > 0)).astype(np.int16)
    aux = (rng.integers(0, 30, size=(B, T)) * (kind > 0)).astype(np.uint8)
    glob = rng.integers(0, 49, size=(B, m.glob_f)).astype(np.uint8)
    slots = rng.integers(0, 49, size=(B, 12 * m.slot_f)).astype(np.uint8)
    cand = np.stack([rng.integers(0, 32, size=(B, M)), rng.integers(0, n_cards, size=(B, M)),
                     rng.integers(0, 16, size=(B, M)), rng.integers(0, 16, size=(B, M)),
                     rng.integers(0, m.cfg["n_names"] + 1, size=(B, M)), rng.integers(0, 64, size=(B, M))], -1)
    cand = cand.reshape(B, M * 6).astype(np.int16)
    n_cand = rng.integers(2, M + 1, size=B).astype(np.int32)
    return [torch.from_numpy(x) for x in (card, kind, aux, glob, slots, cand, n_cand)]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ckpt = argv[0] if argv else "runs/pilot-v2/model_it00349.pt"
    st = torch.load(ROOT / ckpt, map_location="cpu")
    cfg = st["config"]
    failures = []
    rng = np.random.default_rng(0)
    torch.manual_seed(0)

    base = build(cfg, 0)
    base.load_state_dict(st["model"])
    base.eval()
    K = 6
    pop = build(cfg, K)
    missing, unexpected = pop.load_state_dict(st["model"], strict=False)
    assert not unexpected, unexpected
    assert all(k.startswith(("agent_emb.", "value_heads.")) for k in missing), missing
    pop.init_agents_from_base()
    pop.eval()

    x = fake_states(base, 64, rng)
    ids = torch.from_numpy(rng.integers(0, K, size=64))
    with torch.no_grad():
        lb, vb = base(*x)
        lp, vp = pop(*x, agent=ids)
        ln, vn = pop(*x)
    if not (torch.allclose(lb, lp, atol=1e-5) and torch.allclose(vb, vp, atol=1e-6)):
        failures.append(f"population differs from its base checkpoint: logits {float((lb - lp).abs().max()):.2e}, "
                        f"values {float((vb - vp).abs().max()):.2e}")
    if not (torch.allclose(lb, ln, atol=1e-5) and torch.allclose(vb, vn, atol=1e-6)):
        failures.append("agent=None differs from the base checkpoint")

    with torch.no_grad():                         # make agent 2 different from the rest
        pop.agent_emb.weight[2].normal_(0, 0.5)
        pop.value_heads[2][-1].weight.normal_(0, 0.5)
        pop.value_heads[2][-1].bias.fill_(0.3)
        l2, v2 = pop(*x, agent=ids)
        pop.fixed_agent = 2
        lf, vf = pop(*x)
        la, va = pop(*x, agent=torch.full((64,), 2))
        pop.fixed_agent = 0
    same = ids != 2
    if not (torch.allclose(l2[same], lb[same], atol=1e-5) and torch.allclose(v2[same], vb[same], atol=1e-6)):
        failures.append("changing agent 2 changed other agents' rows")
    if torch.allclose(l2[~same], lb[~same], atol=1e-3) or torch.allclose(v2[~same], vb[~same], atol=1e-3):
        failures.append("changing agent 2 did not change its rows")
    if not (torch.allclose(lf, la, atol=1e-5) and torch.allclose(vf, va, atol=1e-6)):
        failures.append("fixed_agent=2 differs from agent ids all 2")

    with torch.no_grad():
        pop.copy_agent(2, 4)
        l4, v4 = pop(*x, agent=torch.full((64,), 4))
    if not (torch.allclose(l4, la, atol=1e-5) and torch.allclose(v4, va, atol=1e-6)):
        failures.append("copy_agent(2, 4) does not make agent 4 play as agent 2")

    import onnxruntime as ort
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "agent2.onnx")
        pop.fixed_agent = 2
        export_token_onnx(pop, path)
        pop.fixed_agent = 0
        sess = ort.InferenceSession(path)
        names = [i.name for i in sess.get_inputs()]
        lo, vo = sess.run(None, {n: t.numpy() for n, t in zip(names, x)})
    if not (np.allclose(lo, la.numpy(), atol=2e-4) and np.allclose(vo, va.numpy(), atol=2e-5)):
        failures.append(f"ONNX export of agent 2 differs from PyTorch: logits {np.abs(lo - la.numpy()).max():.2e}")

    # Merged serving: AgentView slots of one network served in one pass (rl/remote.py).
    from rl.remote import AgentView, RemotePool
    pool = RemotePool.__new__(RemotePool)
    pool.capture, pool.pace = None, 0.0
    sent = {}
    pool._send = lambda i, kind, payload: sent.setdefault(i, []).append(payload)
    from rl.remote import TOKEN_INPUTS, unpack_arrays
    reqs = []
    for w, (lo_, hi_, slot) in enumerate([(0, 20, 1), (20, 40, 2), (40, 64, 1)]):
        n = hi_ - lo_
        arrays = {k: t[lo_:hi_].numpy().reshape(n, -1) if k != "n_cand" else t[lo_:hi_].numpy()
                  for k, t in zip(TOKEN_INPUTS, x)}
        legal = [np.arange(int(c)) for c in arrays["n_cand"]]
        arrays["legal_offsets"] = np.concatenate([[0], np.cumsum([len(l) for l in legal])]).astype(np.int32)
        arrays["legal_ids"] = np.concatenate(legal).astype(np.int32)
        reqs.append((w, {"id": w, "slot": slot, "n": n, "encoding": "tokens", "greedy": True}, arrays))
    models = {1: AgentView(pop, 0), 2: AgentView(pop, 2)}
    pool._serve_batches(reqs, models, "cpu")
    got_v = {}
    for w, payloads in sent.items():
        h, a = unpack_arrays(payloads[0])
        got_v[w] = a["value"]
    want = torch.cat([vb[0:20], va[20:40], vb[40:64]]).numpy()
    if not np.allclose(np.concatenate([got_v[0], got_v[1], got_v[2]]), want, atol=1e-5):
        failures.append("merged AgentView serving differs from per-agent forward passes")

    if failures:
        print("FAIL\n  " + "\n  ".join(failures))
        sys.exit(1)
    print(f"PASS: population of {K} agents from {ckpt}")


if __name__ == "__main__":
    main()
