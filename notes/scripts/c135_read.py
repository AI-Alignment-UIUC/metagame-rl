"""C135 (runs/probe/C135-fullwidth-pp/record.md): does the pilot's own full-width search play PlusPower and Gust at the breakpoints?
Reads notes/scripts/audit/c135_worker.js's attack rows (the designated seat's attacks) and each game's results, per arm (G, SV, SP):
  pp@b10  among b10 states (the attack without this turn's PlusPower would leave exactly 10) with PlusPower available (in hand at the
          attack or attached), the share where PlusPower was played first; also the knockout share there;
  g@bG    among bG states (a Pokemon benched at the turn's first decision dies to this attack + 10, the Active at that moment
          wouldn't) with Gust of Wind and PlusPower available (in hand at the turn's first decision or at the attack, or played this
          turn), the share where the Defender was gusted up from the Bench and knocked out;
  also knockouts per damaging attack, PlusPower attached per attack, Gust plays per attacking turn, and Prizes per own turn (the
  designated seat's Prizes taken over half the game's turns). "clean" drops defenders with damage-changing Powers (Mr. Mime's
  Invisible Wall, Ditto's Transform). Then the record's bands. Writes summary.json.
  PYTHONPATH=. .venv/Scripts/python notes/scripts/c135_read.py [--seed 91] [--tag ""]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runs/probe/C135-fullwidth-pp"
POWER = ("Mr. Mime", "Ditto")
r3 = lambda x: None if x is None else round(x, 3)
share = lambda k, n: r3(k / n) if n else None


def read(rows, res):
    dmg = [x for x in rows if x["base"] is not None and x["base"] > 0]
    b10 = [x for x in rows if x["b10state"] and x["ppHand"] + x["pp"] >= 1]
    b10c = [x for x in b10 if not any(str(x["dc"]).startswith(p) for p in POWER)]
    avail = lambda x: (x["gustStart"] or x["gustHand"] or x["gustPlayed"]) and (x["ppStart"] or x["ppHand"] or x["ppPlayed"])
    bg = [x for x in rows if x["bGstate"] and avail(x)]
    prizes = turns = 0
    for g in res:
        seat = 1 if g["seed"] % 2 == 0 else 2
        left = (g.get("prizesLeft") or {}).get(str(seat))
        if left is not None and g.get("turns"):
            prizes += 6 - left
            turns += g["turns"] / 2
    return {"attacks": len(rows), "damaging": len(dmg),
            "pp@b10": share(sum(x["pp"] >= 1 for x in b10), len(b10)), "b10_states": len(b10),
            "ko_at_b10": share(sum(x["ko"] for x in b10), len(b10)),
            "pp@b10_clean": share(sum(x["pp"] >= 1 for x in b10c), len(b10c)), "b10_states_clean": len(b10c),
            "g@bG": share(sum(x["gusted"] and x["ko"] for x in bg), len(bg)), "bG_states": len(bg),
            "ko_per_damaging_attack": share(sum(x["ko"] for x in dmg), len(dmg)),
            "pp_attached_per_attack": share(sum(x["pp"] for x in rows), len(rows)),
            "gust_per_attacking_turn": share(sum(x["gustPlayed"] >= 1 for x in rows), len(rows)),
            "prizes_per_own_turn": r3(prizes / turns) if turns else None, "games": len(res),
            "errors": sum(1 for g in res if g.get("error"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=91)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    out = {}
    for arm in ("G", "SV", "SP"):
        p = OUT / f"{arm}_s{a.seed}{a.tag}.jsonl"
        if p.exists():
            rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
            res = json.loads((OUT / f"{arm}_s{a.seed}{a.tag}.results.json").read_text(encoding="utf-8"))
            out[arm] = read(rows, res)
    if all(k in out for k in ("G", "SV", "SP")):
        g, sv, sp = out["G"]["pp@b10"], out["SV"]["pp@b10"], out["SP"]["pp@b10"]
        out["band"] = ("R-value-knows" if sv is not None and g is not None and sv >= 0.5 and g < 0.1 else
                       "R-value-blind" if sv is not None and sp is not None and sv < 0.15 and sp >= 0.5 else "between")
    (OUT / f"summary{a.tag}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
