"""C95 (runs/probe/C95-qhead-candidates/record.md), Stage 1: an offline testbed that trains small value heads ("Q heads":
an MLP over each option's vector plus V0) on self-play data and scores them against the C94 oracle.

Rules: the oracle file O is evaluation only; no candidate trains on it, except the quarantined `cap` check (fit on 150 O
decisions split by game, scored on the rest). Training data is B (branched self-play) and S (single-visit self-play) only.
Scores on O (per decision, then pooled; 95% CI by bootstrap over decisions): rho (within-decision Spearman with O's Q, Fisher-z
pooled), rho_dis (rho / sqrt(R_O)), top1 (against chance), dG (O's Q at the head's argmax minus at the pilot's greedy).

New candidates go in TARGETS (name -> (source, builder)); a builder maps the source's records to a train set (see `trainset`).

  PYTHONPATH=. .venv/Scripts/python notes/scripts/qhead_testbed.py --o runs/probe/C94-oracle/oracle.pt \
      --b runs/probe/C95-qhead-candidates/B.pt --s runs/probe/C94-oracle/selfplay.pt --candidates c1,c7mc,cap --seeds 1 2
"""
import argparse
import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
from probe_target_signal import NAMED, pearson, spearman  # noqa: E402

HIDDEN, LR, EPOCHS, BATCH, FRAC, MAX_SEC = 128, 1e-3, 60, 64, 0.8, 600
PROMPT_COL = 48          # obs.glob byte 48 == 0 marks a prompt row (ar/train.py's Floor)


class TooSlow(Exception):
    pass


# ------------------------------------------------------------------------------------------------------------ train sets
def trainset(kind, E, v0, Y=None, R=None):
    """kind: 'centred' (Y[a] per answer, loss on within-decision-centred outputs), 'bt' (R[a, j], pairwise logistic) or
    'point' (one option a decision, Y a scalar, plain regression). E: list of (A, D) arrays; v0: list of floats."""
    return {"kind": kind, "E": E, "v0": np.asarray(v0, np.float32), "Y": Y, "R": R}


def b_valid_cols(r):
    R = np.asarray(r["R"], float)
    return R, ~np.isnan(R).any(0)


def build_c1(recs):
    """Seed-centred regression: target = mean over rollouts j of R[a, j] - mean over answers of R[., j]."""
    E, v0, Y = [], [], []
    for r in recs:
        R, ok = b_valid_cols(r)
        if ok.sum() == 0 or len(R) < 2:
            continue
        E.append(np.asarray(r["emb"], np.float32)); v0.append(r["V0"])
        Y.append((R[:, ok] - R[:, ok].mean(0, keepdims=True)).mean(1))
    return trainset("centred", E, v0, Y=Y)


def build_c2(recs):
    """Bradley-Terry on within-seed pairs: logistic loss on sign(R[a, j] - R[b, j]); ties carry no gradient."""
    E, v0, R_ = [], [], []
    for r in recs:
        R, ok = b_valid_cols(r)
        if ok.sum() == 0 or len(R) < 2:
            continue
        E.append(np.asarray(r["emb"], np.float32)); v0.append(r["V0"]); R_.append(R[:, ok])
    return trainset("bt", E, v0, R=R_)


def turn_targets(batch: dict):
    """C88 (ar commit d822ed9): per row, the value at the same trajectory's first later row of another turn (glob byte 0), i.e.
    the seat's next-turn decision; the final reward if the game ends first. Nothing after that turn's start enters it."""
    value, reward, done, traj = batch["value"], batch["reward"], batch["done"], batch["traj"]
    turn = batch["obs.glob"].reshape(len(value), -1)[:, 0]
    tgt = np.zeros(len(value), dtype=np.float32)
    nxt = {}                                              # traj -> (turn, value, target) of its next row
    for t in range(len(value) - 1, -1, -1):
        k = traj[t]
        if done[t] or k not in nxt:                       # the game ends after this decision
            tgt[t] = reward[t] if done[t] else value[t]
        else:
            u_turn, u_val, u_tgt = nxt[k]
            tgt[t] = u_val if u_turn != turn[t] else u_tgt
        nxt[k] = (turn[t], value[t], tgt[t])
    return tgt


