"""C193 Amendment 4 (runs/probe/C193-lists-swap-depth/record.md): runs/loop/HOLD-SCREENS holds every queue's new screen launches
(loop.py launch refuses kind screen and pilot) until C193's last stage, s2-search-plus, is registered. Then the file is removed.
Running screens are untouched. --until-file F holds until F exists (C194); --until-registered NAME until that stage is registered.
C194 Amendment 1: by default the file is a reservation (reserve_gb=6.5): a screen or pilot launches with 8.0 + 6.5 GB free.
C196 Amendment 2: --reserve-gpu-gb G also keeps G GB of GPU memory (a screen launches only if in use + 3.7 + G fits the 80% cap).
#1000: a reservation binds resumes too. C189 Amendment 6: --blanket makes it a plain hold that also binds resumes
(hold_resumes=1), and --except-candidate C exempts that candidate's own launches, so one free slot is kept for C's stages.
    .venv/Scripts/python notes/scripts/hold_c193.py [--until-file F | --until-registered NAME] [--reserve-gpu-gb 3.0]
                                                     [--blanket] [--except-candidate C189]
#1043: --reserve-only A,B lets only those runs launch (loop.py's reserve_only line, with reserve_gb 0), and --until-alive A,B
removes the file once each has been seen running: a priority order among resumes.
    .venv/Scripts/python notes/scripts/hold_c193.py --reserve-only C191-WL-s52,C184-WR-s50 --until-alive C191-WL-s52,C184-WR-s50
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
import queue_c90 as Q                                    # noqa: E402

Q.D = ROOT / "runs" / "probe" / "C193-lists-swap-depth"
HOLD, LAST = ROOT / "runs" / "loop" / "HOLD-SCREENS", "C193-s2-search-plus"


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


if __name__ == "__main__":
    until, reg_name, gpu, exc = arg("--until-file"), arg("--until-registered") or LAST, arg("--reserve-gpu-gb"), arg("--except-candidate")
    blanket = "--blanket" in sys.argv
    only = arg("--reserve-only")                          # #1043: only these runs launch (loop.py's reserve_only line)
    alive_names = arg("--until-alive").split(",") if arg("--until-alive") else []   # #1043: released once each was seen running
    until = ROOT / until if until else None
    what = (f"{', '.join(alive_names)} have each been seen running" if alive_names else
            f"{until.relative_to(ROOT).as_posix()} exists" if until else f"{reg_name} launches")
    text = f"C193 Amendment 4, {time.strftime('%Y-%m-%d %H:%M')}: an evaluation's cells take the next free slot or memory until {what}\n"
    if only:
        text += f"reserve_gb=0  (#1043: no RAM kept beyond each launch's own need)\nreserve_only={only}  (#1043: only these may launch; the rest hold)\n"
    elif blanket:
        text += "hold_resumes=1  (C189 Amendment 6: a plain hold; resumes hold too)\n"
    else:
        text += "reserve_gb=6.5  (C194 Amendment 1: a screen or pilot launches only with 8.0 + 6.5 GB free)\n"
        if gpu:
            text += f"reserve_gpu_gb={gpu}  (C196 Amendment 2: and only if GPU in use + its own + {gpu} GB fits the 80% cap)\n"
    if exc:
        text += f"except_candidate={exc}  (C189 Amendment 6: that candidate's stages are exempt)\n"
    HOLD.write_text(text, encoding="utf-8")
    Q.log("Amendment 4: HOLD-SCREENS written; new screens hold until " + what + (f", except {exc}" if exc else ""))
    seen = set()
    while True:
        if alive_names:
            seen |= {n for n in alive_names if Q.alive(n)}
            if seen == set(alive_names):
                break
        elif until.exists() if until else reg_name in Q.reg():
            break
        time.sleep(60)
    HOLD.unlink(missing_ok=True)
    Q.log("Amendment 4: hold released (" + what + "), HOLD-SCREENS removed")
