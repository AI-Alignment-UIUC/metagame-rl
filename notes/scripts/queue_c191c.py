"""C191 WL s53's resume (#1015): loop.py's RAM-critical rule stopped it after iteration 5 ("stop: RAM critical"), which isn't a
pause, so C191's queue logged it as ended and won't relaunch it. This resumes it from its checkpoint with C191's own kill, through
Screen.launch's retries (a refusal from row 73, the RAM gate or a hold is retried every 2 minutes). C191's stop at 29 still reads
both arms' logs here, since queue_c191 itself ended at 06:38:30 once no arm was live; C191's supervisor (stage
reads, G3 probes, the wall kill) runs here for WL s53 too.
    .venv/Scripts/python notes/scripts/queue_c191c.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import threading                                         # noqa: E402
import queue_c90 as Q                                    # noqa: E402
import queue_c171 as QC                                  # noqa: E402
import queue_c191 as Q191                                # noqa: E402

Q.D = ROOT / "runs" / "probe" / "C191-energy-start-bracket"
NAME = "C191-WL-s53"

if __name__ == "__main__":
    run = ROOT / "runs" / "screens" / NAME
    stop = run / "STOP"
    if stop.exists() and stop.read_text(encoding="utf-8").startswith("stop: RAM critical"):
        stop.rename(run / "STOP.ramcritical-it5")
    Q.log(f"{NAME}: resuming from its checkpoint after loop.py's RAM-critical stop")
    QC.D = Q.D
    screens = Q191.make_screens()
    s = screens[NAME]
    s.launch(resume=True)
    threading.Thread(target=s.watch, args=(Q191.kill,), daemon=True).start()
    threading.Thread(target=Q191.stop_at_29, args=(screens,), daemon=True).start()
    QC.supervise({NAME: s})
    Q.log(f"{NAME}: resume driver end")
