"""BENCH arm training (runs/probe/BENCH/record.md): ar/train.py's recipe on the bench matchups, wall clock as the budget.

As ar_milestone.py's training step (its functions, imported): a temporary worktree of an ar/ commit, the worktree's
fixed module patched (TIME_BUDGET = --minutes, ITERS huge, practice_matchups -> --matchups), train.py text-patched to be
pausable on runs/GPU-PAUSE (resume with --resume-from), optionally MODEL_OVERRIDES replaced (--model-overrides JSON).
Writes <out>/pilot.pt and <out>/result.json; no scoring (bench_eval.py does that). Nothing under ar/ is edited.
Exit codes: 0 done, 1 crash, 4 refused, 5 paused.

Run:  RL_GPU_SHARE=0.1 PYTHONPATH=. .venv/Scripts/python notes/scripts/bench_train.py --name <arm> --seed 1
"""
import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ar_milestone import ROOT, Paused, blocked, git, load_fixed, log, patch_train, remove_worktree, train   # noqa: E402

BENCH = ROOT / "runs" / "probe" / "BENCH"

# BENCH-P6 (runs/probe/BENCH/P6/record.md), inserted into the worktree's train.py by --p6, after its GAE function.
P6 = '''

_gae_p6 = advantages


def advantages(batch: dict, gamma: float, lam: float):
    """BENCH-P6: at a prompt row resolving the seat's own Trainer (prompt open, glob slot 48 = 0, and the seat's last
    main-phase action a Trainer play, verb 5), the advantage is the Monte Carlo return minus V (lambda 1 there). Every
    other row's advantage, and every value target, stay GAE's."""
    adv, ret = _gae_p6(batch, gamma, lam)
    value, reward, done, traj = batch["value"], batch["reward"], batch["done"], batch["traj"]
    T = len(value)
    prompt = batch["obs.glob"].reshape(T, -1)[:, 48] == 0
    verb = batch["obs.cand"].reshape(T, -1, 6)[np.arange(T), batch["action"].astype(np.int64), 0]
    own, last = np.zeros(T, dtype=bool), {}
    for t in range(T):
        if prompt[t]:
            own[t] = last.get(traj[t], False)
        else:
            last[traj[t]] = verb[t] == 5
    g, nxt = np.zeros(T, dtype=np.float32), {}
    for t in range(T - 1, -1, -1):
        g[t] = reward[t] + gamma * (0.0 if done[t] else nxt.get(traj[t], 0.0))
        nxt[traj[t]] = g[t]
    sd = float(adv[own].std()) if own.any() else 0.0
    adv = adv.copy()
    adv[own] = g[own] - value[own]
    print(f"p6 rows {int(own.sum())} of {T}; their adv sd GAE {sd:.3f} MC {float(adv[own].std()) if own.any() else 0.0:.3f}",
          flush=True)
    return adv, ret

'''

# BENCH-P5 (runs/probe/BENCH/P5/record.md), inserted by --p5 after the GAE function. wrap_p5 (below) leaves the iteration's
# branched rows in RemotePool.p5["rows"] (global rollout rows: k, pp, other, q = [Q(pp), Q(other)]).
P5 = '''

_gae_p5 = advantages


def advantages(batch: dict, gamma: float, lam: float):
    """BENCH-P5: at a branched row whose taken action is one of the two candidates, the advantage is Q(taken) minus the mean
    of the two Qs; those rows are then scaled together by sd(GAE there) / sd(the centred values). Every other row's
    advantage, and every value target, stay GAE's."""
    import json as _json
    import time as _time
    from rl.remote import RemotePool
    adv, ret = _gae_p5(batch, gamma, lam)
    st, T = RemotePool.p5, len(adv)
    rows, off, ids, act = st["rows"], batch["legal_offsets"], batch["legal_ids"], batch["action"]
    taken = [r for r in rows if act[r["k"]] in (r["pp"], r["other"])]
    aligned = sum(1 for r in rows if {r["pp"], r["other"]} <= set(ids[off[r["k"]]:off[r["k"] + 1]].tolist()))
    idx = np.array([r["k"] for r in taken], dtype=np.int64)
    new = np.array([r["q"][0 if act[r["k"]] == r["pp"] else 1] - sum(r["q"]) / 2 for r in taken], dtype=np.float32)
    sd_g, sd_b, scale = (float(adv[idx].std()) if len(idx) else 0.0), (float(new.std()) if len(idx) else 0.0), None
    if len(idx) >= 2 and sd_g > 0 and sd_b > 0:
        scale = sd_g / sd_b
        new = new * scale
    adv = adv.copy()
    if len(idx):
        adv[idx] = new
    rec = {"iteration": st["it"], "T": T, "eligible": st["eligible"], "branched": len(rows), "taken_among": len(taken),
           "aligned": aligned, "sd_gae": round(sd_g, 4), "sd_branched": round(sd_b, 4),
           "scale": None if scale is None else round(scale, 4), "scaled": scale is not None,
           "share_pp": round(sum(1 for r in rows if act[r["k"]] == r["pp"]) / len(rows), 4) if rows else None,
           "frac": st["frac"], "branch_s": round(st["branch_s"], 1), "collect_s": round(st["collect_s"], 1),
           "share_collect": round(st["branch_s"] / max(_time.time() - st["t0"], 1e-9), 3), "share_prev_iter": st["prev_share"]}
    print("p5 " + _json.dumps(rec), flush=True)
    with (st["out"] / "p5.jsonl").open("a", encoding="utf-8") as f:
        f.write(_json.dumps(rec) + "\\n")
    return adv, ret

'''


