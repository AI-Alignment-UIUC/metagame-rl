"""C187 H0 s49's resume (#1051): H0 s49 was paused at iteration 0 (#1047) for C189's stage 2; its watcher removed the pause STOP
before its resume (held by HOLD-SCREENS) launched, so C187's supervisor counted the arm as ended and the queue exited at 10:30:56,
taking the watcher with it. This resumes H0 s49 from its checkpoint through Screen.launch's retries (row 73, the RAM gate and the
hold are retried every 2 minutes), with C187's kill and its supervisor (stage reads, G3 probes, the wall kill).
    .venv/Scripts/python notes/scripts/queue_c187b.py
"""
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import queue_c90 as Q                                    # noqa: E402
import queue_c168 as Q168                                # noqa: E402
import queue_c171 as QC                                  # noqa: E402
import queue_c187 as Q187                                # noqa: E402

NAME = "C187-H0-s49"

if __name__ == "__main__":
    Q.log(f"{NAME}: resume driver start (#1051)")
    s = Q187.make_screens()[NAME]
    kill = lambda rows: Q168.own_kill(rows, trainer_line=15, pokemon_over=18.5)   # as queue_c187
    s.launch(resume=True)
    threading.Thread(target=s.watch, args=(kill,), daemon=True).start()
    QC.supervise({NAME: s})
    Q.log(f"{NAME}: resume driver end")
