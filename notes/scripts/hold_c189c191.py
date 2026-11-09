"""#1057 (research, taken by default, row 115): runs/loop/HOLD-SCREENS in two phases. Phase 1: only C189's stage-2 pilots may
launch (reserve_only, reserve_gb 0) until C189-cells-s2 is registered. Phase 2: only WL s53's resume and WR s51 may launch until
each has been seen running. Then the file is removed and the rest (DN s51, H0 s49, ND s49) go first-come.
    .venv/Scripts/python notes/scripts/hold_c189c191.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import queue_c90 as Q                                    # noqa: E402

Q.D = ROOT / "runs" / "probe" / "C193-lists-swap-depth"
HOLD = ROOT / "runs" / "loop" / "HOLD-SCREENS"
PHASES = [("C189-SH-s49-s2,C189-SL-s49-s2", lambda seen: "C189-cells-s2" in Q.reg(), "C189-cells-s2 is registered"),
          ("C191-WL-s53,C184-WR-s51", lambda seen: seen >= {"C191-WL-s53", "C184-WR-s51"}, "WL s53 and WR s51 have each been seen running")]

if __name__ == "__main__":
    for only, done, what in PHASES:
        HOLD.write_text(f"#1057, {time.strftime('%Y-%m-%d %H:%M')}: only {only} may launch until {what}\n"
                        f"reserve_gb=0  (#1043: no RAM kept beyond each launch's own need)\nreserve_only={only}  (#1057)\n", encoding="utf-8")
        Q.log(f"#1057 hold: only {only} until {what}")
        seen = set()
        while True:
            seen |= {n for n in only.split(",") if Q.alive(n)}
            if done(seen):
                break
            time.sleep(60)
    HOLD.unlink(missing_ok=True)
    Q.log("#1057 hold: released, HOLD-SCREENS removed")
