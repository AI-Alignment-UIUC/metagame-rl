import json, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
R = "C:/Users/evanc/Desktop/333/metagame-rl/runs/screens/"
runs = ["scr-resetcap","scr-ctl479","scr-gate479","scr-gatevs479","scr-t60gate479","scr-jsearch479","scr-vs479","scr-league479","scr-turns70","scr-turns120","scr-lamv479","scr-turns40","scr-reset","scr-gamma","scr-resetent","scr-judge2","scr-practice","scr-anchor"]
print("run | iters | moved/it | mean prop P,T,E | mean acc P,T,E | sel-diff (acc-prop) P,T,E | select drift/it P,T,E (moved*acc/D) | total popmean drift/it P,T,E | h_in first->last")
for r in runs:
    try:
        rows=[json.loads(l) for l in open(R+r+"/log.jsonl",encoding='utf-8')]
    except Exception as e:
        print(r, "ERR", e); continue
    sel=[x for x in rows if x.get("select") and x["select"].get("acc") is not None and x["select"].get("prop") is not None]
    if not sel: 
        print(r,"no select rows"); continue
    mv=np.array([x["select"]["moved"] for x in sel],float)
    acc=np.array([x["select"]["acc"] for x in sel]); prop=np.array([x["select"]["prop"] for x in sel])
    D=len(rows[0]["shapes"])
    seld=(mv[:,None]*acc).sum(0)/D/len(sel)
    sh=np.array([np.mean(x["shapes"],0) for x in rows])
    tot=(sh[-1]-sh[0])/max(len(rows)-1,1)
    w=mv/ mv.sum()
    accw=(w[:,None]*acc).sum(0)
    propm=prop.mean(0)
    hin=[x.get("draft",{}).get("h_in") for x in rows]
    hin=[h for h in hin if h is not None]
    print(f"{r} | {rows[0]['iter']}-{rows[-1]['iter']} | {mv.mean():.1f} | {np.round(propm,2)} | {np.round(accw,2)} | {np.round(accw-(w[:,None]*prop).sum(0),2)} | {np.round(seld,3)} | {np.round(tot,3)} | {hin[0] if hin else None}->{hin[-1] if hin else None}")
