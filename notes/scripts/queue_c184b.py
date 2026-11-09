"""C184 WR s51 on its own driver (#1057): C191 set B's high side, the same command as WR s50 (queue_c184's chain). queue_c184
launches its arms one at a time and has WR s51 last, behind ND s49; this starts it once C189-cells-s48 is registered (#1066: after C189 stage 3); HOLD-SCREENS's phases put C203-b-s48 ahead of it (#1097), with C184's WR kill and the supervisor. queue_c184, if it reaches WR s51 later, finds it alive or registered.
    .venv/Scripts/python notes/scripts/queue_c184b.py
"""
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import queue_c90 as Q                                    # noqa: E402
import queue_c168 as Q168                                # noqa: E402
import queue_c171 as QC                                  # noqa: E402
import queue_c184 as Q184                                # noqa: E402

NAME = "C184-WR-s51"

if __name__ == "__main__":
    Q.log(f"{NAME}: driver start (#1057), after C189-cells-s48 and WL s53's resume")
    while "C189-cells-s48" not in Q.reg():
        time.sleep(60)
    # (#1097: no wait for WL s53, which ended at 44; runs/loop/HOLD-SCREENS's phases set the order: C203-b-s48 first, then WR s51)
    s = Q184.make_screens()[NAME]
    if not Q.alive(NAME):
        s.launch(resume=NAME in Q.reg())
    threading.Thread(target=s.watch, args=(lambda rows: Q168.own_kill(rows, trainer_line=0),), daemon=True).start()
    QC.supervise({NAME: s})
    Q.log(f"{NAME}: driver end")
