"""C13 stage 1 scoring (runs/probe/C13-stage1/record.md; evaluation only, log #157). For each cell (judge x wall set):
the plain score, the walls' exact share of 2000 STS round points W(T) (walls_vs_humans_report.sts_points) with equal
weight per human list, W over Pi = uniform on T 20-45, the break-even turn T50 where W crosses 0.5, 90% intervals by a
bootstrap over wall-list pairs, and the paired gains of the walls-only and human-side search cells over greedy.

  .venv/Scripts/python -I notes/scripts/c13_score.py > runs/probe/C13-stage1/score.txt
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes/scripts"))
from walls_vs_humans_report import sts_points  # noqa: E402

S = ROOT / "runs/probe/C13-stage1"
P = ROOT / "runs/probe"
TS = np.arange(10, 121)                                    # every cut from 10 to 120 engine turns
PI = (TS >= 20) & (TS <= 45)
SUB = [0, 1, 5, 8, 16, 19, 22, 23]


def load(*paths):
    rows = []
    for p in paths:
        rows += [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]
    keys = [(r["i"], r["j"], r["g"]) for r in rows]
    assert len(keys) == len(set(keys)), f"duplicate deals in {paths}"
    return rows


CELLS = {
    "J1 A g0-7": load(P / "sts_greedy_all24.jsonl"),
    "J1 A g8-15": load(S / "greedy_A_g8.jsonl"),
    "J1 B": load(S / "greedy_B.jsonl"),
    "J1 C": load(S / "greedy_C.jsonl"),
    "J2 A all24": load(P / "sts_search_both_sub.jsonl", S / "both_sub_rest.jsonl", S / "both_rest16.jsonl"),
    "walls-only A": load(S / "walls_only.jsonl"),
    "human-side A (sub)": load(P / "sts_search_human_sub.jsonl"),
}
CELLS["J1 A g0-15"] = CELLS["J1 A g0-7"] + CELLS["J1 A g8-15"]
S1B = [ROOT / "runs/probe/C13-stage1b" / f for f in ("J2_C_g0.jsonl", "J2_C_g3.jsonl")]
if any(p.exists() for p in S1B):                         # stage 1b (log #158): J2 on set C
    CELLS["J2 C all24"] = load(*[p for p in S1B if p.exists()])


def arrays(rows):
    """Per pair: the walls' points and all points at every cut, plus plain and draw-at-T scores (sums and counts)."""
    pairs = sorted({(r["i"], r["j"]) for r in rows})
    ix = {p: k for k, p in enumerate(pairs)}
    a = np.zeros((len(pairs), len(TS))); tot = np.zeros_like(a); dr = np.zeros_like(a)
    plain = np.zeros(len(pairs)); n = np.zeros(len(pairs))
    for r in rows:
        k = ix[(r["i"], r["j"])]
        for c, t in enumerate(TS):
            x, y = sts_points(r, int(t))
            a[k, c] += x; tot[k, c] += x + y
            dr[k, c] += r["aScore"] if r["turns"] <= t else 0.5
        plain[k] += r["aScore"]; n[k] += 1
    lists = sorted({j for _, j in pairs})
    M = np.array([[1.0 if p[1] == j else 0.0 for p in pairs] for j in lists])   # lists x pairs
    return pairs, M, a, tot, dr, plain, n


def stat(c, M, a, tot, dr, plain, n):
    """Pair weights c (boot x pairs) -> per-list-weighted W(T), draw-at-T score and plain score."""
    w = c[:, None, :] * M[None]                                   # boot x lists x pairs
    has = w.sum(2) > 0
    W = np.einsum("blp,pc->blc", w, a) / np.maximum(np.einsum("blp,pc->blc", w, tot), 1e-9)
    D = np.einsum("blp,pc->blc", w, dr) / np.maximum(np.einsum("blp,p->bl", w, n), 1e-9)[..., None]
    pl = np.einsum("blp,p->bl", w, plain) / np.maximum(np.einsum("blp,p->bl", w, n), 1e-9)
    k = has.sum(1)
    return ((W * has[..., None]).sum(1) / k[:, None], (D * has[..., None]).sum(1) / k[:, None],
            (pl * has).sum(1) / k)


def t50(W):
    """The first cut at which W reaches 0.5 (linear interpolation); <10 or >120 off the grid."""
    out = []
    for w in np.atleast_2d(W):
        up = np.nonzero(w >= 0.5)[0]
        if not len(up):
            out.append(np.inf); continue
        k = up[0]
        out.append(TS[0] - 0.5 if k == 0 else TS[k - 1] + (0.5 - w[k - 1]) / (w[k] - w[k - 1]))
    return np.array(out)


