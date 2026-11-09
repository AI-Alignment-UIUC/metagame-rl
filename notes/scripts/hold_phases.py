"""runs/loop/HOLD-SCREENS in phases, for a priority order among screens and pilots (#1066). Each argument is a phase,
ONLY=UNTIL: while it holds, only the runs in ONLY (comma-separated) may launch (loop.py's reserve_only, reserve_gb 0); it ends when
UNTIL holds: "reg:NAME" (NAME is registered) or "alive" (each run in ONLY has been seen running). After the last phase the file
is removed. Probes aren't held (loop.py holds only screens and pilots).
    .venv/Scripts/python notes/scripts/hold_phases.py "C191-WL-s53,C189-SH-s48,C189-SL-s48=reg:C189-cells-s48" "C184-WR-s51=alive"
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import queue_c90 as Q                                    # noqa: E402

Q.D = ROOT / "runs" / "probe" / "C193-lists-swap-depth"
HOLD = ROOT / "runs" / "loop" / "HOLD-SCREENS"

if __name__ == "__main__":
    for ph in sys.argv[1:]:
        only, until = ph.split("=")
        names = only.split(",")
        what = f"{until[4:]} is registered" if until.startswith("reg:") else f"{', '.join(names)} have each been seen running"
        HOLD.write_text(f"#1066, {time.strftime('%Y-%m-%d %H:%M')}: only {only} may launch until {what}\n"
                        f"reserve_gb=0  (#1043: no RAM kept beyond each launch's own need)\nreserve_only={only}  (#1066)\n", encoding="utf-8")
        Q.log(f"#1066 hold: only {only} until {what}")
        seen = set()
        while True:
            seen |= {n for n in names if Q.alive(n)}
            if (until[4:] in Q.reg()) if until.startswith("reg:") else seen == set(names):
                break
            time.sleep(60)
    HOLD.unlink(missing_ok=True)
    Q.log("#1066 hold: released, HOLD-SCREENS removed")
