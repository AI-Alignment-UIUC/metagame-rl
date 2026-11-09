"""C191 Amendment 3 (runs/probe/C191-energy-start-bracket/record.md): WL s52 resumed from its checkpoint at 44 to 74, once C196's last
h2 stage (C196-setA-h2-pplus2) is registered, since a resume skips the screen reservation. A readout every 5 iterations (49, 54, ...,
74) to readouts.jsonl and the record's log: median P/T/E, the drift a counted iteration over those 5 (select.moved x acc_E / 99), G1
mean5 (c171_read.stage). Stops: drift within +-0.05 at 2 readouts in a row (at rest; E and T reported); median E >= 23 or median
T <= 23 at 2 readouts in a row (W's level); errors over 2% of an iteration's games; the wall kill and row 73 as the other queues.
    .venv/Scripts/python notes/scripts/queue_c191b.py
"""
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "notes" / "scripts"))
sys.path.insert(0, str(ROOT))
import queue_c90 as Q                                    # noqa: E402
import queue_c191 as Q191                                # noqa: E402

D = ROOT / "runs" / "probe" / "C191-energy-start-bracket"
Q.D = D
NAME, AFTER, TO = "C191-WL-s52", "C197-s49-H", 75   # C191 Amendment 4: after C197's last h2 cell, not C196's
RUN = ROOT / "runs" / "screens" / NAME


def readout(rows, it):
    import c171_read as C
    byit = {r["iter"]: r for r in rows}
    d = [byit[i]["select"]["moved"] * byit[i]["select"]["acc"][2] / 99 for i in range(it - 4, it + 1)
         if i in byit and (byit[i].get("select") or {}).get("acc")]
    st = C.stage(RUN, it, 52)
    return {"iter": it, "median_pte": [byit[it]["shape_quartiles"][k][1] for k in ("pokemon", "trainer", "energy")],
            "drift": round(sum(d) / len(d), 4) if d else None, "G1_mean5": st.get("G1_mean5"), "G1_last": st.get("G1_last")}


READS = []


def kill(rows):
    if any(r.get("errors", 0) > 0.02 * max(r.get("games", 1), 1) for r in rows):
        return "errors over 2% of an iteration's games"
    done = {x["iter"] for x in READS}
    for it in sorted({r["iter"] for r in rows if r["iter"] > 44 and (r["iter"] + 1) % 5 == 0} - done):
        if not (RUN / f"population_it{it:04d}.pt").exists():
            continue
        x = readout(rows, it)
        READS.append(x)
        with open(D / "readouts.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(x) + "\n")
        Q.log(f"WL s52 readout at {it}: {json.dumps(x)}")
    last2 = READS[-2:]
    if len(last2) == 2 and all(x["drift"] is not None and abs(x["drift"]) <= 0.05 for x in last2):
        return f"at rest: drift within 0.05 at 2 readouts ({[x['drift'] for x in last2]}), median P/T/E {last2[-1]['median_pte']}"
    if len(last2) == 2 and all(x["median_pte"][2] >= 23 or x["median_pte"][1] <= 23 for x in last2):
        return f"W's level: median E >= 23 or T <= 23 at 2 readouts ({[x['median_pte'] for x in last2]})"
    return None


def main():
    Q.log(f"C191 Amendment 3 queue start: {NAME} resumes to {TO - 1} once {AFTER} is registered")
    while AFTER not in Q.reg():
        time.sleep(60)
    chain = RUN / "chain.sh"
    text = chain.read_text(encoding="utf-8")
    assert "--iters 45" in text and "--resume" in text, "WL s52's chain isn't the one expected"
    chain.write_text(text.replace("--iters 45", f"--iters {TO}").replace("iters 45\"", f"iters {TO}\""), encoding="utf-8", newline="\n")
    s = Q191.make_screens()[NAME]
    chain.write_text(text.replace("--iters 45", f"--iters {TO}").replace("iters 45\"", f"iters {TO}\""), encoding="utf-8", newline="\n")   # make_screens rewrote it
    if (RUN / "STOP").exists():
        (RUN / "STOP").rename(RUN / "STOP.at44")
    Q.log(f"{NAME}: chain set to --iters {TO}; resuming from its checkpoint")
    s.launch(resume=True)
    s.watch(kill)
    Q.log("C191 Amendment 3 queue end")


if __name__ == "__main__":
    main()