def s_embeddings(S, pilot, device):
    """Rows of S: the chosen option's vector (the input of model.score, by forward pre-hook) and which rows are prompts."""
    from rl import limits
    from rl.gpu_matrix import load_policy
    from rl.remote import trim_inputs
    from rl.train import model_inputs
    limits.apply(device, 1)
    model, _ = load_policy(pilot, device)
    ins = model_inputs(S, "tokens")
    dts = [np.int16, np.uint8, np.uint8, np.uint8, np.uint8, np.int16, np.int32]
    cap = []
    h = model.score.register_forward_pre_hook(lambda mod, inp: cap.append(inp[0].detach()))
    out, act = [], S["action"].astype(np.int64)
    try:
        with torch.no_grad():
            for s in range(0, len(act), 256):
                x = [torch.from_numpy(np.ascontiguousarray(a[s:s + 256]).astype(d)).to(device) for a, d in zip(ins, dts)]
                cap.clear()
                model(*trim_inputs(x, model))
                c = cap[0].float()
                out.append(c[torch.arange(len(c)), torch.from_numpy(act[s:s + 256]).to(device)].cpu().numpy())
    finally:
        h.remove()
    return np.concatenate(out)


def build_s(which):
    def build(S):
        batch = S["batch"]
        if "emb" not in S:
            S["emb"] = s_embeddings(batch, S["pilot"], S["device"])
        prompt = batch["obs.glob"].reshape(len(batch["action"]), -1)[:, PROMPT_COL] == 0
        use = prompt if prompt.any() else np.ones(len(prompt), bool)
        tgt = {"mc": batch["mc_ret"], "gae": batch["gae_ret"], "turn": turn_targets(batch)}[which] - batch["value"]
        print(f"S {which}: {int(use.sum())} of {len(use)} rows ({'prompt rows only' if prompt.any() else 'ALL rows: no prompt rows found'})")
        idx = np.flatnonzero(use)
        return trainset("point", [S["emb"][i][None] for i in idx], batch["value"][idx], Y=tgt[idx].astype(np.float32))
    return build


# candidate -> (source, builder). Add c3 (vals bootstrap), c5, c6 (ListNet), c8 (ensemble) here.
def line_targets(r, f):
    """Per answer, the seed-centred mean over rollouts valid for every answer of f(vals of the line, its reward), or None."""
    V, R = r["vals"], np.asarray(r["R"], float)
    ok = ~np.isnan(R).any(0)
    if ok.sum() == 0 or len(R) < 2:
        return None
    T = np.array([[f(V[a][j] or [], R[a, j]) for j in np.flatnonzero(ok)] for a in range(len(R))], float)
    return (T - T.mean(0, keepdims=True)).mean(1)


def h_step(h):
    """The seat's value at its h-th own decision after the answer; the line's reward if the game ended first."""
    return lambda v, rew: v[h - 1] if len(v) >= h else rew


def lam_return(lam):
    """The lambda-return over the seat's later values then the reward (gamma 1)."""
    def f(v, rew):
        g = lam ** len(v) * rew
        for h, x in enumerate(v):
            g += (1 - lam) * lam ** h * x
        return g
    return f


def c2r_target(r):
    """A linear Bradley-Terry score for the ridge head: per answer, the mean within-seed pairwise sign against the others."""
    R, ok = b_valid_cols(r)
    if ok.sum() == 0 or len(R) < 2:
        return None
    s = np.sign(R[:, None, ok] - R[None, :, ok])
    return s.sum(1).mean(1) / (len(R) - 1)


C3 = {"c3h1": h_step(1), "c3h2": h_step(2), "c3h4": h_step(4), "c3l5": lam_return(0.5), "c3l8": lam_return(0.8)}


