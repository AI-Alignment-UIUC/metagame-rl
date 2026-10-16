"""Pilot diagnostics (logs #42, #47), one policy at a time, so pilots are compared on the same checks:

  1. against SimpleBot on 24 held-out random decks (runs/pilot-scratch/heldout_decks.json; no human shape)
  2. head to head against a reference pilot on the archived decks (rl.crossplay; evaluation only)
(The third check, deck variants scored by the start-of-game value, went with the value reader at log #65;
it is at the `pre-simplify` tag.)

Run: PYTHONPATH=. .venv/Scripts/python notes/scripts/pilot_diag.py --policy runs/pilot-v2/model_it00399.pt \
        --ref runs/pilot-scratch/model_it00249.pt --out runs/pilot-v2/diag
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from rl.crossplay import as_spec

ap = argparse.ArgumentParser()
ap.add_argument("--policy", required=True)
ap.add_argument("--ref", default="runs/pilot-scratch/model_it00249.pt")
ap.add_argument("--out", required=True, help="output prefix (a directory is created)")
ap.add_argument("--workers", type=int, default=12)
args = ap.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
res = {"policy": args.policy, "ref": args.ref}

subprocess.run(["node", "env/tools/evaluate.js", "--x", as_spec(args.policy), "--y", "simplebot",
                "--decks-file", "runs/pilot-scratch/heldout_decks.json", "--games", "400", "--workers", str(args.workers),
                "--concurrency", "8", "--seed", "77", "--json", str(out / "random_decks.json")],
               check=True, stdout=subprocess.DEVNULL)
r = json.load(open(out / "random_decks.json"))
res["vs_simplebot_random_decks"] = {"win": r["all"]["xWinRate"], "ci95": r["all"]["ci95"]}
print("vs SimpleBot on held-out random decks:", r["all"]["xWinRate"], "±", r["all"]["ci95"], flush=True)

subprocess.run([sys.executable, "-m", "rl.crossplay", "--policy", args.policy, "--opponents", args.ref, "--games", "400",
                "--workers", str(args.workers), "--out", str(out / "h2h.json")], check=True, stdout=subprocess.DEVNULL)
res["h2h_file"] = str(out / "h2h.json")

v = subprocess.run([sys.executable, "notes/scripts/trainer_restore_test.py", args.policy], check=True,
                   capture_output=True, text=True)
res["deck_variants"] = v.stdout.strip().splitlines()[-8:]
print("\n".join(res["deck_variants"]), flush=True)
json.dump(res, open(out / "diag.json", "w"), indent=1)