def wrap_p5(out: Path, komath: int = 0):
    """--p5: each RemotePool.collect call asks the workers for ppBranch (env/remote_worker.js ppCatch) and leaves the rows,
    shifted to the concatenated rollout's row numbers, in RemotePool.p5. If the iteration before spent over 0.6 of its wall
    time in the branches (the busiest worker's branch seconds), ppFrac is 0.5 from then on (a seeded coin in the worker), logged.
    komath N (BENCH-P5b): every N-th iteration also asks for C110's koMath labels (env/remote_worker.js koCatch) and appends the
    branched difference Q(PlusPower) - Q(other) by label (conversion, KO anyway, no-KO) to <out>/p5_komath.jsonl. Returns the undo."""
    import time
    from rl.remote import RemotePool
    orig, prev = RemotePool.collect, {"t": None, "branch": 0.0}
    RemotePool.p5 = st = {"out": out, "it": -1, "frac": 1.0, "prev_share": None}

    def collect(self, msgs, models, device):
        now = time.time()
        if prev["t"] is not None:      # the whole of the previous iteration (collect, update, the rest) is known now
            st["prev_share"] = round(prev["branch"] / (now - prev["t"]), 3)
            if st["prev_share"] > 0.6 and st["frac"] == 1.0:
                st["frac"] = 0.5
                print(f"p5: branch share {st['prev_share']} over 0.6: branching half the eligible decisions from now on", flush=True)
        st["it"] += 1
        st["t0"] = prev["t"] = now
        ko = bool(komath) and st["it"] % komath == 0
        msgs = [{**m, "ppBranch": 1, "ppFrac": st["frac"], **({"koMath": 1} if ko else {})} if m.get("cmd") == "collect" else m
                for m in msgs]
        replies = orig(self, msgs, models, device)
        st["collect_s"] = time.time() - now
        rows, base, st["eligible"], st["branch_s"], kos = [], 0, 0, 0.0, {}
        for r in replies:
            pb = r.get("ppBranch") or {}
            rows += [{**x, "k": x["k"] + base} for x in pb.get("rows", [])]
            st["eligible"] += pb.get("eligible", 0)
            st["branch_s"] = max(st["branch_s"], pb.get("seconds", 0.0))
            kos.update({x["k"] + base: x["atk"] for x in r.get("koMath") or []})
            base += r["transitions"]
        st["rows"], prev["branch"] = rows, st["branch_s"]
        if ko:
            by = {"conv": [], "ko": [], "noko": []}
            for x in rows:
                hit = [a for a in kos.get(x["k"], []) if a["left"] is not None]
                if x["k"] in kos:
                    lab = ("ko" if any(a["dmg"] >= a["left"] for a in hit) else
                           "conv" if any(a["left"] - 10 <= a["dmg"] < a["left"] for a in hit) else "noko")
                    by[lab].append(x["q"][0] - x["q"][1])
            rec = {"iteration": st["it"], "collect_s": round(st["collect_s"], 1), "labelled": len(kos),
                   **{k: {"n": len(v), "delta_mean": round(float(sum(v) / len(v)), 4) if v else None,
                          "delta_se": round(float((sum((d - sum(v) / len(v)) ** 2 for d in v) / max(len(v) - 1, 1) / len(v)) ** 0.5), 4)
                          if len(v) > 1 else None} for k, v in by.items()}}
            with open(out / "p5_komath.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + chr(10))
            print("p5 komath", json.dumps(rec), flush=True)
        return replies

    RemotePool.collect = collect
    return lambda: setattr(RemotePool, "collect", orig)


# BENCH-P8 (runs/probe/BENCH/P8/record.md), inserted by --p8 after the GAE function. wrap_p8 (below) leaves the iteration's
# branched rows in RemotePool.p8["rows"] (global rollout rows: k, greedy, u, card {u, g}, q = [Q(greedy), Q(u)]).
P8 = '''

_gae_p8 = advantages


def advantages(batch: dict, gamma: float, lam: float):
    """BENCH-P8: at a branched row whose taken action is greedy or u, the advantage is Q(taken) minus the mean of the two Qs;
    those rows are then scaled together by sd(GAE there) / sd(the centred values), as P5's. Every other row's advantage, and
    every value target, stay GAE's. Logs <out>/p8.jsonl with the per-Trainer branched counts and mean Q(u) - Q(greedy)."""
    import json as _json
    import time as _time
    from rl.remote import RemotePool
    adv, ret = _gae_p8(batch, gamma, lam)
    st, T = RemotePool.p8, len(adv)
    rows, off, ids, act = st["rows"], batch["legal_offsets"], batch["legal_ids"], batch["action"]
    taken = [r for r in rows if act[r["k"]] in (r["greedy"], r["u"])]
    aligned = sum(1 for r in rows if {r["greedy"], r["u"]} <= set(ids[off[r["k"]]:off[r["k"] + 1]].tolist()))
    idx = np.array([r["k"] for r in taken], dtype=np.int64)
    new = np.array([r["q"][0 if act[r["k"]] == r["greedy"] else 1] - sum(r["q"]) / 2 for r in taken], dtype=np.float32)
    sd_g, sd_b, scale = (float(adv[idx].std()) if len(idx) else 0.0), (float(new.std()) if len(idx) else 0.0), None
    if len(idx) >= 2 and sd_g > 0 and sd_b > 0:
        scale = sd_g / sd_b
        new = new * scale
    adv = adv.copy()
    if len(idx):
        adv[idx] = new
    cards = {}
    for r in rows:
        for role, name in (("u", r["card"]["u"]), ("greedy", r["card"]["g"])):
            if name:
                c = cards.setdefault(name, {"u": [], "greedy": []})
                c[role].append(r["q"][1] - r["q"][0])
    mean = lambda v: round(float(sum(v) / len(v)), 4) if v else None
    rec = {"iteration": st["it"], "T": T, "eligible": st["eligible"], "branched": len(rows), "replaced": len(taken),
           "aligned": aligned, "sd_gae": round(sd_g, 4), "sd_branched": round(sd_b, 4),
           "scale": None if scale is None else round(scale, 4), "frac": st["frac"], "branch_s": round(st["branch_s"], 1),
           "collect_s": round(st["collect_s"], 1),
           "share_collect": round(st["branch_s"] / max(_time.time() - st["t0"], 1e-9), 3), "share_prev_iter": st["prev_share"],
           "cards": {n: {"n_u": len(c["u"]), "delta_u": mean(c["u"]), "n_greedy": len(c["greedy"]), "delta_greedy": mean(c["greedy"])}
                     for n, c in sorted(cards.items())}}
    print("p8 " + _json.dumps(rec), flush=True)
    with (st["out"] / "p8.jsonl").open("a", encoding="utf-8") as f:
        f.write(_json.dumps(rec) + "\\n")
    return adv, ret

'''

# BENCH-P9 (runs/probe/BENCH/P9/record.md), inserted by --turn-gamma after the GAE function: a per-game-turn discount.
P9 = '''

_gae_p9 = advantages
TURN_GAMMA = None


def advantages(batch: dict, gamma: float, lam: float):
    """BENCH-P9: GAE with a per-turn discount. Between a seat's decision t and its next decision, the discount is
    gamma * TURN_GAMMA ** (game turns between them; glob byte 0 is the game turn, env/tokens.js): 1 within a turn, usually
    TURN_GAMMA ** 2 to the seat's next turn. Lambda unchanged; the value targets are adv + value, as GAE's. Logs the largest
    change from the undiscounted advantages (exactly 0 at TURN_GAMMA 1.0: the identity check)."""
    value, reward, done, traj = batch["value"], batch["reward"], batch["done"], batch["traj"]
    turn = batch["obs.glob"].reshape(len(value), -1)[:, 0].astype(np.int64)
    adv = np.zeros(len(value), dtype=np.float32)
    nxt_v, nxt_a, nxt_t = {}, {}, {}
    for t in range(len(value) - 1, -1, -1):
        k = traj[t]
        v1, a1 = (0.0, 0.0) if done[t] else (nxt_v.get(k, 0.0), nxt_a.get(k, 0.0))
        g = gamma * TURN_GAMMA ** max(int(nxt_t.get(k, turn[t])) - int(turn[t]), 0)
        adv[t] = reward[t] + g * v1 - value[t] + g * lam * a1
        nxt_v[k], nxt_a[k], nxt_t[k] = value[t], adv[t], turn[t]
    base = _gae_p9(batch, gamma, lam)[0]
    d = np.abs(adv - base)
    print(f"p9 turn-gamma {TURN_GAMMA}: |adv - adv(gamma_T 1)| max {float(d.max()):.6g} mean {float(d.mean()):.6g}; "
          f"identical {bool(np.array_equal(adv, base))}", flush=True)
    return adv, adv + value

'''

# BENCH-P10 (runs/probe/BENCH/P10/record.md), inserted by --p10-eps after the GAE function; wrap_p10 (below) forces the rows.
P10 = '''

_gae_p10 = advantages


def advantages(batch: dict, gamma: float, lam: float):
    """BENCH-P10: GAE with the trace cut at forced rows (batch["sampled"] 0, wrap_p10's override). A row whose next decision
    in its trajectory was forced bootstraps from V there with no trace across it (lambda 0 across the forced action); the
    forced row and every later row keep their own GAE, so their value targets are the returns that actually follow. With no
    forced rows this is train.py's GAE exactly (logged), and the forced count is checked against the server's."""
    from rl.remote import RemotePool
    value, reward, done, traj = batch["value"], batch["reward"], batch["done"], batch["traj"]
    forced = batch["sampled"] == 0 if "sampled" in batch else np.zeros(len(value), dtype=bool)
    adv = np.zeros(len(value), dtype=np.float32)
    nxt_v, nxt_a, nxt_f, cut = {}, {}, {}, 0
    for t in range(len(value) - 1, -1, -1):
        k = traj[t]
        f1 = not done[t] and bool(nxt_f.get(k, False))
        cut += f1
        v1, a1 = (0.0, 0.0) if done[t] else (nxt_v.get(k, 0.0), 0.0 if f1 else nxt_a.get(k, 0.0))
        adv[t] = reward[t] + gamma * v1 - value[t] + gamma * lam * a1
        nxt_v[k], nxt_a[k], nxt_f[k] = value[t], adv[t], forced[t]
    base = _gae_p10(batch, gamma, lam)[0]
    srv = getattr(RemotePool, "p10", {}).get("last_forced")
    print(f"p10 forced {int(forced.sum())} of {len(value)} rows (server {srv}); trace cut before {cut}; "
          f"|adv - GAE| max {float(np.abs(adv - base).max()):.6g}; identical {bool(np.array_equal(adv, base))}", flush=True)
    return adv, adv + value

'''

# --p10-eps: ppo_update's anchors and replacements. With no forced row in the batch (pol None) every replaced line runs as
# train.py's; with some, forced rows take no policy loss and no KL stat, the policy term is the mean over the minibatch's
# policy rows and the advantages normalise over them (rl/train.py's handling of unsampled rows); value and entropy use every row.
P10_UPDATE = [
    ("    adv = (adv - adv.mean()) / (adv.std() + 1e-8)\n",
     "    pol = torch.from_numpy(batch[\"sampled\"] != 0).to(device) if \"sampled\" in batch and (batch[\"sampled\"] == 0).any() else None\n"
     "    if pol is None:   # --p10-eps: no forced rows, train.py's update exactly\n"
     "        adv = (adv - adv.mean()) / (adv.std() + 1e-8)\n"
     "    else:\n"
     "        adv = (adv - adv[pol].mean()) / (adv[pol].std() + 1e-8)\n"
     "    print(f\"p10 policy mask: {'off (no forced rows)' if pol is None else f'{int((~pol).sum())} forced rows of {T} masked'}\", flush=True)\n"),
    ("        out = {k: 0.0 for k in stats}\n",
     "        out = {k: 0.0 for k in stats}\n"
     "        npol = None if pol is None else pol[idx].sum().clamp(min=1).float()   # --p10-eps\n"),
    ("            pi_loss = -torch.min(ratio * adv[j], ratio.clamp(1 - CLIP, 1 + CLIP) * adv[j]).mean()\n"
     "            v_loss = ((v - ret[j]) ** 2).mean()\n"
     "            loss = w * (pi_loss + VF * v_loss - ENT * entropy)\n",
     "            if pol is None:\n"
     "                pi_loss = -torch.min(ratio * adv[j], ratio.clamp(1 - CLIP, 1 + CLIP) * adv[j]).mean()\n"
     "                v_loss = ((v - ret[j]) ** 2).mean()\n"
     "                loss = w * (pi_loss + VF * v_loss - ENT * entropy)\n"
     "            else:   # --p10-eps: the policy term over the minibatch's policy rows\n"
     "                pj = pol[j].float()\n"
     "                pi_loss = (-torch.min(ratio * adv[j], ratio.clamp(1 - CLIP, 1 + CLIP) * adv[j]) * pj).sum() / npol\n"
     "                v_loss = ((v - ret[j]) ** 2).mean()\n"
     "                loss = pi_loss + w * (VF * v_loss - ENT * entropy)\n"),
    ("                out[\"pi_loss\"] += w * pi_loss.item()\n",
     "                out[\"pi_loss\"] += (w if pol is None else 1.0) * pi_loss.item()\n"),
    ("                out[\"kl\"] += w * (old_logp[j] - logp).mean().item()\n",
     "                out[\"kl\"] += w * (old_logp[j] - logp).mean().item() if pol is None else \\\n"
     "                    ((old_logp[j] - logp) * pj).sum().item() / float(npol)\n"),
]


def wrap_p10(out: Path, eps: float, seed: int):
    """--p10-eps: at each served sampled row (not greedy, not a search's topk request) whose legal options include a Trainer
    play (candidate verb 5, env/tokens.js VERB.trainer; the pool has no Stadiums), with probability eps the response's action
    becomes a uniformly chosen legal Trainer play, its logp 0 (unused) and its sampled flag 0, which env/runner.js records into
    the rollout (batch["sampled"]). Its own RNG, so eps 0 draws nothing and every response passes byte-identical (counted).
    Each iteration logs a `p10` line and <out>/p10.jsonl. Returns the undo."""
    import numpy as np
    from rl import remote as R
    orig_collect, orig_serve = R.RemotePool.collect, R.RemotePool._serve_batches
    rng = np.random.default_rng(10_000 + seed)
    R.RemotePool.p10 = st = {"it": 0, "last_forced": None}
    cnt = {}

    def serve(self, requests, models, device):
        plan = {}
        for i, h, a in requests:
            if h.get("greedy") or h.get("topk") or h.get("encoding") != "tokens":
                continue
            n, off, ids = h["n"], a["legal_offsets"], a["legal_ids"]
            cand = a["cand"].reshape(n, -1, 6)
            cnt["rows"] += n
            for r in range(n):
                legal = ids[off[r]:off[r + 1]].astype(np.int64)
                tr = legal[cand[r, legal, 0] == 5]
                if len(tr):
                    cnt["eligible"] += 1
                    if eps > 0 and rng.random() < eps:
                        plan.setdefault((i, h["id"]), {})[r] = int(tr[rng.integers(len(tr))])
        orig_send = self._send

        def send(i, kind, payload):
            if kind == R.RESPONSE:
                cnt["payloads"] += 1
                hdr, arrs = R.unpack_arrays(payload)
                p = plan.get((i, hdr["id"]))
                if p:
                    arrs = {k: v.copy() for k, v in arrs.items()}
                    for r, act in p.items():
                        arrs["action"][r], arrs["logp"][r], arrs["sampled"][r] = act, 0.0, 0
                    cnt["forced"] += len(p)
                    cnt["changed"] += 1
                    payload = R.pack_arrays({k: v for k, v in hdr.items() if k != "arrays"}, list(arrs.items()))
            orig_send(i, kind, payload)

        self._send = send
        try:
            orig_serve(self, requests, models, device)
        finally:
            del self._send

    def collect(self, msgs, models, device):
        cnt.update(rows=0, eligible=0, forced=0, payloads=0, changed=0)
        replies = orig_collect(self, msgs, models, device)
        games = sum(len(r.get("results", [])) for r in replies if r)
        st["last_forced"] = cnt["forced"]
        rec = {"iteration": st["it"], "eps": eps, "games": games, **cnt,
               "eligible_per_game": round(cnt["eligible"] / max(games, 1), 2), "forced_per_game": round(cnt["forced"] / max(games, 1), 2)}
        print("p10 " + json.dumps(rec), flush=True)
        with (out / "p10.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        st["it"] += 1
        return replies

    R.RemotePool.collect, R.RemotePool._serve_batches = collect, serve
    return lambda: (setattr(R.RemotePool, "collect", orig_collect), setattr(R.RemotePool, "_serve_batches", orig_serve))


def wrap_p8(out: Path, frac: float):
    """--p8: each RemotePool.collect call asks the workers for trBranch at share trFrac = frac (env/remote_worker.js trCatch) and
    leaves the rows, shifted to the concatenated rollout's row numbers, in RemotePool.p8. Returns the undo."""
    import time
    from rl.remote import RemotePool
    orig, prev = RemotePool.collect, {"t": None, "branch": 0.0}
    RemotePool.p8 = st = {"out": out, "it": -1, "frac": frac, "prev_share": None}

    def collect(self, msgs, models, device):
        now = time.time()
        if prev["t"] is not None:      # the whole of the previous iteration is known now
            st["prev_share"] = round(prev["branch"] / (now - prev["t"]), 3)
        st["it"] += 1
        st["t0"] = prev["t"] = now
        msgs = [{**m, "trBranch": 1, "trFrac": st["frac"]} if m.get("cmd") == "collect" else m for m in msgs]
        replies = orig(self, msgs, models, device)
        st["collect_s"] = time.time() - now
        rows, base, st["eligible"], st["branch_s"] = [], 0, 0, 0.0
        for r in replies:
            tb = r.get("trBranch") or {}
            rows += [{**x, "k": x["k"] + base} for x in tb.get("rows", [])]
            st["eligible"] += tb.get("eligible", 0)
            st["branch_s"] = max(st["branch_s"], tb.get("seconds", 0.0))
            base += r["transitions"]
        st["rows"], prev["branch"] = rows, st["branch_s"]
        return replies

    RemotePool.collect = collect
    return lambda: setattr(RemotePool, "collect", orig)


def wrap_collect(out: Path):
    """Log only: each RemotePool.collect call (one training iteration) asks the workers for trainerCounts (env/remote_worker.js:
    decisions and options picked per "<resolving Trainer>|<prompt>|<seat>"), sums them and appends a line to
    <out>/trainer_counts.jsonl plus a `tc` line to stdout. Returns the undo."""
    from rl.remote import RemotePool
    orig, it = RemotePool.collect, [0]

    def collect(self, msgs, models, device):
        msgs = [{**m, "trainerCounts": 1} if m.get("cmd") == "collect" else m for m in msgs]
        replies = orig(self, msgs, models, device)
        counts = {}
        for r in replies:
            for k, v in (r.get("trainerCounts") or {}).items():
                c = counts.setdefault(k, {"prompts": 0, "picks": 0})
                c["prompts"] += v["prompts"]
                c["picks"] += v["picks"]
        with (out / "trainer_counts.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"iteration": it[0], "counts": counts}) + "\n")
        top = sorted(counts.items(), key=lambda kv: -kv[1]["picks"])[:5]
        named = lambda n: [sum(v[x] for k, v in counts.items() if k.split("|")[0] == n) for x in ("prompts", "picks")]
        print(f"tc {it[0]}: top {[(k, v['picks']) for k, v in top]}; Computer Search (prompts, picks) {named('Computer Search')}; "
              f"Item Finder {named('Item Finder')}", flush=True)
        it[0] += 1
        return replies

    RemotePool.collect = collect
    return lambda: setattr(RemotePool, "collect", orig)


def run(a, wt: Path, out: Path, res: dict) -> int:
    fixed = load_fixed(wt, a.minutes, out, Path(a.resume_from).resolve() if a.resume_from else None)
    fixed.ITERS = a.iters or 10 ** 9                            # wall clock is the budget (--iters: stop at that count)
    if a.start:                                                 # a warm-started pilot (BENCH-P1's T0) instead of start.pt
        fixed.START = (ROOT / a.start).resolve()
    matchups = json.loads(Path(a.matchups).read_text(encoding="utf-8"))
    fixed.practice_matchups = lambda: matchups
    text = (wt / "train.py").read_text(encoding="utf-8")
    if a.model_overrides:
        old = "MODEL_OVERRIDES = {}"
        if text.count(old) != 1:
            raise RuntimeError("train.py has no single 'MODEL_OVERRIDES = {}' line to replace")
        text = text.replace(old, f"MODEL_OVERRIDES = {json.loads(a.model_overrides)!r}")
    if a.adam_warm:                                             # P5 Amendment 3: zero-learning-rate iterations fill a cold Adam
        o = "            stats = ppo_update(model, opt, batch, device)\n"
        if text.count(o) != 1:
            raise RuntimeError("train.py has no single ppo_update call for --adam-warm")
        reset = (f"            if it == {a.adam_warm}:   # --adam-reset-m (P5c): the warm-up's coherent first moment is dropped\n"
                 "                for s_ in opt.state.values():\n"
                 "                    s_[\"exp_avg\"].zero_()\n") if a.adam_reset_m else ""
        text = text.replace(o, "            for g in opt.param_groups:   # --adam-warm\n"
                                f"                g[\"lr\"] = 0.0 if it < {a.adam_warm} else LR\n" + reset + o)
    if a.kl_stop:                                               # P5c: PPO epochs stop once a minibatch's approximate KL > kl_stop
        for o, n in (("    for _ in range(EPOCHS):\n", "    cut = False\n    for _ in range(EPOCHS):\n"),
                     ("            torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)\n",
                      f"            if mb[\"kl\"] > {a.kl_stop}:   # --kl-stop: this minibatch's stats count, its step is skipped\n"
                      "                for k in stats:\n                    stats[k] += mb[k]\n                n += 1\n"
                      "                cut = True\n                break\n"
                      "            torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)\n"),
                     ("    return {k: v / max(n, 1) for k, v in stats.items()}\n",
                      "        if cut:\n            break\n"
                      "    print(f\"kl-stop: {n} minibatches of {EPOCHS * ((T + MINIBATCH - 1) // MINIBATCH)}, cut {cut}\", flush=True)\n"
                      "    return {k: v / max(n, 1) for k, v in stats.items()}\n")):
            if text.count(o) != 1:
                raise RuntimeError(f"train.py has no single anchor for --kl-stop: {o.strip()[:40]}")
            text = text.replace(o, n)
    if a.p6:
        if text.count("\ndef ppo_update(") != 1 or text.count("\ndef advantages(") != 1:
            raise RuntimeError("train.py has no single advantages / ppo_update pair for --p6")
        text = text.replace("\ndef ppo_update(", P6 + "\ndef ppo_update(")
    if a.p5:
        if text.count("\ndef ppo_update(") != 1 or text.count("\ndef advantages(") != 1:
            raise RuntimeError("train.py has no single advantages / ppo_update pair for --p5")
        text = text.replace("\ndef ppo_update(", P5 + "\ndef ppo_update(")
    if a.p8:
        if text.count("\ndef ppo_update(") != 1 or text.count("\ndef advantages(") != 1:
            raise RuntimeError("train.py has no single advantages / ppo_update pair for --p8")
        text = text.replace("\ndef ppo_update(", P8 + "\ndef ppo_update(")
    if a.turn_gamma is not None:                                # P9: off (no flag) leaves train.py's GAE untouched
        if a.p5 or a.p6 or a.p8:
            raise RuntimeError("--turn-gamma recomputes plain GAE; it does not combine with --p5 / --p6 / --p8")
        if text.count("\ndef ppo_update(") != 1 or text.count("\ndef advantages(") != 1:
            raise RuntimeError("train.py has no single advantages / ppo_update pair for --turn-gamma")
        text = text.replace("\ndef ppo_update(", P9.replace("TURN_GAMMA = None", f"TURN_GAMMA = {a.turn_gamma!r}") + "\ndef ppo_update(")
    if a.p10_eps is not None:                                   # P10: off (no flag) leaves train.py untouched
        if a.p5 or a.p6 or a.p8 or a.turn_gamma is not None or a.kl_stop:
            raise RuntimeError("--p10-eps does not combine with --p5 / --p6 / --p8 / --turn-gamma / --kl-stop")
        if text.count("\ndef ppo_update(") != 1 or text.count("\ndef advantages(") != 1:
            raise RuntimeError("train.py has no single advantages / ppo_update pair for --p10-eps")
        text = text.replace("\ndef ppo_update(", P10 + "\ndef ppo_update(")
        for o, n in P10_UPDATE:
            if text.count(o) != 1:
                raise RuntimeError(f"train.py has no single anchor for --p10-eps: {o.strip()[:50]}")
            text = text.replace(o, n)
    patched = patch_train(text)
    log(f"pausable anchors found: {patched is not None}; matchups {len(matchups)}; overrides {a.model_overrides or 'none'}; "
        f"p6 {a.p6}; p5 {a.p5}; p8 {a.p8}; turn-gamma {a.turn_gamma}; p10-eps {a.p10_eps}")
    (wt / "train.py").write_text(patched or text, encoding="utf-8")   # the worktree's copy only
    undo = wrap_collect(out) if a.trainer_counts else (lambda: None)
    undo5 = wrap_p5(out, a.p5_komath) if a.p5 else (lambda: None)
    undo8 = wrap_p8(out, a.p8_frac) if a.p8 else (lambda: None)
    undo10 = wrap_p10(out, a.p10_eps, a.seed) if a.p10_eps is not None else (lambda: None)
    try:
        res["train"] = train(fixed, wt, a.seed)
    finally:
        undo10()
        undo8()
        undo5()
        undo()
    log(f"train: {res['train']}")
    if not fixed.OUT.exists():
        raise RuntimeError("train.py saved no pilot")
    shutil.copyfile(fixed.OUT, a.out_dir / "pilot.pt")
    if not a.keep_ckpt:                                         # --keep-ckpt: a later stage resumes from it
        fixed.CKPT.unlink(missing_ok=True)
    return 0


def main():
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--commit", help="a commit of the ar/ repo (default: ar/'s HEAD)")
    ap.add_argument("--minutes", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--name", default="arm0")
    ap.add_argument("--matchups", default=str(BENCH / "bench_matchups.json"))
    ap.add_argument("--model-overrides", help="JSON dict replacing train.py's MODEL_OVERRIDES = {}")
    ap.add_argument("--start", help="the pilot to train from (default ar/data/start.pt), e.g. BENCH-P1's distilled T0; "
                    "bench pilots stay under runs/probe/BENCH")
    ap.add_argument("--resume-from", help="a ckpt.pt of a paused run (exit 5)")
    ap.add_argument("--no-trainer-counts", dest="trainer_counts", action="store_false",
                    help="skip the per-Trainer prompt and pick counts (<out>/trainer_counts.jsonl, log only)")
    ap.add_argument("--iters", type=int, help="stop after this many iterations in all (a resumed run counts its earlier ones)")
    ap.add_argument("--keep-ckpt", action="store_true", help="keep <out>/ckpt.pt after the run, for a chained stage")
    ap.add_argument("--p5-komath", type=int, default=0, help="BENCH-P5b: every N-th iteration, log the branched difference by C110's "
                    "knockout label (koMath)")
    ap.add_argument("--adam-warm", type=int, default=0, help="the first N iterations at learning rate 0 (weights untouched; a cold "
                    "start's Adam moments fill), then LR (P5 Amendment 3)")
    ap.add_argument("--adam-reset-m", action="store_true", help="with --adam-warm N: zero Adam's first moment at iteration N (P5c)")
    ap.add_argument("--kl-stop", type=float, default=0.0, help="stop the PPO epochs once a minibatch's approximate KL exceeds this "
                    "(P5c: 0.04); the KL kill stays the backstop")
    ap.add_argument("--p6", action="store_true", help="BENCH-P6: Monte Carlo credit (lambda 1) at own-Trainer prompt rows")
    ap.add_argument("--p5", action="store_true", help="BENCH-P5: branched PlusPower-timing advantages at play-or-attack rows")
    ap.add_argument("--p8", action="store_true", help="BENCH-P8: branched greedy-vs-u advantages at Trainer-playable main-phase rows")
    ap.add_argument("--p8-frac", type=float, default=1.0, help="with --p8: the share s of Trainer-playable decisions branched")
    ap.add_argument("--turn-gamma", type=float, help="BENCH-P9: GAE's discount per game turn between a seat's decisions (0.98); "
                    "1.0 reproduces train.py's advantages exactly (logged each iteration)")
    ap.add_argument("--p10-eps", type=float, help="BENCH-P10: at main-phase rows with a legal Trainer play, force a uniform one "
                    "with this probability (0.10), masked from the policy loss, GAE's trace cut there; 0 changes nothing (logged)")
    ap.add_argument("--out-dir", help="default runs/probe/BENCH/arm-<name>-s<seed>")
    a = ap.parse_args()
    commit = git("rev-parse", "--verify", "--quiet", f"{a.commit or 'HEAD'}^{{commit}}", check=False)
    if not commit:
        ap.error(f"--commit {a.commit}: not a commit of the ar/ repo")
    a.out_dir = Path(a.out_dir).resolve() if a.out_dir else BENCH / f"arm-{a.name}-s{a.seed}"
    if (a.out_dir / "result.json").exists():
        ap.error(f"{a.out_dir / 'result.json'} exists: pass another --name or --out-dir")
    why = blocked()
    if why:
        log(f"refusing: {why}.")
        sys.exit(4)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    log(f"bench train: commit {commit[:7]}, {a.minutes:g} min, seed {a.seed}, out {a.out_dir}")
    res = {"commit": commit, "seed": a.seed, "minutes": a.minutes, "matchups": a.matchups,
           "overrides": json.loads(a.model_overrides) if a.model_overrides else {}, "p6": a.p6, **({"p5": True} if a.p5 else {}), **({"p8": a.p8_frac} if a.p8 else {}),
           **({"adam_warm": a.adam_warm} if a.adam_warm else {}), **({"turn_gamma": a.turn_gamma} if a.turn_gamma is not None else {}),
           **({"p10_eps": a.p10_eps} if a.p10_eps is not None else {})}
    tmp = Path(tempfile.mkdtemp(prefix=f"bench-{commit[:7]}-")).resolve()
    wt, code = tmp / "ar", 1
    git("worktree", "add", "--detach", str(wt), commit)
    try:
        code = run(a, wt, a.out_dir, res)
    except Paused as e:
        code = 5
        log(f"paused after iteration {e.args[0]}; resume with --resume-from {a.out_dir / 'ckpt.pt'}")
    except BaseException as e:
        res["crash"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        sys.modules.pop("fixed", None)
        log(f"worktree removed: {remove_worktree(wt, tmp)}")
        if code != 5:
            res["ended"] = f"{datetime.now():%Y-%m-%d %H:%M}"
            (a.out_dir / "result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
            log(f"wrote {a.out_dir / 'result.json'}")
    sys.exit(code)


if __name__ == "__main__":
    main()