def build_line(f):
    def build(recs):
        E, v0, Y = [], [], []
        for r in recs:
            y = line_targets(r, f)
            if y is not None:
                E.append(np.asarray(r["emb"], np.float32)); v0.append(r["V0"]); Y.append(y)
        return trainset("centred", E, v0, Y=Y)
    return build


TARGETS = {"c1": ("B", build_c1), "c2": ("B", build_c2), **{k: ("B", build_line(f)) for k, f in C3.items()},
           "c7mc": ("S", build_s("mc")), "c7gae": ("S", build_s("gae")), "c7turn": ("S", build_s("turn"))}


# ------------------------------------------------------------------------------------------------------------------ head
def pad(ts, idx):
    """Tensors for the decisions idx: E (N, Amax, D), v0, mask (N, Amax), Y, R."""
    A = max(len(ts["E"][i]) for i in idx)
    D = ts["E"][idx[0]].shape[1]
    E, M = np.zeros((len(idx), A, D), np.float32), np.zeros((len(idx), A), bool)
    Y = np.zeros((len(idx), A), np.float32)
    R = None
    if ts["kind"] == "bt":
        m = max(ts["R"][i].shape[1] for i in idx)
        R = np.full((len(idx), A, m), np.nan, np.float32)
    for k, i in enumerate(idx):
        a = len(ts["E"][i])
        E[k, :a], M[k, :a] = ts["E"][i], True
        if ts["kind"] == "centred":
            Y[k, :a] = ts["Y"][i]
        elif ts["kind"] == "point":
            Y[k, 0] = ts["Y"][i]
        else:
            R[k, :a, :ts["R"][i].shape[1]] = ts["R"][i]
    return E, ts["v0"][idx], M, Y, R


class Head(nn.Module):
    def __init__(self, D, mu, sd):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(D + 1, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, 1))
        self.mu, self.sd = torch.tensor(mu), torch.tensor(sd)

    def forward(self, E, v0):
        x = torch.cat([(E - self.mu) / self.sd, v0[:, None, None].expand(-1, E.shape[1], 1)], -1)
        return self.net(x).squeeze(-1)


def loss_fn(kind, out, M, Y, R):
    if kind == "point":
        return ((out[:, 0] - Y[:, 0]) ** 2).mean()
    if kind == "centred":
        n = M.sum(1, keepdim=True)
        c = (out * M).sum(1, keepdim=True) / n
        return (((out - c) - Y) ** 2 * M).sum() / M.sum()
    d = out[:, :, None] - out[:, None, :]                              # (N, A, A): out[a] - out[b]
    diff = R[:, :, None, :] - R[:, None, :, :]                         # (N, A, A, m), nan where invalid
    w = (~torch.isnan(diff)) & (diff != 0)                              # ties carry no gradient
    p = (0.5 + torch.nan_to_num(diff) / 4).clamp(0, 1)                  # soft labels: partial outcomes (±1/3) count part
    bce = torch.nn.functional.softplus(d[..., None]) - p * d[..., None]
    return (bce * w).sum() / w.sum().clamp(min=1)


def fit(ts, seed):
    """Seeded head fit: FRAC of the decisions (seeded subsample), EPOCHS epochs of mini-batches. Raises TooSlow past MAX_SEC."""
    rng = np.random.default_rng(seed)
    n = len(ts["E"])
    idx = np.sort(rng.choice(n, max(1, int(round(FRAC * n))), replace=False))
    flat = np.concatenate([ts["E"][i] for i in idx])
    mu, sd = flat.mean(0), flat.std(0) + 1e-6
    torch.manual_seed(seed)
    head = Head(flat.shape[1], mu, sd)
    opt = torch.optim.Adam(head.parameters(), lr=LR)
    t0 = time.time()
    for ep in range(EPOCHS):
        perm = rng.permutation(idx)
        for s in range(0, len(perm), BATCH):
            E, v0, M, Y, R = (None if x is None else torch.from_numpy(np.asarray(x)) for x in pad(ts, perm[s:s + BATCH]))
            loss = loss_fn(ts["kind"], head(E, v0), M, Y, R)
            opt.zero_grad(); loss.backward(); opt.step()
        if time.time() - t0 > MAX_SEC:
            raise TooSlow(f"fit over {MAX_SEC}s at epoch {ep}")
    return head, time.time() - t0, len(idx)


