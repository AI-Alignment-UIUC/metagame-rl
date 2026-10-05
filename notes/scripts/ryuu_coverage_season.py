"""Coverage of a season's archived decks against the ryuu-play fork, by printing.

Each deck card is resolved to its printing (pokemon-tcg-data id) from the archive's card images,
then classed as:
  exact      the engine has this name in the same printed set
  reprint    the engine has this name in another set, and pokemon-tcg-data shows the two
             printings as the same card (HP, types, stage, evolves-from, Powers / Bodies /
             abilities, attacks, weakness, resistance, retreat, rules text)
  different  the engine has this name, but only as a different card (Gengar from Fossil for
             Gengar Prime)
  missing    no engine card of this name
  unresolved the printing couldn't be read from the archive page (counted apart)
A list is buildable when every card is exact or reprint.

Sources: ptcgarchive.com/<year>-decks, saved in notes/data/<year>-season-ptcgarchive/decks.html
(one list per archetype). Card data: PokemonTCG/pokemon-tcg-data, cached in
notes/data/cache/tcgdata/.

  python notes/scripts/ryuu_coverage_season.py 2005 --json notes/data/eval/coverage_2005.json
  python notes/scripts/ryuu_coverage_season.py 2011 --json notes/data/eval/coverage_2011.json
"""
import argparse
import collections
import glob
import html
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TCGDATA_URL = "https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/cards/en/{}.json"
CACHE = ROOT / "notes" / "data" / "cache" / "tcgdata"

# Legal sets per season (pokemon-tcg-data ids), for the archive's printings.
SEASONS = {
    2005: ["ex1", "ex2", "ex3", "ex4", "ex5", "ex6", "ex7", "ex8", "ex9", "pop1", "np", "tk1a", "tk1b", "tk2a", "tk2b"],
    2011: ["hgss1", "hgss2", "hgss3", "hgss4", "col1", "bw1", "hsp", "bwp", "bw2", "bw7", "bw11", "pl1", "pl2", "pl3", "pl4"],
}
# ptcgarchive 2011 image names spell set and code ("rescue-energy-triumphant-tm-90").
ARCHIVE_CODE = {"HS": "hgss1", "UL": "hgss2", "UD": "hgss3", "TM": "hgss4", "CL": "col1", "BLW": "bw1",
                "EPO": "bw2", "BCR": "bw7", "LTR": "bw11", "HGSS": "hsp", "BW": "bwp", "PL": "pl1", "RR": "pl2",
                "SV": "pl3", "AR": "pl4"}
# The engine's printed set codes (end of fullName) -> pokemon-tcg-data ids.
ENGINE_SET = {"BS": "base1", "JU": "base2", "FO": "base3", "TR": "base5", "PR": "basep",
              "RS": "ex1", "SS": "ex2", "RG": "ex6",
              "DP": "dp1", "MD": "dp5", "LA": "dp6", "SF": "dp7", "GE": "dp4", "PL": "pl1",
              "HGSS": "hgss1", "UNL": "hgss2", "UND": "hgss3", "TRM": "hgss4", "COL": "col1",
              "BW": "bw1", "EPO": "bw2", "NVI": "bw3", "NXD": "bw4", "DEX": "bw5", "DRX": "bw6", "BCR": "bw7",
              "PLS": "bw8", "PLF": "bw9", "PLB": "bw10", "LTR": "bw11",
              "XY": "xy1", "FLF": "xy2", "FFI": "xy3", "PHF": "xy4", "PRC": "xy5", "ROS": "xy6", "AOR": "xy7",
              "BKT": "xy8", "BKP": "xy9", "FCO": "xy10",
              "SUM": "sm1", "UPR": "sm5", "CES": "sm7", "TEU": "sm9", "UNB": "sm10", "UNM": "sm11", "CEC": "sm12",
              "SSH": "swsh1", "VIV": "swsh4"}


def norm(s: str) -> str:
    s = s.replace("é", "e").replace("’", "'").replace("δ", "delta").replace("&", "and")
    s = re.sub(r"\s+(Prime|LEGEND|Legend)$", "", s.strip())
    return re.sub(r"[^a-z0-9]", "", s.lower())


