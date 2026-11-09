"""C191 WL s53 under queue_c90's fixed pause (#1057): replaces queue_c191c, whose old queue_c90 would read a paused arm as ended
(#1051). Watches WL s53 with C191's kill; on its pause STOP it waits, then resumes it from its checkpoint (held by HOLD-SCREENS
until its phase); runs C191's stop at 29 and the supervisor (stage reads, G3 probes, the wall kill) for WL s53.
    .venv/Scripts/python notes/scripts/queue_c191d.py
"""
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import queue_c90 as Q                                    # noqa: E402
import queue_c171 as QC                                  # noqa: E402
import queue_c191 as Q191                                # noqa: E402

Q.D = ROOT / "runs" / "probe" / "C191-energy-start-bracket"
NAME = "C191-WL-s53"

if __name__ == "__main__":
    Q.log(f"{NAME}: driver start (#1057)")
    QC.D = Q.D
    screens = Q191.make_screens()                        # rewrites both WL chains at --iters 45: right for WL s53; WL s52 is done
    s = screens[NAME]
    if not Q.alive(NAME):
        s.launch(resume=True)
    threading.Thread(target=s.watch, args=(Q191.kill,), daemon=True).start()
    threading.Thread(target=Q191.stop_at_29, args=(screens,), daemon=True).start()
    QC.supervise({NAME: s})
    Q.log(f"{NAME}: driver end")