# ------------------------------------------------------------------------------------------------------------------ scores
def predict(head, recs):
    with torch.no_grad():
        return [head(torch.from_numpy(np.asarray(r["emb"], np.float32))[None], torch.tensor([float(r["V0"])]))[0].numpy() for r in recs]


def rsb_of(r):
    """Spearman-Brown split-half of one decision (oracle_pack.split_half's per-decision value), nan if undefined."""
    c = pearson(r["Qh"][0], r["Qh"][1])
    return np.nan if c is None else 2 * c / (1 + c) if c > -0.99 else -0.999


def per_decision(recs, preds):
    rows = []
    for r, p in zip(recs, preds):
        Q = np.asarray(r["Q"], float)
        ok = not np.isnan(Q).any()
        three = ok and len(Q) >= 3
        rho = spearman(p, Q) if three else None
        rows.append({"rho": np.nan if rho is None else rho, "rsb": rsb_of(r) if three else np.nan,
                     "hit": float(np.argmax(p) == np.argmax(Q)) if ok else np.nan, "chance": 1.0 / len(Q) if ok else np.nan,
                     "dG": float(Q[int(np.argmax(p))] - Q[r["greedy"]]) if ok else np.nan})
    return {k: np.array([d[k] for d in rows], float) for k in rows[0]}


def zmean(x):
    x = x[~np.isnan(x)]
    return float(np.tanh(np.arctanh(np.clip(x, -0.999, 0.999)).mean())) if len(x) else np.nan


def stats_for(x, n_boot=1000, seed=0):
    """Point and 95% CI for each score over the decisions in x (dict of arrays), bootstrap over decisions."""
    n = len(x["rho"])
    if n == 0:
        return {"decisions": 0}

    def point(d):
        rho, rsb = zmean(d["rho"]), zmean(np.where(np.isnan(d["rho"]), np.nan, d["rsb"]))
        g = d["dG"][~np.isnan(d["dG"])]
        return {"rho": rho, "R_O": rsb, "rho_dis": rho / np.sqrt(rsb) if rsb > 0 else np.nan,
                "top1": np.nanmean(d["hit"]) if (~np.isnan(d["hit"])).any() else np.nan,
                "dG": g.mean() if len(g) else np.nan}
    p0 = point(x)
    rng = np.random.default_rng(seed)
    bs = [point({k: v[i] for k, v in x.items()}) for i in (rng.integers(0, n, n) for _ in range(n_boot))]
    out = {"decisions": n, "decisions_A3": int((~np.isnan(x["rho"])).sum()), "chance": float(np.nanmean(x["chance"]))}
    for k, v in p0.items():
        b = np.array([q[k] for q in bs], float)
        b = b[~np.isnan(b)]
        out[k] = {"v": None if np.isnan(v) else round(float(v), 4),
                  "lo": round(float(np.percentile(b, 2.5)), 4) if len(b) > 20 else None,
                  "hi": round(float(np.percentile(b, 97.5)), 4) if len(b) > 20 else None}
    g = x["dG"][~np.isnan(x["dG"])]
    out["dG"]["se"] = round(float(g.std(ddof=1) / np.sqrt(len(g))), 4) if len(g) > 1 else None
    return out


def score(recs, preds):
    named = [i for i, r in enumerate(recs) if r["trainer"] and any(r["trainer"].startswith(n) for n in NAMED)]
    csg = [i for i, r in enumerate(recs) if r["trainer"] and r["trainer"].startswith(("Computer Search", "Gust of Wind"))]
    d = per_decision(recs, preds)                        # cs_gust: the R_O 0.64-0.69 stratum (C95 Amendment 2)
    return {"all": stats_for(d), "named5": stats_for({k: v[named] for k, v in d.items()}),
            "cs_gust": stats_for({k: v[csg] for k, v in d.items()})}