def tcg_set(set_id: str) -> list:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{set_id}.json"
    if not f.exists():
        try:
            data = urllib.request.urlopen(TCGDATA_URL.format(set_id), timeout=60).read()
        except Exception as e:                       # a promo or kit set the data lacks
            print(f"  (no pokemon-tcg-data for {set_id}: {e})")
            data = b"[]"
        f.write_bytes(data)
    return json.loads(f.read_text(encoding="utf-8"))


def signature(c: dict) -> str:
    """What makes two printings the same card in play."""
    keep = {k: c.get(k) for k in ("supertype", "subtypes", "hp", "types", "evolvesFrom", "retreatCost", "rules")}
    keep["abilities"] = [(a.get("name"), a.get("type"), a.get("text")) for a in c.get("abilities", [])]
    keep["attacks"] = [(a.get("name"), a.get("cost"), a.get("damage"), a.get("text")) for a in c.get("attacks", [])]
    keep["weaknesses"] = c.get("weaknesses")
    keep["resistances"] = c.get("resistances")
    s = json.dumps(keep, sort_keys=True)
    s = s.replace("Pokémon", "Pokemon").replace("’", "'")
    return re.sub(r"\s+", " ", s)


def near(a: dict, b: dict) -> bool:
    """Same card structure, rules and attack texts at least 90% alike (wording changes between
    printings, e.g. "Basic card" / "basic Energy card"); reported apart, for a check by hand."""
    import difflib
    ja, jb = json.loads(signature(a)), json.loads(signature(b))
    for k in ("supertype", "subtypes", "hp", "types", "evolvesFrom", "retreatCost", "weaknesses", "resistances"):
        if ja.get(k) != jb.get(k):
            return False
    if [x[:3] for x in ja["attacks"]] != [x[:3] for x in jb["attacks"]] or \
            [x[:2] for x in ja["abilities"]] != [x[:2] for x in jb["abilities"]]:
        return False
    ta = json.dumps([ja.get("rules"), [x[3] for x in ja["attacks"]], [x[2] for x in ja["abilities"]]]).lower()
    tb = json.dumps([jb.get("rules"), [x[3] for x in jb["attacks"]], [x[2] for x in jb["abilities"]]]).lower()
    return difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.9


def parse_archive(path: Path) -> list:
    s = path.read_text(encoding="utf-8", errors="replace")
    decks = []
    for p in re.split(r'<h1 class="wp-block-heading"', s)[1:]:
        title = html.unescape(re.sub(r"<[^>]+>", "", p[:p.find("</h1>")].split(">", 1)[1])).strip().rstrip(":")
        table = re.search(r"<table.*?</table>", p, re.S)
        if not table:
            continue
        cards = []
        for cell in re.findall(r"<td>(.*?)</td>", table.group(0), re.S):
            for line in re.split(r"<br\s*/?>", cell):
                t = html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
                m = re.match(r"(\d+)\s*x\s*(.+)", t)
                if m:
                    cards.append([int(m.group(1)), m.group(2).strip()])
        if not cards:
            continue
        ids = []
        for t in re.findall(r'data-image-title="([^"]+)"', p):
            t = re.sub(r"-ptcgo.*$", "", t.strip().lower())
            if re.fullmatch(r"[a-z]+[0-9a-z]*-\d+[a-z]?", t):          # "ex2-60" (2005 pages)
                ids.append(t)
                continue
            m = re.match(r"(.+)-([a-z0-9]+)-(\d+[a-z]?)$", t)              # "...-triumphant-tm-90" (2011)
            if m and m.group(2).upper() in ARCHIVE_CODE:
                ids.append(f"{ARCHIVE_CODE[m.group(2).upper()]}-{m.group(3)}")
        para = re.search(r'<p class="wp-block-paragraph">(.*?)</p>', p, re.S)
        decks.append({"title": title, "cards": cards, "images": ids,
                      "desc": html.unescape(re.sub(r"<[^>]+>", "", para.group(1))) if para else ""})
    return decks


