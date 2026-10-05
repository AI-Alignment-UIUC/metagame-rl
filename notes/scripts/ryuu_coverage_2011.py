"""Coverage of the 2011 season's archived decks (HGSS-on, the format of Worlds 2011, San Diego)
against the ryuu-play fork, by printing: a card counts as covered only if the engine has the same
name in the same printed set (its fullName ends in the set code). A same-name card from another
set is reported apart, since it may be a different card.

Source: ptcgarchive.com/2011-decks (saved 2026-10-05 in notes/data/2011-season-ptcgarchive/decks.html; parsed to
decks.json): one list per archetype, with the card images naming set and number.

  python notes/scripts/ryuu_coverage_2011.py [--json out.json]
"""
import argparse
import collections
import glob
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "notes" / "data" / "2011-season-ptcgarchive"

# ptcgarchive image names spell the set; the engine uses the printed set code.
SET_CODES = {"heartgold-soulsilver": "HS", "unleashed": "UL", "undaunted": "UD", "triumphant": "TM",
             "call-of-legends": "CL", "black-white": "BLW", "black-and-white": "BLW", "emerging-powers": "EPO",
             "hgss-promos": "HGSS", "hgss-black-star-promos": "HGSS", "bw-black-star-promos": "BWP"}


# The engine's codes for the same sets.
ENGINE_CODE = {"HS": "HGSS", "UL": "UNL", "UD": "UND", "TM": "TRM", "BLW": "BW", "CL": "COL"}


def card_name(name: str) -> str:
    """Prime and LEGEND are card frames, not part of the name."""
    return re.sub(r"\s+(Prime|LEGEND|Legend)$", "", name.strip())


def norm(s: str) -> str:
    s = s.replace("é", "e").replace("’", "'")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def parse(path: Path) -> list:
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
        prints = []
        for t in re.findall(r'data-image-title="([^"]+)"', p):
            t = re.sub(r"-ptcgo.*$", "", t.lower())
            m = re.match(r"(.+)-(\d+[a-z]?)$", t)
            if m:
                prints.append([m.group(1), m.group(2)])
        para = re.search(r'<p class="wp-block-paragraph">(.*?)</p>', p, re.S)
        decks.append({"title": title, "cards": cards, "printings": prints,
                      "desc": html.unescape(re.sub(r"<[^>]+>", "", para.group(1))) if para else ""})
    return decks


def engine_index() -> dict:
    idx = collections.defaultdict(set)
    for f in glob.glob(str(ROOT / "ryuu-play/packages/sets/src/**/*.ts"), recursive=True):
        t = open(f, encoding="utf-8").read()
        m = re.search(r"public fullName: string = '((?:[^'\\]|\\.)*)'", t)
        if not m:
            continue
        full = m.group(1).replace("\\'", "'")
        name, code = full.rsplit(" ", 1) if " " in full else (full, "")
        idx[norm(name)].add(code.upper())
    return idx


def printing_of(name: str, prints: list) -> str:
    """The set code of `name` from the deck's card images ("<card>-<set name>-<code>-<num>")."""
    key = norm(card_name(name).replace("&", "and"))
    best = None
    for stem, _num in prints:
        tokens = stem.split("-")
        for k in range(len(tokens), 0, -1):         # longest card-name prefix that matches
            if norm("".join(tokens[:k])) == key:
                rest = tokens[k:]
                if rest:
                    best = rest[-1].upper()
                    for sname, code in SET_CODES.items():
                        if "-".join(rest[:-1]).startswith(sname) or "-".join(rest).startswith(sname):
                            best = code
                return best
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    decks = parse(DATA / "decks.html")
    json.dump(decks, open(DATA / "decks.json", "w"), indent=1)
    eng = engine_index()
    rows, per_deck = [], {}
    for d in decks:
        c = collections.Counter()
        for cnt, name in d["cards"]:
            code = printing_of(name, d["printings"])
            have = eng.get(norm(card_name(name))) or set()
            status = "exact" if code and ENGINE_CODE.get(code, code) in have else ("other-printing" if have else "missing")
            c[status] += cnt
            rows.append({"deck": d["title"], "count": cnt, "name": name, "set": code, "status": status,
                         "engine_sets": sorted(have)})
        per_deck[d["title"]] = dict(c)
        print(f"{d['title'][:24]:24s} {sum(c.values()):2d} cards: exact {c['exact']:2d}, other printing "
              f"{c['other-printing']:2d}, missing {c['missing']:2d}   | {d['desc'][:70]}")
    distinct = {(r["name"], r["set"]) for r in rows}
    miss = {k for k in distinct if any(r["status"] == "missing" and (r["name"], r["set"]) == k for r in rows)}
    other = {k for k in distinct if any(r["status"] == "other-printing" and (r["name"], r["set"]) == k for r in rows)}
    full = sum(1 for v in per_deck.values() if v.get("exact", 0) == sum(v.values()))
    print(f"\n{len(decks)} lists; {full} fully buildable by printing; distinct cards {len(distinct)}: "
          f"{len(distinct) - len(miss) - len(other)} exact, {len(other)} same name other set, {len(miss)} missing")
    agg = collections.Counter()
    for r in rows:
        if r["status"] != "exact":
            agg[(r["name"], r["set"], r["status"], tuple(r["engine_sets"]))] += r["count"]
    print("not covered, by copies across the lists:")
    for (name, code, st, h), n in agg.most_common():
        print(f"  {n:3d}  {name} [{code}] {st}{' (engine: ' + ', '.join(h) + ')' if h else ''}")
    if args.json:
        json.dump({"lists": per_deck, "rows": rows}, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