def cap_split(recs, n_train=150):
    """Whole games stay together: games ordered by a fixed hash, taken until n_train decisions (3/4 of the file if it is small)."""
    n_train = min(n_train, int(0.75 * len(recs)))
    games = sorted({r["game"] for r in recs}, key=lambda g: zlib.crc32(str(g).encode()))
    tr, got = set(), 0
    for g in games:
        k = sum(r["game"] == g for r in recs)
        if got and got + k > n_train:
            continue
        tr.add(g); got += k
    return [r for r in recs if r["game"] in tr], [r for r in recs if r["game"] not in tr]


# ------------------------------------------------------------------------------------------------------------------ main
def emb_feats(r, vocab):
    return np.asarray(r["emb"], float)


def card_feats(r, vocab):
    """One-hot of (answer card, resolving Trainer) over the training folds' vocabulary; unseen pairs are all zero."""
    X = np.zeros((len(r["answers"]), len(vocab)))
    for a, k in enumerate(r["answers"]):
        j = vocab.get((r["keys"][k].split("|")[-1], r["trainer"]))
        if j is not None:
            X[a, j] = 1.0
    return X


LAMS = (1.0, 10.0, 100.0, 1e3, 1e4, 1e5)                # ridge grid (C95 Amendment 3: extended past 1000)


def c1_target(r):
    R, ok = b_valid_cols(r)
    return None if ok.sum() == 0 or len(R) < 2 else (R[:, ok] - R[:, ok].mean(0, keepdims=True)).mean(1)


def ridge_head(recs, target, seed, folds=5):
    """The "r" head (C95 Amendment 3): ridge from within-decision-centred option vectors to a candidate's per-answer
    target, on the seed's FRAC subsample of the training records; lambda by inner CV by game on them only."""
    rng = np.random.default_rng(seed)
    data = [(r, target(r)) for r in recs if r.get("emb") is not None]
    data = [d for d in data if d[1] is not None]
    data = [d for d, k in zip(data, rng.random(len(data)) < FRAC) if k]
    games = sorted({r["game"] for r, _ in data})
    fold = {games[i]: j % folds for j, i in enumerate(rng.permutation(len(games)))}

    def xy(ds):
        return (np.concatenate([np.asarray(r["emb"], float) - np.asarray(r["emb"], float).mean(0) for r, _ in ds]),
                np.concatenate([np.asarray(y, float) for _, y in ds]))

    def solve(X, y, lam):
        return np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ y)

    err = dict.fromkeys(LAMS, 0.0)
    for k in range(folds):
        fa, fb = [d for d in data if fold[d[0]["game"]] != k], [d for d in data if fold[d[0]["game"]] == k]
        if fa and fb:
            Xa, ya = xy(fa)
            Xb, yb = xy(fb)
            for lam in LAMS:
                err[lam] += float(((Xb @ solve(Xa, ya, lam) - yb) ** 2).sum())
    lam = min(LAMS, key=lambda x: err[x])
    return solve(*xy(data), lam), lam, len(data)


RIDGE = {"c1r": c1_target, "c2r": c2r_target, **{k + "r": (lambda f: lambda r: line_targets(r, f))(f) for k, f in C3.items()}}