def boot(arr, nb=4000, seed=0):
    pairs = arr[0]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(pairs), (nb, len(pairs)))
    c = np.zeros((nb, len(pairs)))
    np.add.at(c, (np.arange(nb)[:, None], idx), 1)
    return c


def ci(x, q=(5, 95)):
    x = x[np.isfinite(x)] if np.isinf(x).any() else x
    return np.percentile(x, q)


def show(name, rows):
    arr = arrays(rows)
    W, D, pl = stat(np.ones((1, len(arr[0]))), *arr[1:])
    W, D, pl = W[0], D[0], pl[0]
    c = boot(arr)
    Wb, Db, plb = stat(c, *arr[1:])
    tb = t50(Wb)
    lo, hi = ci(plb)
    ends = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        ends[r.get("ending") or "none"][0 if r["aScore"] == 1 else 1 if r["aScore"] == 0 else 2] += 1
    print(f"\n== {name}: {len(rows)} games, {len(arr[0])} pairs, {len({j for _, j in arr[0]})} lists; endings "
          f"[walls, lists, other] {dict(ends)}")
    print(f"  plain {pl:.3f} [90% {lo:.3f}, {hi:.3f}]; W(Pi 20-45) {W[PI].mean():.3f} "
          f"[{ci(Wb[:, PI].mean(1))[0]:.3f}, {ci(Wb[:, PI].mean(1))[1]:.3f}]; T50 {t50(W)[0]:.1f} "
          f"[{np.percentile(tb, 5):.1f}, {np.percentile(tb, 95):.1f}] (finite in {np.isfinite(tb).mean():.0%})")
    for t in (20, 25, 30, 35, 40, 45, 50, 60, 70, 80):
        k = int(np.nonzero(TS == t)[0][0])
        print(f"   T {t:3d}: STS share {W[k]:.3f} [{ci(Wb[:, k])[0]:.3f}, {ci(Wb[:, k])[1]:.3f}]  draw-at-T {D[k]:.3f}  "
              f"unfinished {np.mean([r['turns'] > t for r in rows]):.0%}")
    k50, k60 = int(np.nonzero(TS == 50)[0][0]), int(np.nonzero(TS == 60)[0][0])
    m5060 = Wb[:, k50:k60 + 1].mean(1)
    print(f"  W(T 50-60) {W[k50:k60 + 1].mean():.3f} [90% {ci(m5060)[0]:.3f}, {ci(m5060)[1]:.3f}]")
    return W, pl


def paired(name, ra, rb):
    """rb - ra on identical deals (same i, j, g), equal weight per list, 90% interval by pair bootstrap."""
    ka = {(r["i"], r["j"], r["g"]): r for r in ra}
    common = [(ka[k], r) for r in rb if (k := (r["i"], r["j"], r["g"])) in ka]
    rows_d = [dict(x, aScore=y["aScore"] - x["aScore"]) for x, y in common]
    arr = arrays(rows_d)
    _, _, pl = stat(np.ones((1, len(arr[0]))), *arr[1:])
    _, _, plb = stat(boot(arr), *arr[1:])
    lo, hi = ci(plb)
    print(f"  paired {name}: {pl[0]:+.3f} [90% {lo:+.3f}, {hi:+.3f}] on {len(common)} deals, "
          f"{sum(x['aScore'] != y['aScore'] for x, y in common)} results differ")
    return pl[0], lo, hi


def check(path, lo=0.45, hi=0.55):
    """Stage 1b's kill (record.md): exit 2 if the 90% interval of W(T 50-60) lies wholly above hi or below lo."""
    arr = arrays(load(path))
    Wb, _, _ = stat(boot(arr), *arr[1:])
    k50, k60 = int(np.nonzero(TS == 50)[0][0]), int(np.nonzero(TS == 60)[0][0])
    a, b = ci(Wb[:, k50:k60 + 1].mean(1))
    print(f"check {path}: W(T 50-60) 90% [{a:.3f}, {b:.3f}]")
    return 2 if a > hi or b < lo else 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["--check"]:
        sys.exit(check(sys.argv[2]))
    res ={k: show(k, v) for k, v in CELLS.items()}
    g = CELLS["J1 A g0-7"]
    print("\n== gains over greedy on the same deals (plain score; a gain for the walls is positive)")
    paired("walls-only (walls searched) - greedy, all 24", g, CELLS["walls-only A"])
    paired("J2 both seats - greedy, all 24", g, CELLS["J2 A all24"])
    sub = [r for r in g if r["j"] in SUB]
    paired("human-side (lists searched) - greedy, subset", sub, CELLS["human-side A (sub)"])
    paired("J2 both seats - greedy, subset", sub, [r for r in CELLS["J2 A all24"] if r["j"] in SUB])
    print("\n== bands (record.md): computed on the lines above; read in log #157")


if __name__ == "__main__":
    main()
