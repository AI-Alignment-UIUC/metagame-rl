"""Plays one policy against a list of opponents, seat- and deck-swapped (env/tools/evaluate.js), and
prints a table with 95% confidence intervals per deck direction (plan items A3, A4 exits).

Opponents are evaluate.js agent specs (simplebot, heuristic, onnx:<file>, ...) or checkpoint
files (*.pt), which are exported to ONNX first. The policy itself may also be a checkpoint.

Run: .venv/Scripts/python -m rl.crossplay --policy runs/a3b/model_it00139.pt \
        --opponents simplebot,heuristic,runs/a3c/model_it00099.pt --d1 "15+ #2 William Lieu" \
        --d2 "15+ #1 Andrew Marshall" --games 400 --out notes/data/eval/a3_exit.json
"""
import argparse
import json
import subprocess
from pathlib import Path

import torch

from rl.model import build, export_onnx

ROOT = Path(__file__).resolve().parent.parent


def as_spec(x: str, greedy: bool = True) -> str:
    if not x.endswith(".pt"):
        return x
    path = (ROOT / x).resolve()
    state = torch.load(path, map_location="cpu")
    cfg = state["config"]
    onnx = path.with_suffix(".onnx")
    if cfg.get("kind") == "TokenPointerNet":
        from rl.token_model import build_token_model, export_token_onnx
        m = build_token_model(str(ROOT / "notes/data/cards/pool.json"), str(ROOT / "notes/data/cards/text_emb.npy"),
                              cfg["n_names"], cfg["glob_f"], cfg["slot_f"], cfg["max_tok"], cfg["max_cand"],
                              d=cfg["d"], layers=cfg["layers"], heads=cfg["heads"])
        m.load_state_dict(state["model"])
        export_token_onnx(m, str(onnx))
        return f"onnxtok:{onnx}" + (":greedy" if greedy else "")
    m = build(cfg)
    m.load_state_dict(state["model"])
    export_onnx(m, str(onnx))
    return f"onnx:{onnx}" + (":greedy" if greedy else "")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--opponents", required=True, help="comma-separated agent specs or .pt checkpoints")
    ap.add_argument("--d1", default="all")
    ap.add_argument("--d2", default="all")
    ap.add_argument("--games", type=int, default=400)
    ap.add_argument("--workers", type=int, default=18)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--stochastic", action="store_true", help="sample the policy instead of playing its argmax")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    x = as_spec(args.policy, greedy=not args.stochastic)
    rows = []
    tmp = ROOT / "runs" / ".crossplay.json"
    for opp in args.opponents.split(","):
        y = as_spec(opp.strip(), greedy=True)
        cmd = ["node", str(ROOT / "env/tools/evaluate.js"), "--x", x, "--y", y, "--d1", args.d1, "--d2", args.d2,
               "--games", str(args.games), "--workers", str(args.workers), "--concurrency", "8", "--seed", str(args.seed),
               "--json", str(tmp)]
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        r = json.load(open(tmp))
        row = {"opponent": opp.strip(), "n": r["all"]["n"], "win": r["all"]["xWinRate"], "ci95": r["all"]["ci95"],
               "dir1": r["dir1"]["xWinRate"], "dir1_ci95": r["dir1"]["ci95"], "dir2": r["dir2"]["xWinRate"],
               "dir2_ci95": r["dir2"]["ci95"], "cut": r["all"]["cut"], "errors": r["all"]["errors"]}
        rows.append(row)
        print(f"{opp.strip():45s} {100 * row['win']:5.1f}% ± {100 * row['ci95']:4.1f}  "
              f"(on {args.d1[:18]}: {100 * row['dir1']:5.1f}% ± {100 * row['dir1_ci95']:4.1f}; "
              f"on {args.d2[:18]}: {100 * row['dir2']:5.1f}% ± {100 * row['dir2_ci95']:4.1f})  n={row['n']}", flush=True)
    tmp.unlink(missing_ok=True)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        json.dump({"policy": args.policy, "d1": args.d1, "d2": args.d2, "stochastic": args.stochastic, "rows": rows},
                  open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