def ridge_cap(orecs, seed, feats):
    """Quarantined capacity check (research #330, A1's ridge_probe design): ridge from within-decision-centred features to
    O's centred Q. 5 folds by game (a seeded permutation of games), lambda by inner 4-fold CV by game inside each training
    fold, held-out predictions pooled. Returns (predictions per record, the lambdas chosen)."""
    lams = LAMS
    ok = [r for r in orecs if not np.isnan(r["Q"]).any()]
    games = sorted({r["game"] for r in orecs}, key=lambda g: zlib.crc32(str(g).encode()))
    games = [games[i] for i in np.random.default_rng(seed).permutation(len(games))]
    fold = {g: i % 5 for i, g in enumerate(games)}

    def xy(rs, vocab):
        X = [feats(r, vocab) for r in rs]
        return (np.concatenate([x - x.mean(0) for x in X]),
                np.concatenate([np.asarray(r["Q"], float) - np.mean(r["Q"]) for r in rs]))

    def solve(X, y, lam):
        return np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ y)

    preds, chosen = [None] * len(orecs), []
    for k in range(5):
        tr = [r for r in ok if fold[r["game"]] != k]
        vocab = {}
        for r in tr:
            for a in r["answers"]:
                vocab.setdefault((r["keys"][a].split("|")[-1], r["trainer"]), len(vocab))
        inner = {g: i % 4 for i, g in enumerate([g for g in games if any(r["game"] == g for r in tr)])}
        err = dict.fromkeys(lams, 0.0)
        for j in range(4):
            fa, fb = [r for r in tr if inner[r["game"]] != j], [r for r in tr if inner[r["game"]] == j]
            if fa and fb:
                Xa, ya = xy(fa, vocab)
                Xb, yb = xy(fb, vocab)
                for lam in lams:
                    err[lam] += float(((Xb @ solve(Xa, ya, lam) - yb) ** 2).sum())
        lam = min(lams, key=lambda x: err[x])
        chosen.append(lam)
        w = solve(*xy(tr, vocab), lam)
        for i, r in enumerate(orecs):
            if fold[r["game"]] == k:
                x = feats(r, vocab)
                preds[i] = (x - x.mean(0)) @ w
    return preds, chosen


