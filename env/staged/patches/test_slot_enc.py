"""Tests for slot_enc.patch (per-slot encoder options, "slotEnc"; rl/gpu_matrix.py slot_enc_of, rl/remote.py enc_of and _canon_guard).
Apply card_latent.patch, card_state.patch, then slot_enc.patch on a tree at 77fbae0. The encoder-level checks are in test_slot_enc.js.

Run (CPU, no GPU; the trees need the ryuu-play and node_modules junctions to the main repo's):
  CUDA_VISIBLE_DEVICES= SLOTENC_BASE=<tree at 77fbae0 + card_latent + card_state> PYTHONPATH=<tree with all three patches> \
      <main repo>/.venv/Scripts/python.exe test_slot_enc.py

(a) one model, and two models of the same config, play the same games on the patched tree and on SLOTENC_BASE: identical results.
(c) GpuMatrix.play with models {0: canon, 1: plain} (and {0: canon, 1: plain with chain 4}) runs without the guard raising; every
    batch a model is served is checked to be in that model's own encoding (forward pre-hooks on the served models).
(d) the guard still refuses mixed models without slotEnc (and with a slotEnc that does not match them), and accepts matching ones.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

MAIN = Path(os.environ.get("CARDREF_MAIN", "C:/Users/evanc/Desktop/333/metagame-rl"))
BASE = os.environ.get("SLOTENC_BASE", "")
CKPT = str(MAIN / "runs/pilot/C49-sd/model_it00199.pt")
PICKED, HAND, LAST_ZONE = 13, 6, 13
FAIL = []


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        FAIL.append(msg)


def decks_of(root, n=2):
    out = subprocess.run(["node", "-e", f"console.log(JSON.stringify(require('./env/decks.js').archivedDecks().slice(0,{n})))"],
                         cwd=root, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def child(mode):
    """Plays a few games and prints the results (run in the patched tree and in the base tree)."""
    import torch
    from rl.gpu_matrix import GpuMatrix, load_policy
    from rl.remote import RemotePool, ROOT
    torch.manual_seed(0)
    a, _ = load_policy(CKPT, "cpu", {"state_canon": 1} if mode == "canon" else None)
    b, _ = load_policy(CKPT, "cpu", {"state_canon": 1} if mode == "canon" else None)
    pool = RemotePool(2)
    try:
        gm = GpuMatrix.attach(a, pool, 2, device="cpu", concurrency=8)
        kw = {"slots": [0, 1], "models": {0: a, 1: b}} if mode == "twin" else {}
        gm.play(decks_of(ROOT), 8, 5, pairs=[(0, 1)], round_turns=30, **kw)
        print("RESULT " + json.dumps(sorted([r["seed"], r["winner"], r["ending"], r["steps"], r["turns"]] for r in gm.results)))
    finally:
        pool.close()


def run_child(tree, mode):
    env = {**os.environ, "PYTHONPATH": str(tree), "CUDA_VISIBLE_DEVICES": ""}
    out = subprocess.run([sys.executable, __file__, "--child", mode], env=env, capture_output=True, text=True, cwd=tree)
    lines = [l for l in out.stdout.splitlines() if l.startswith("RESULT ")]
    return lines[0][7:] if lines else "ERROR " + out.stderr[-600:]


def main():
    import torch
    from rl.gpu_matrix import GpuMatrix, load_policy, slot_enc_of
    from rl.remote import RemotePool, ROOT

    # (a) unchanged without slotEnc: the same results as the tree without this patch
    if BASE:
        root = Path(ROOT)
        for mode in ("plain", "canon", "twin"):
            p, b = run_child(root, mode), run_child(BASE, mode)
            check(not p.startswith("ERROR") and p == b, f"(a) {mode}: results of 8 games equal the base tree's ({p[:60]}...)" if p == b
                  else f"(a) {mode}: patched {p[:200]} vs base {b[:200]}")
    else:
        print("(a) skipped: SLOTENC_BASE not set")

    # (c) mixed models through GpuMatrix.play
    for label, over in (("canon vs plain", {}), ("canon (chain 0) vs plain chain 4", {"chain": 4})):
        torch.manual_seed(0)
        canon, _ = load_policy(CKPT, "cpu", {"state_canon": 1})
        plain, _ = load_policy(CKPT, "cpu", over or None)
        check(slot_enc_of({0: canon, 1: plain}) == {"0": {"canon": 1, "chain": 0, "history": 0}, "1": {"canon": 0, "chain": over.get("chain", 0), "history": 0}},
              f"(c) {label}: slot_enc_of reads each model's config: {slot_enc_of({0: canon, 1: plain})}")
        rec = {"canon": [], "plain": []}
        for name, m in (("canon", canon), ("plain", plain)):
            m.register_forward_pre_hook(lambda mod, args, n=name: rec[n].append((args[1].cpu().numpy(), args[2].cpu().numpy(), args[5].cpu().numpy())))
        pool = RemotePool(2)
        try:
            gm = GpuMatrix.attach(canon, pool, 2, device="cpu", concurrency=8)
            try:
                gm.play(decks_of(ROOT), 8, 5, pairs=[(0, 1)], slots=[0, 1], models={0: canon, 1: plain}, round_turns=30)
                raised = None
            except RuntimeError as e:
                raised = str(e)
        finally:
            pool.close()
        check(raised is None, f"(c) {label}: play completed, guard did not raise" + (f" ({raised[:150]})" if raised else ""))
        check(len(gm.results) == 8 and not any(r.get("error") for r in gm.results), f"(c) {label}: {len(gm.results)} games, no engine error")
        rows = {n: sum(len(k) for k, _, _ in rec[n]) for n in rec}
        check(all(rows.values()), f"(c) {label}: both models were served (rows canon {rows['canon']}, plain {rows['plain']})")
        zone = lambda k: (k >= HAND) & (k <= LAST_ZONE)
        c_picked = sum(int((k == PICKED).sum()) for k, _, _ in rec["canon"])
        c_flags = sum(int((zone(k) & ((a & 224) > 0)).sum()) for k, a, _ in rec["canon"])
        p_picked = sum(int((k == PICKED).sum()) for k, _, _ in rec["plain"])
        p_flags = sum(int((zone(k) & ((a & 224) > 0)).sum()) for k, a, _ in rec["plain"])
        check(c_picked == 0 and c_flags > 0, f"(c) {label}: the canon model saw no PICKED token and {c_flags} canon flags")
        check(p_flags == 0 and p_picked > 0, f"(c) {label}: the plain model saw no canon flag and {p_picked} PICKED tokens")
        if over:       # the chain-4 model keeps the last 4 candidate rows of its batches (trim_inputs): its own chain rows
            tail = sum(int((c[:, -6 * over["chain"]:] != 0).any(1).sum()) for _, _, c in rec["plain"])
            check(tail > 0, f"(c) {label}: the chain-4 model was served {tail} rows with chain rows")

    # (d) the guard
    from rl.remote import RemotePool as RP
    canon, _ = load_policy(CKPT, "cpu", {"state_canon": 1})
    plain, _ = load_policy(CKPT, "cpu")
    models = {0: canon, 1: plain}
    msg = lambda **kw: {"cmd": "games", "encoding": "tokens", "canon": 1, **kw}

    def refuses(m):
        try:
            RP._canon_guard([m], models)
            return False
        except RuntimeError:
            return True
    check(refuses(msg()), "(d) mixed models without slotEnc: refused")
    check(refuses(msg(slotEnc={"0": {"canon": 1, "chain": 0, "history": 0}})), "(d) slotEnc missing a slot: refused")
    check(refuses(msg(slotEnc={"0": {"canon": 1, "chain": 0, "history": 0}, "1": {"canon": 1, "chain": 0, "history": 0}})),
          "(d) slotEnc with the wrong canon for a slot: refused")
    check(not refuses(msg(slotEnc=slot_enc_of(models))), "(d) slotEnc covering every slot with its model's options: accepted")
    check(refuses({"cmd": "games", "encoding": "tokens", "canon": 0, "slotEnc": slot_enc_of(models)}),
          "(d) the command-level canon flag is still checked (canon 0 with a canon model in use): refused")
    check(not refuses({"cmd": "games", "encoding": "identity"}), "(d) a non-token command is not touched")
    print("ALL PASS" if not FAIL else f"FAILED {len(FAIL)}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        child(sys.argv[2])
    else:
        main()
