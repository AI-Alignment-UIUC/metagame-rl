import json, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
R = "C:/Users/evanc/Desktop/333/metagame-rl/runs/screens/"
for r in sys.argv[1:]:
    rows=[json.loads(l) for l in open(R+r+"/log.jsonl",encoding='utf-8')]
    print("==",r)
    for x in rows:
        s=x.get("select") or {}
        d=x.get("draft") or {}
        q=x["shape_quartiles"]
        b=x["best"][0] if x.get("best") else {}
        print(x["iter"], "mv",s.get("moved"), "gpc",s.get("games_per_candidate"),"gain",s.get("gain"), "prop",s.get("prop"),"acc",s.get("acc"), "h_in",d.get("h_in"),"h_out",d.get("h_out"), "med",q["pokemon"][1],q["trainer"][1],q["energy"][1], "types",x.get("types"), "topin", b.get("top_in"), "topout", b.get("top_out"))