def engine_cards() -> dict:
    """norm(name) -> list of pokemon-tcg-data set ids (None where the engine's set code is unmapped)."""
    idx = collections.defaultdict(list)
    for f in glob.glob(str(ROOT / "ryuu-play/packages/sets/src/**/*.ts"), recursive=True):
        t = open(f, encoding="utf-8").read()
        q = r"'((?:[^'\\]|\\.)*)'"
        nm = re.search(r"public name: string = " + q, t)
        if not nm:
            continue
        name = nm.group(1).replace("\\'", "'")
        # The printed set: the end of fullName when the card has one, else its `set` field.
        fm = re.search(r"public fullName: string = " + q, t)
        sm = re.search(r"public set: string = " + q, t)
        code = fm.group(1).rsplit(" ", 1)[-1] if fm and " " in fm.group(1) else (sm.group(1) if sm else "")
        code = re.sub(r"-\d+$", "", code.upper())                       # "RS-2": a second printing in RS
        idx[norm(name)].append(ENGINE_SET.get(code))
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("year", type=int, choices=sorted(SEASONS))
    ap.add_argument("--json")
    args = ap.parse_args()
    data = ROOT / "notes" / "data" / f"{args.year}-season-ptcgarchive"
    decks = parse_archive(data / "decks.html")
    json.dump(decks, open(data / "decks.json", "w"), indent=1)
    by_id, by_set_name = {}, collections.defaultdict(list)
    for sid in sorted({sid for sid in SEASONS[args.year]} | set(ENGINE_SET.values())):
        for c in tcg_set(sid):
            by_id[c["id"]] = c
            by_set_name[(sid, norm(c["name"]))].append(c)
    eng = engine_cards()
    rows, per = [], {}
    for d in decks:
        imgs = [by_id[i] for i in d["images"] if i in by_id]
        cnt = collections.Counter()
        for n, name in d["cards"]:
            key = norm(name)
            printing = next((c for c in imgs if norm(c["name"]) == key), None)
            have = eng.get(key, [])
            if not have:
                status = "missing"
            elif printing is None:
                # Printing not on the page: covered only if every legal printing of the name that
                # season is a card the engine has.
                legal = [c for sid in SEASONS[args.year] for c in by_set_name.get((sid, key), [])]
                eng_sigs = {signature(c) for s in set(have) if s for c in by_set_name.get((s, key), [])}
                if legal and all(c["id"].split("-")[0] in have or signature(c) in eng_sigs for c in legal):
                    status = "exact" if all(c["id"].split("-")[0] in have for c in legal) else "reprint"
                else:
                    status = "unresolved"
            else:
                pset = printing["id"].split("-")[0]
                if pset in have:
                    status = "exact"
                else:
                    sig = signature(printing)
                    others = [c for s in set(have) if s for c in by_set_name.get((s, key), [])]
                    if any(signature(c) == sig for c in others):
                        status = "reprint"
                    elif any(near(printing, c) for c in others):
                        status = "near-reprint"
                    else:
                        status = "different"
            cnt[status] += n
            rows.append({"deck": d["title"], "count": n, "name": name, "printing": printing["id"] if printing else None,
                         "status": status, "engine_sets": sorted({s or "?" for s in have})})
        per[d["title"]] = dict(cnt)
        ok = cnt["exact"] + cnt["reprint"]
        print(f"{d['title'][:26]:26s} buildable {ok:2d}/{sum(cnt.values())} (+{cnt['near-reprint']:2d} near)  exact {cnt['exact']:2d} "
              f"reprint {cnt['reprint']:2d} different {cnt['different']:2d} missing {cnt['missing']:2d} unresolved {cnt['unresolved']:2d}")
    names = {norm(r["name"]) for r in rows}
    st = collections.defaultdict(set)
    for r in rows:
        st[r["status"]].add(norm(r["name"]))
    full = sum(1 for v in per.values() if v.get("exact", 0) + v.get("reprint", 0) == sum(v.values()))
    tot = collections.Counter()
    for r in rows:
        tot[r["status"]] += r["count"]
    print(f"\n{args.year}: {len(decks)} lists, {full} fully buildable; {len(names)} card names: "
          + ", ".join(f"{k} {len(v)}" for k, v in sorted(st.items()))
          + f"; copies {sum(tot.values())}: " + ", ".join(f"{k} {v}" for k, v in sorted(tot.items())))
    agg = collections.Counter()
    for r in rows:
        if r["status"] not in ("exact", "reprint"):
            agg[(r["name"], r["printing"], r["status"])] += r["count"]
    print("not buildable, by copies across the lists:")
    for (name, pr, s), n in agg.most_common(40):
        print(f"  {n:3d}  {name} [{pr}] {s}")
    if args.json:
        json.dump({"year": args.year, "lists": per, "rows": rows}, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