def fmt(v):
    return "None" if v is None else f"{v:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--o", required=True)
    ap.add_argument("--b", default=None)
    ap.add_argument("--s", default=None)
    ap.add_argument("--candidates", default="c1,c7mc,c7gae,c7turn,cap")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--out", default="runs/probe/C95-qhead-candidates/scores.jsonl")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    a = ap.parse_args()
    torch.set_num_threads(4)
    O = torch.load(ROOT / a.o, weights_only=False)
    orecs = O["records"]
    src = {}
    if a.b:
        src["B"] = [r for r in torch.load(ROOT / a.b, weights_only=False)["records"]]
    if a.s:
        S = torch.load(ROOT / a.s, weights_only=False)
        S["device"] = a.device
        src["S"] = S
    out_path = ROOT / a.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cache, table = {}, []

    def emit(row):
        with open(out_path, "a") as f:
            f.write(json.dumps(row) + "\n")
        sc = row.get("scores", {})
        for grp in ("cs_gust", "named5", "all"):          # Computer Search + Gust first (research, after C97)
            s = sc.get(grp, {})
            if s.get("decisions"):
                table.append((row["candidate"] + ("(Q)" if row["quarantined"] else ""), row["seed"], grp, s["decisions"],
                              row["fit_seconds"], s["rho"], s["rho_dis"], s["top1"], s["chance"], s["dG"]))
        if not sc:
            print(row["candidate"], row["seed"], row["status"])

    for cand in a.candidates.split(","):
        if cand in RIDGE:                                # a target candidate with the ridge head (Amendment 3)
            if "B" not in src:
                print(f"{cand}: needs --b, skipped")
                continue
            for seed in a.seeds:
                t0 = time.time()
                w, lam, n = ridge_head(src["B"], RIDGE[cand], seed)
                preds = [(np.asarray(r["emb"], float) - np.asarray(r["emb"], float).mean(0)) @ w for r in orecs]
                emit({"candidate": cand, "seed": seed, "quarantined": False, "head": "ridge", "lambda": lam,
                      "train_decisions": n, "eval_decisions": len(orecs), "frac": FRAC, "status": "ok",
                      "fit_seconds": round(time.time() - t0, 1), "scores": score(orecs, preds)})
            continue
        if cand in ("ridgecap", "cardcap"):              # quarantined (research #330): nested-CV ridge, pooled as cap5
            for seed in a.seeds:
                t0 = time.time()
                preds, lams = ridge_cap(orecs, seed, emb_feats if cand == "ridgecap" else card_feats)
                emit({"candidate": cand, "seed": seed, "quarantined": True, "folds": 5, "lambdas": lams,
                      "eval_decisions": len(orecs), "status": "ok", "fit_seconds": round(time.time() - t0, 1),
                      "scores": score(orecs, preds)})
            continue
        if cand == "cap5":                               # quarantined: 5-fold cross-fitting by game over all of O, pooled
            games = sorted({r["game"] for r in orecs}, key=lambda g: zlib.crc32(str(g).encode()))
            fold = {g: i % 5 for i, g in enumerate(games)}
            for seed in a.seeds:
                preds, t0 = [None] * len(orecs), time.time()
                for k in range(5):
                    tr = [r for r in orecs if fold[r["game"]] != k and not np.isnan(r["Q"]).any()]
                    ts = trainset("centred", [np.asarray(r["emb"], np.float32) for r in tr], [r["V0"] for r in tr],
                                  Y=[np.asarray(r["Q"], float) - np.mean(r["Q"]) for r in tr])
                    head = fit(ts, seed)[0]
                    idx = [i for i, r in enumerate(orecs) if fold[r["game"]] == k]
                    for i, q in zip(idx, predict(head, [orecs[i] for i in idx])):
                        preds[i] = q
                emit({"candidate": cand, "seed": seed, "quarantined": True, "folds": 5, "eval_decisions": len(orecs),
                      "epochs": EPOCHS, "frac": FRAC, "status": "ok", "fit_seconds": round(time.time() - t0, 1),
                      "scores": score(orecs, preds)})
            continue
        if cand == "cap":
            tr, test = cap_split(orecs)
            ts = trainset("centred", [np.asarray(r["emb"], np.float32) for r in tr], [r["V0"] for r in tr],
                          Y=[np.asarray(r["Q"], float) - np.nanmean(r["Q"]) for r in tr])
            keep = [i for i, r in enumerate(tr) if not np.isnan(r["Q"]).any()]
            ts = trainset("centred", [ts["E"][i] for i in keep], [ts["v0"][i] for i in keep], Y=[ts["Y"][i] for i in keep])
            eval_recs = test
        else:
            name, builder = TARGETS[cand]
            if name not in src:
                print(f"{cand}: needs --{name.lower()}, skipped")
                continue
            if cand not in cache:
                cache[cand] = builder(src[name])
            ts, eval_recs = cache[cand], orecs
        for seed in a.seeds:
            row = {"candidate": cand, "seed": seed, "quarantined": cand == "cap", "train_decisions": len(ts["E"]),
                   "eval_decisions": len(eval_recs), "epochs": EPOCHS, "frac": FRAC}
            if not ts["E"] or not eval_recs:
                row["status"] = "no train or eval decisions"
            else:
                try:
                    head, sec, nfit = fit(ts, seed)
                    row.update({"status": "ok", "fit_seconds": round(sec, 1), "fit_decisions": nfit})
                    row["scores"] = score(eval_recs, predict(head, eval_recs))
                except TooSlow as e:
                    row["status"] = f"too slow: {e}"
            emit(row)
    print(f"{'cand':8} {'seed':>4} {'grp':7} {'n':>4} {'sec':>5}  {'rho [CI]':22} {'rho_dis [CI]':22} {'top1':>6} {'chance':>6} {'dG (se)':>16}")
    for c, sd, g, n, sec, rho, rd, t1, ch, dg in table:
        ci = lambda v: f"{fmt(v['v'])} [{fmt(v['lo'])},{fmt(v['hi'])}]"
        print(f"{c:8} {sd:>4} {g:7} {n:>4} {sec:>5}  {ci(rho):22} {ci(rd):22} {fmt(t1['v']):>6} {ch:>6.3f} {fmt(dg['v'])} ({fmt(dg['se'])})")


if __name__ == "__main__":
    main()
