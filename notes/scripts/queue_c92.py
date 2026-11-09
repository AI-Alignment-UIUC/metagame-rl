"""C92 (runs/screens/C92-p479fresh/record.md, log #306-#307): C90's exact chain with --init-from the 479 lineage's pilot
(pilot_it0479.pt here, extracted from scr-resetcap/population_it0479.pt), seeds 1 and 2 in runs/screens/C92-p479fresh/s1,
s2 (s2 --replicate-of s1). Each seed launches in its own thread through loop.py launch (retried while refused) and is
watched pausable through queue_c90's Screen with the record's kill rule. Logs to C90-pairedselect/log.txt.
"""
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
from queue_c90 import Screen, log                      # noqa: E402

D = ROOT / "runs" / "screens" / "C92-p479fresh"
SRC = ROOT / "runs" / "screens" / "C90-R1-K-base-paired" / "chain.sh"
PILOT = "runs/screens/C92-p479fresh/pilot_it0479.pt"


def kill(rows):
    """The record: errors over 2% of an iteration's games; moves outside 3-30 for 3 iterations in a row within 0-5."""
    if any(r.get("errors", 0) > 0.02 * max(r.get("games", 1), 1) for r in rows):
        return "errors over 2%"
    off = [not 3 <= (r.get("select") or {}).get("moved", 0) <= 30 for r in rows if r["iter"] <= 5 and r.get("counted")]
    if any(all(off[i:i + 3]) for i in range(len(off) - 2)):
        return "moves outside 3-30 for 3 iterations in a row in 0-5"


def chain(seed: int) -> str:
    text = SRC.read_text(encoding="utf-8")
    name = f"C92-p479fresh-s{seed}"
    for a, b in (('cd "$(dirname "$0")/../../.."', 'cd "$(dirname "$0")/../../../.."'),
                 ("runs/screens/C90-R1-K-base-paired", f"runs/screens/C92-p479fresh/s{seed}"),
                 ("C90-R1-K-base-paired", name),
                 ("--init-from runs/pilot/C49-sd/model_it00199.pt", f"--init-from {PILOT}"),
                 ("from runs/pilot/C49-sd/model_it00199.pt, 30", "from the 479 lineage's pilot (C92), 30"),
                 ("--seed 1 ", f"--seed {seed} ")):
        assert text.count(a) >= 1, a
        text = text.replace(a, b)
    return text


def run_seed(seed: int):
    run = D / f"s{seed}"
    run.mkdir(parents=True, exist_ok=True)
    (run / "chain.sh").write_text(chain(seed), encoding="utf-8", newline="\n")
    x = Screen(f"C92-p479fresh-s{seed}", "C92", "runs/screens/C92-p479fresh/record.md", run, "prevention", "fresh",
               ["--evan-row", "78"] + (["--replicate-of", "C92-p479fresh-s1"] if seed == 2 else []))
    if not (run / "launch.log").exists():
        x.launch()
    x.watch(kill)


def main():
    t1 = threading.Thread(target=run_seed, args=(1,))
    t1.start()
    while not (D / "s1" / "launch.log").exists():         # s2 replicates s1, so s1 registers first
        threading.Event().wait(10)
    t2 = threading.Thread(target=run_seed, args=(2,))
    t2.start()
    t1.join(); t2.join()
    log("C92 done")


if __name__ == "__main__":
    main()
