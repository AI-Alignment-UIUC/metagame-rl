#!/usr/bin/env python3
"""Aggregate a recorded Pokémon TCG tournament metagame from ptcgarchive.com.

Given one or more ptcgarchive.com event pages (default: the July 2000 West Coast
Super Trainer Showdown, i.e. the Base–Rocket format), the script

  1. downloads and caches the event page and every linked decklist
     (hosted on pokemontcgarchive.wordpress.com),
  2. parses each list ("4x Hitmonchan", "3x Mewtwo (Movie Promo)"),
  3. classifies cards (Pokémon / Trainer / Energy, Basic / Stage 1 / Stage 2)
     with set data from PokemonTCG/pokemon-tcg-data,
  4. reports archetype concentration (shares, HHI, effective number of
     archetypes), card frequencies, trainer counts, evolution usage, pairwise
     deck similarity and, optionally, coverage against a ryuu-play checkout,
  5. writes CSV / JSON outputs for further analysis.

Examples (on Windows use the `py` launcher; the `python` alias is the Store stub):
  py meta_aggregate.py
  py meta_aggregate.py --event https://ptcgarchive.com/2000-super-trainer-showdown-new-jersey/ ^
                       --sets base1,base2,base3,base5,basep,gym1,gym2
  py meta_aggregate.py --ryuu C:/path/to/ryuu-play --top 30
  py meta_aggregate.py --event URL1 --event URL2        (combined report)

pokemon-tcg-data set ids: base1 Base, base2 Jungle, base3 Fossil, base4 Base Set 2,
base5 Team Rocket, basep Wizards Black Star Promos, gym1 Gym Heroes, gym2 Gym
Challenge, neo1-neo4 Neo, ecard1-ecard3 Expedition/Aquapolis/Skyridge, ex1-ex16 EX era.

Outputs (default: notes/data/<event-slug>/):
  cards.csv            one row per (deck, card)
  decks.csv            one row per deck with counts, flags and signature
  card_frequency.csv   decks containing / total copies / mean copies when present
  archetypes.csv       archive label, deck count, share
  summary.json         headline numbers
Downloads are cached under notes/data/cache/ so re-runs work offline.
Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import html
import itertools
import json
import re
import statistics
import sys
import urllib.request
from collections import Counter
from pathlib import Path

DEFAULT_EVENT = "https://ptcgarchive.com/2000-super-trainer-showdown-california/"
DEFAULT_SETS = "base1,base2,base3,base5,basep"
TCGDATA_URL = "https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/cards/en/{}.json"
DECKLIST_HOSTS = ("pokemontcgarchive.wordpress.com", "ptcgarchive.com")
# ptcgarchive.com links inside an event page that are navigation, not decklists
NON_DECK_RE = re.compile(r"/(wotc-events|wotc-decks|\d{4}-(events|decks|worlds-standings|japanese-events))/?$"
                         r"|[?#]|/(category|tag|page|feed)/")
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

ALIASES = {"nidoran \u2642": "nidoran male", "nidoran \u2640": "nidoran female"}

# ----------------------------------------------------------------------------
# text helpers
# ----------------------------------------------------------------------------

def norm(name: str) -> str:
    """Canonical lowercase card name: straight apostrophes, no accents, one space."""
    s = html.unescape(name).replace("\u2019", "'").replace("\u2018", "'").replace("\xa0", " ")
    s = s.replace("\u00e9", "e").replace("\u00c9", "E").replace("!", "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return ALIASES.get(s, s)


def clean(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).replace("\xa0", " ").strip()


def strip_ann(raw: str) -> str:
    return re.sub(r"\s*\(.*?\)\s*", " ", raw).strip()


def body_of(page: str) -> str:
    m = (re.search(r"<article.*?</article>", page, flags=re.S)
         or re.search(r"<main.*?</main>", page, flags=re.S))
    return m.group(0) if m else page


def to_lines(fragment: str) -> list[str]:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", fragment, flags=re.S)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</(p|div|h[1-6]|li|tr|td)>", "\n", s)
    t = html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ")
    return [ln.strip() for ln in t.split("\n")]


def slug_of(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1] or "event"


# ----------------------------------------------------------------------------
# download / cache
# ----------------------------------------------------------------------------

def fetch(url: str, cache_file: Path, refresh: bool = False) -> str:
    if cache_file.exists() and cache_file.stat().st_size > 0 and not refresh:
        return cache_file.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(text, encoding="utf-8")
    return text


# ----------------------------------------------------------------------------
# event page -> list of decklist entries
# ----------------------------------------------------------------------------

DIVISION_RE = re.compile(r"(division|masters|seniors|juniors)", re.I)
TOKEN_RE = re.compile(
    r"<(h[1-6]|strong|b)[^>]*>(.*?)</\1>"            # headings (division names)
    r"|<a\s[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>",     # links (decklists)
    re.S)


def parse_event(page: str, event_url: str) -> list[dict]:
    body = body_of(page)
    entries, division, per_div = [], "?", Counter()
    for m in TOKEN_RE.finditer(body):
        if m.group(2) is not None:
            text = clean(m.group(2))
            if DIVISION_RE.search(text) and len(text) < 40:
                division = re.sub(r"\s*age\s+division:?", "", text, flags=re.I).strip(" :")
            continue
        href, player = m.group(3), clean(m.group(4))
        if (not player or not any(h in href for h in DECKLIST_HOSTS)
                or NON_DECK_RE.search(href) or href.rstrip("/") == event_url.rstrip("/")):
            continue
        tail = body[m.end(): m.end() + 300].split("<", 1)[0]
        label = clean(tail).strip(" -\u2013\u2014:|\t\n") or "?"
        if entries and entries[-1]["url"] == href:
            # the same link split across two anchors (WordPress artifact): merge
            prev = entries[-1]
            glue = "" if player[:1].islower() else " "
            prev["player"] = (prev["player"] + glue + player).strip()
            if prev["label"] == "?":
                prev["label"] = label
            continue
        per_div[division] += 1
        entries.append({"event": slug_of(event_url), "division": division, "place": per_div[division],
                        "player": player, "label": label, "url": href})
    return entries


# ----------------------------------------------------------------------------
# card database (pokemon-tcg-data)
# ----------------------------------------------------------------------------

def load_card_db(set_ids: list[str], cache_dir: Path, refresh: bool) -> dict:
    db: dict[str, dict] = {}
    for sid in set_ids:
        text = fetch(TCGDATA_URL.format(sid), cache_dir / "tcgdata" / (sid + ".json"), refresh)
        for c in json.loads(text):
            subtypes = c.get("subtypes", [])
            stage = next((s for s in ("Basic", "Stage 1", "Stage 2") if s in subtypes), "-")
            entry = db.setdefault(norm(c["name"]), {"supertype": norm(c["supertype"]), "stage": stage, "sets": []})
            if sid not in entry["sets"]:
                entry["sets"].append(sid)
    return db


def classify(key: str, db: dict) -> tuple[str, str]:
    base = key.replace(" (promo)", "")
    e = db.get(base)
    if e:
        return e["supertype"], e["stage"]
    if "energy" in base:
        return "energy", "-"
    return "?", "?"


# ----------------------------------------------------------------------------
# decklist page -> Counter of cards
# ----------------------------------------------------------------------------

SECTION_RE = re.compile(r"^(pok[e\u00e9]mon|trainers?|energy)\s*\(\d+\)$", re.I)
COUNT_RE = re.compile(r"^(\d+)\s*[x\u00d7]\s+(.+)$")
LOOSE_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z].+)$")
STOP_RE = re.compile(r"^(share this|\d+(st|nd|rd|th)\b)", re.I)


def canonical(name: str, db: dict, corrections: dict, cutoff: float = 0.85) -> str:
    """Map a transcribed name onto the card database, repairing typos with fuzzy matching."""
    if name in db or not db:
        return name
    close = difflib.get_close_matches(name, db.keys(), n=1, cutoff=cutoff)
    if close:
        corrections[name] = close[0]
        return close[0]
    return name


def parse_decklist(page: str, db: dict) -> tuple[Counter, dict, dict]:
    cards, meta, corrections, seen_section = Counter(), {}, {}, False
    for ln in to_lines(body_of(page)):
        if not ln:
            continue
        if SECTION_RE.match(ln):
            seen_section = True
            continue
        if seen_section and STOP_RE.match(ln):
            break
        m = COUNT_RE.match(ln)
        if not m:
            m = LOOSE_RE.match(ln)
            if not (m and seen_section and norm(strip_ann(m.group(2))) in db):
                continue
        n, raw = int(m.group(1)), m.group(2).strip()
        ann = " ".join(re.findall(r"\((.*?)\)", raw))
        base = canonical(norm(strip_ann(raw)), db, corrections)
        key = base + (" (promo)" if "promo" in ann.lower() else "")
        cards[key] += n
        meta[key] = ann
    return cards, meta, corrections


# ----------------------------------------------------------------------------
# ryuu-play card pool (optional)
# ----------------------------------------------------------------------------

RYUU_NAME_RE = re.compile(r"name:\s*string\s*=\s*(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")")


RYUU_CLASS_RE = re.compile(r"export class (\w+)")


def ryuu_names(root: Path, folders: list[str] | None = None) -> set[str]:
    """Names of cards ryuu-play actually registers at runtime.

    A card class only counts if its set's index.ts instantiates it on a line that is
    not commented out (e.g. Fossil Ditto has a class file but `// new Ditto(),`).
    `folders` restricts the pool to sub-folders of packages/sets/src (e.g. ["base-sets"]),
    which matters because coverage is by name and later sets reuse names.
    """
    names = set()
    src = root / "packages" / "sets" / "src"
    roots = [src / f for f in folders] if folders else [src]
    for index in (p for r in roots for p in r.rglob("index.ts")):
        registered = set()
        for line in index.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("//"):
                continue
            registered.update(re.findall(r"new (\w+)\(\)", line))
        if not registered:
            continue
        for f in index.parent.glob("*.ts"):
            if f.name == "index.ts" or f.name.endswith(".spec.ts"):
                continue
            src = f.read_text(encoding="utf-8", errors="replace")
            cls = RYUU_CLASS_RE.search(src)
            m = RYUU_NAME_RE.search(src)
            if cls and m and cls.group(1) in registered:
                names.add(norm((m.group(1) or m.group(2) or "").replace("\\'", "'")))
    return names


# ----------------------------------------------------------------------------
# aggregation
# ----------------------------------------------------------------------------

def summarize_deck(entry: dict, cards: Counter, meta: dict, corrections: dict, db: dict, min_sig: int) -> dict:
    d = dict(entry)
    d["corrections"] = corrections
    counts = Counter()
    evo_names, unresolved, poke = [], [], []
    for key, n in cards.items():
        st, stage = classify(key, db)
        counts[st] += n
        if st == "?":
            unresolved.append(key)
        if st == "pokemon":
            poke.append((key, n))
            if stage in ("Stage 1", "Stage 2"):
                counts["evolution"] += n
                evo_names.append(key)
    poke.sort(key=lambda kv: (-kv[1], kv[0]))
    sig = sorted(k for k, n in poke if n >= min_sig) or sorted(k for k, _ in poke)
    d.update(total=sum(cards.values()), pokemon=counts["pokemon"], trainers=counts["trainer"],
             energy=counts["energy"], evolution_cards=counts["evolution"], evolution_names=sorted(evo_names),
             signature=" / ".join(sig), top_pokemon=" / ".join(k for k, _ in poke[:2]),
             pokemon_lines=", ".join(f"{k} {n}" for k, n in poke), unresolved=unresolved,
             cards=dict(cards), annotations=meta)
    return d


def overlap(a: Counter, b: Counter, keys=None) -> float:
    ks = keys if keys is not None else (set(a) | set(b))
    size = max(sum(a[k] for k in ks), sum(b[k] for k in ks), 1)
    return sum(min(a[k], b[k]) for k in ks) / size


def concentration(labels: list[str]) -> dict:
    c = Counter(labels)
    n = max(len(labels), 1)
    shares = sorted((v / n for v in c.values()), reverse=True)
    hhi = sum(s * s for s in shares)
    return {"archetypes": len(c), "top1_share": shares[0] if shares else 0.0,
            "top2_share": sum(shares[:2]), "hhi": hhi, "effective_archetypes": (1 / hhi) if hhi else 0.0,
            "counts": dict(c.most_common())}


def aggregate(decks: list[dict], db: dict, top: int, ryuu: set[str] | None) -> dict:
    n = len(decks)
    freq, copies = Counter(), Counter()
    for d in decks:
        for k, c in d["cards"].items():
            freq[k] += 1
            copies[k] += c
    card_rows = []
    for k, f in freq.most_common():
        st, stage = classify(k, db)
        card_rows.append({"card": k, "supertype": st, "stage": stage, "decks": f, "share": f / n,
                          "total_copies": copies[k], "mean_copies_when_present": copies[k] / f})

    trainers = [d["trainers"] for d in decks]
    evo_free = sum(1 for d in decks if d["evolution_cards"] == 0)
    single_line = sum(1 for d in decks if len(set(d["evolution_names"])) == 1)

    sims, same, diff, tsims = [], [], [], []
    for a, b in itertools.combinations(decks, 2):
        ca, cb = Counter(a["cards"]), Counter(b["cards"])
        s = overlap(ca, cb)
        sims.append(s)
        (same if a["label"] == b["label"] else diff).append(s)
        tkeys = {k for k in set(ca) | set(cb) if classify(k, db)[0] == "trainer"}
        ta, tb = sum(ca[k] for k in tkeys), sum(cb[k] for k in tkeys)
        tsims.append(sum(min(ca[k], cb[k]) for k in tkeys) / max(1, min(ta, tb)))

    def mean(xs):
        return statistics.mean(xs) if xs else 0.0

    corrections = {}
    for d in decks:
        corrections.update(d["corrections"])
    out = {
        "decks": n,
        "distinct_cards": len(freq),
        "unresolved_names": sorted({k for d in decks for k in d["unresolved"]}),
        "name_corrections": corrections,
        "labels": concentration([d["label"] for d in decks]),
        "signatures": concentration([d["signature"] for d in decks]),
        "top_pokemon_pairs": concentration([d["top_pokemon"] for d in decks]),
        "by_division": {dv: concentration([d["label"] for d in decks if d["division"] == dv])
                        for dv in sorted({d["division"] for d in decks})},
        "by_event": {ev: concentration([d["label"] for d in decks if d["event"] == ev])
                     for ev in sorted({d["event"] for d in decks})},
        "trainers": {"min": min(trainers), "median": statistics.median(trainers), "max": max(trainers),
                     "decks_with_25_plus": sum(t >= 25 for t in trainers)},
        "evolution": {"decks_without_evolutions": evo_free, "decks_with_one_evolution_line": single_line,
                      "evolution_lines": dict(Counter(k for d in decks for k in set(d["evolution_names"])).most_common())},
        "similarity": {"mean": mean(sims), "min": min(sims) if sims else 0, "max": max(sims) if sims else 0,
                       "same_label_mean": mean(same), "different_label_mean": mean(diff),
                       "trainer_suite_overlap_mean": mean(tsims)},
        "card_rows": card_rows,
        "top": top,
    }
    if ryuu is not None:
        missing = {k: {"decks": freq[k], "copies": copies[k]} for k in freq
                   if "(promo)" in k or k not in ryuu}
        buildable = sum(1 for d in decks if not any(k in missing for k in d["cards"]))
        out["ryuu"] = {"pool_size": len(ryuu), "missing": missing, "lists_fully_buildable": buildable}
    return out


# ----------------------------------------------------------------------------
# report / outputs
# ----------------------------------------------------------------------------

def pct(x: float) -> str:
    return f"{100 * x:5.1f}%"


def print_report(decks: list[dict], agg: dict) -> None:
    n = agg["decks"]
    print(f"decks: {n}   distinct cards: {agg['distinct_cards']}   "
          f"unresolved names: {agg['unresolved_names'] or 'none'}")
    if agg["name_corrections"]:
        print("typo corrections applied: " + ", ".join(f"{a} -> {b}" for a, b in agg["name_corrections"].items()))
    print()
    print("PER DECK")
    print(f"{'event':34} {'division':13} pl {'player':20} {'label':30} tot  P  T  E evo | Pokémon lines")
    for d in decks:
        print(f"{d['event'][:34]:34} {d['division'][:13]:13} {d['place']:2d} {d['player'][:20]:20} "
              f"{d['label'][:30]:30} {d['total']:3d} {d['pokemon']:2d} {d['trainers']:2d} {d['energy']:2d} "
              f"{d['evolution_cards']:3d} | {d['pokemon_lines']}")
    print()
    for title, key in (("ARCHETYPES (archive labels)", "labels"),
                       ("ARCHETYPES (Pokémon signature: names with >= min copies)", "signatures"),
                       ("ARCHETYPES (top-2 Pokémon by copies)", "top_pokemon_pairs")):
        c = agg[key]
        print(f"{title}: {c['archetypes']} distinct, top-1 {pct(c['top1_share'])}, top-2 {pct(c['top2_share'])}, "
              f"HHI {c['hhi']:.3f}, effective number {c['effective_archetypes']:.2f}")
        for k, v in c["counts"].items():
            print(f"   {v:3d} {pct(v / n)}  {k}")
        print()
    print("BY DIVISION (labels)")
    for dv, c in agg["by_division"].items():
        print(f"   {dv:14} {c['counts']}  effective {c['effective_archetypes']:.2f}")
    if len(agg["by_event"]) > 1:
        print("BY EVENT (labels)")
        for ev, c in agg["by_event"].items():
            print(f"   {ev:40} {c['counts']}  effective {c['effective_archetypes']:.2f}")
    print()
    t, e = agg["trainers"], agg["evolution"]
    print(f"TRAINERS per deck: min {t['min']}  median {t['median']}  max {t['max']}  "
          f"(decks with 25+: {t['decks_with_25_plus']}/{n})")
    print(f"EVOLUTION: {e['decks_without_evolutions']}/{n} decks run no evolution cards; "
          f"{e['decks_with_one_evolution_line']}/{n} run exactly one evolution line; lines seen: {e['evolution_lines']}")
    s = agg["similarity"]
    print(f"SIMILARITY (shared copies / deck size): mean {s['mean']:.2f}  min {s['min']:.2f}  max {s['max']:.2f}  "
          f"same-label {s['same_label_mean']:.2f}  different-label {s['different_label_mean']:.2f}  "
          f"trainer-suite overlap {s['trainer_suite_overlap_mean']:.2f}")
    print()
    print(f"CARD FREQUENCY (top {agg['top']}): decks / share / total copies / mean copies when present")
    for r in agg["card_rows"][: agg["top"]]:
        print(f"   {r['decks']:3d} {pct(r['share'])} {r['total_copies']:4d} {r['mean_copies_when_present']:4.1f}  "
              f"{r['card']}  [{r['supertype']}/{r['stage']}]")
    if "ryuu" in agg:
        r = agg["ryuu"]
        print()
        print(f"RYUU-PLAY COVERAGE: pool {r['pool_size']} names; lists fully buildable {r['lists_fully_buildable']}/{n}; "
              f"cards used that ryuu-play lacks: "
              + (", ".join(f"{k} ({v['decks']} decks, {v['copies']} copies)" for k, v in
                           sorted(r["missing"].items(), key=lambda kv: -kv[1]["decks"])) or "none"))


def write_outputs(out_dir: Path, decks: list[dict], agg: dict, db: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "cards.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event", "division", "place", "player", "label", "card", "copies", "supertype", "stage", "annotation"])
        for d in decks:
            for k, c in sorted(d["cards"].items()):
                st, stage = classify(k, db)
                w.writerow([d["event"], d["division"], d["place"], d["player"], d["label"], k, c, st, stage,
                            d["annotations"].get(k, "")])
    with open(out_dir / "decks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        cols = ["event", "division", "place", "player", "label", "url", "total", "pokemon", "trainers", "energy",
                "evolution_cards", "evolution_names", "signature", "top_pokemon", "pokemon_lines", "unresolved"]
        w.writerow(cols)
        for d in decks:
            w.writerow([" / ".join(d[c]) if isinstance(d[c], list) else d[c] for c in cols])
    with open(out_dir / "card_frequency.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(agg["card_rows"][0].keys()) if agg["card_rows"] else ["card"])
        w.writeheader()
        w.writerows(agg["card_rows"])
    with open(out_dir / "archetypes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "decks", "share"])
        for k, v in agg["labels"]["counts"].items():
            w.writerow([k, v, v / agg["decks"]])
    summary = {k: v for k, v in agg.items() if k != "card_rows"}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--event", action="append", help="ptcgarchive.com event page (repeatable)")
    ap.add_argument("--sets", default=DEFAULT_SETS, help="comma-separated pokemon-tcg-data set ids for card classification")
    ap.add_argument("--data", type=Path, default=Path(__file__).resolve().parent.parent / "data",
                    help="base directory for cache and outputs (default: notes/data)")
    ap.add_argument("--out", type=Path, help="output directory (default: <data>/<event-slug>)")
    ap.add_argument("--ryuu", type=Path, help="path to a ryuu-play checkout to measure card coverage")
    ap.add_argument("--ryuu-sets", default="", help="comma-separated sub-folders of packages/sets/src to count "
                    "(e.g. base-sets for the WotC-era pool); default: all folders")
    ap.add_argument("--top", type=int, default=40, help="rows in the card-frequency table")
    ap.add_argument("--min-sig-copies", type=int, default=2, help="copies needed for a Pokémon to enter the deck signature")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and re-download everything")
    ap.add_argument("--quiet", action="store_true", help="write outputs only, no report")
    args = ap.parse_args(argv)

    events = args.event or [DEFAULT_EVENT]
    cache = args.data / "cache"
    db = load_card_db([s.strip() for s in args.sets.split(",") if s.strip()], cache, args.refresh)

    entries = []
    for url in events:
        page = fetch(url, cache / (slug_of(url) + ".html"), args.refresh)
        found = parse_event(page, url)
        if not found:
            print(f"warning: no decklist links found on {url}", file=sys.stderr)
        entries.extend(found)
    if not entries:
        print("no decklists found; nothing to do", file=sys.stderr)
        return 1

    decks = []
    for e in entries:
        page = fetch(e["url"], cache / e["event"] / (slug_of(e["url"]) + ".html"), args.refresh)
        cards, meta, corrections = parse_decklist(page, db)
        if not cards:
            print(f"warning: no cards parsed for {e['player']} ({e['url']})", file=sys.stderr)
            continue
        decks.append(summarize_deck(e, cards, meta, corrections, db, args.min_sig_copies))

    folders = [s.strip() for s in args.ryuu_sets.split(",") if s.strip()] or None
    ryuu = ryuu_names(args.ryuu, folders) if args.ryuu else None
    if args.ryuu and not ryuu:
        print(f"warning: no card classes found under {args.ryuu}", file=sys.stderr)
    agg = aggregate(decks, db, args.top, ryuu)

    out_dir = args.out or (args.data / (slug_of(events[0]) if len(events) == 1 else f"combined-{len(events)}-events"))
    write_outputs(out_dir, decks, agg, db)
    if not args.quiet:
        print(f"events: {', '.join(events)}")
        print(f"outputs: {out_dir}")
        print()
        print_report(decks, agg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
