"""BENCH-P1 block 1 gates (runs/probe/BENCH/P1/record.md): a P1 pilot against start.pt, on the stored prompt rows of an oracle
run (probe_target_signal's raw probes). Evaluation only; CPU is fine.
  fold         max |card_emb(start) - card_emb(P1)| over all card ids (card_resid folded into the content maps)      kill >= 1e-4
  own-card     the content read's attention mass on the tokens of the option's own card, over card-naming options    kill < 0.95
  swap         swap the encoder outputs of two listed PROMPT tokens (pick options of equal rows otherwise): the pair's
               logits must follow their tokens (each new logit nearer the other option's old one); share of pairs      kill < 0.90
  cosine       the same card's input vector as a HAND token vs a PROMPT token (start 0.46), and two different Trainers in
               hand (start 0.999)                                                  report: >= 0.8 and <= 0.9 = rebuilt
  policy       the P1 pilot's policy against start's over the legal options: mean TV and argmax agreement           kill > 0.03, < 0.95
Without --pilot the P1 model is built from start.pt un-distilled (folded, new weights at their initialisation: lat_qverb and
lat_origin at 0, count_proj random), so the policy gate is expected to fail until rl/warmstart.py has distilled it.

  PYTHONPATH=. .venv/Scripts/python notes/scripts/p1_gates.py [--pilot runs/probe/BENCH/P1/T0.pt] --out runs/probe/BENCH/P1/gates.json
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rl.gpu_matrix import load_policy                                          # noqa: E402
from rl.remote import trim_inputs                                              # noqa: E402
from rl.token_model import build_token_model, count_features, fold_card_content   # noqa: E402

DT = {"tok_card": np.int16, "tok_kind": np.uint8, "tok_aux": np.uint8, "glob": np.uint8, "slots": np.uint8, "cand": np.int16}
HAND, PROMPT = 6, 12


def build_p1(start: str, emb_scale: float = 0.1, origin: int = 1):
    """The un-distilled P1 pilot from a start checkpoint: card_resid folded, cand_latent 3, emb_scale, count_features on. -> (model, fold error)"""
    st = torch.load(ROOT / start, map_location="cpu", weights_only=False)
    cfg = {k: v for k, v in st["config"].items() if k not in ("kind", "n_names", "glob_f", "slot_f", "max_tok", "max_cand", "count_features")}
    c = st["config"]
    m = build_token_model(str(ROOT / "notes/data/cards/pool.json"), str(ROOT / "notes/data/cards/text_emb.npy"), c["n_names"], c["glob_f"],
                          c["slot_f"], c["max_tok"], c["max_cand"], **cfg, count_features=True, cand_latent=3, card_content=1,
                          emb_scale=emb_scale, cand_origin=origin)
    state, err = fold_card_content(st["model"] if "model" in st else st["net"])
    missing, unexpected = m.load_state_dict(state, strict=False)
    assert not unexpected and all(k.startswith(("lat_", "count_proj.")) for k in missing), (missing, unexpected)
    return m.eval(), err


def token_in(m, cid, kind, aux):
    """A token's input vector before the encoder (card + kind + aux [+ count features])."""
    kind, aux = torch.full_like(cid, kind), torch.full_like(cid, aux)
    e = m.card_emb(cid) + m._sc(m.kind(kind)) + m._sc(m.aux(aux))
    return e + m.count_proj(count_features(aux)) if m.count_features else e


def cosines(m, table):
    tr = torch.tensor([i + 1 for i, c in enumerate(table) if c["superType"] == 2])
    cs, itf = [i + 1 for i, c in enumerate(table) if c["name"] == "Computer Search"][0], [i + 1 for i, c in enumerate(table) if c["name"] == "Item Finder"][0]
    cos = torch.nn.functional.cosine_similarity
    with torch.no_grad():
        h, p = token_in(m, tr, HAND, 1), token_in(m, tr, PROMPT, 1)
        hn = torch.nn.functional.normalize(h, dim=-1)
        g = hn @ hn.t()
        off = g[~torch.eye(len(tr), dtype=torch.bool)]
        one = lambda c, k: token_in(m, torch.tensor([c]), k, 1)
    return {"same_card_hand_vs_prompt_computer_search": float(cos(one(cs, HAND), one(cs, PROMPT))),
            "same_card_hand_vs_prompt_trainers_mean": float(cos(h, p).mean()),
            "two_trainers_hand_computer_search_vs_item_finder": float(cos(one(cs, HAND), one(itf, HAND))),
            "two_trainers_hand_pairs_mean": float(off.mean()), "two_trainers_hand_pairs_max": float(off.max())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="ar/data/start.pt")
    ap.add_argument("--pilot", default=None, help="a distilled P1 pilot (.pt); default: the un-distilled P1 built from --start")
    ap.add_argument("--raw", default="runs/probe/C94-oracle/oracle.json.probes.json.gz")
    ap.add_argument("--emb-scale", type=float, default=0.1)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    s, _ = load_policy(a.start, "cpu")
    if a.pilot:
        m, _ = load_policy(a.pilot, "cpu")
        _, fold_err = fold_card_content(torch.load(ROOT / a.start, map_location="cpu", weights_only=False)["model"])
    else:
        m, fold_err = build_p1(a.start, a.emb_scale)
    m.eval()
    assert m.cand_latent == 3, "the pilot has no cand_latent 3 path"
    table = json.load(open(ROOT / "notes/data/cards/pool.json", encoding="utf-8"))["cards"]
    probes = [p for p in json.loads(gzip.open(ROOT / a.raw, "rt").read())["probes"] if p.get("prompt")]
    own, own_pick, unfound = [], [], 0
    swap = {"m": [], "s": []}
    tv, agree = [], []
    with torch.no_grad():
        for st in range(0, len(probes), 32):
            chunk = probes[st:st + 32]
            ins = [torch.from_numpy(np.stack([np.array(p["obs"][k], dtype=DT[k]) for p in chunk])) for k in DT]
            ins.append(torch.tensor([p["obs"]["n_cand"] for p in chunk], dtype=torch.int32))
            ins = trim_inputs(ins, m)
            B = len(chunk)
            tc, tk, ta = ins[0].long(), ins[1].long(), ins[2].long()
            nc = ins[6].long()
            verb, card, s1, s2, name, extra = ins[5].long().view(B, -1, 6).unbind(-1)
            valid = torch.arange(verb.shape[1])[None, :] < nc[:, None]
            lg_m, lg_s = m(*ins)[0], s(*ins)[0]
            for i, p in enumerate(chunk):
                legal = np.array(p["legal"])
                a_, b_ = lg_m[i, legal].double(), lg_s[i, legal].double()
                pm, ps = a_.softmax(0), b_.softmax(0)
                tv.append(float(0.5 * (pm - ps).abs().sum()))
                agree.append(int(a_.argmax() == b_.argmax()))
            for name_, net in (("m", m), ("s", s)):
                x, mask = net.encode(*ins[:5])[:2]
                if name_ == "m":
                    _, found, att = net.content_read(x, mask, tc, tk, ta, verb, card, s1, s2)
                    mass = (att * (tc[:, None, :] == card[..., None])).sum(-1)
                    named = valid & (card != 0)
                    unfound += int((named & ~found).sum())
                    own += mass[named & found].tolist()
                    own_pick += mass[named & found & (verb == 11)].tolist()
                lg0 = net.heads(x, mask, ins[5], ins[6], None, None, tc, tk, ta)[0]
                pairs = [[] for _ in range(3)]       # per row up to 3 disjoint pairs of equal-row pick options with a PROMPT token each
                for b in range(B):
                    opts = []
                    for j in torch.nonzero(valid[b] & (verb[b] == 11) & (card[b] != 0)).flatten().tolist():
                        pos = torch.nonzero(mask[b] & (tk[b] == PROMPT) & (tc[b] == card[b, j])).flatten()
                        if len(pos) and all(card[b, j] != card[b, k] for k, _ in opts):
                            opts.append((j, int(pos[0])))
                    for r in range(3):
                        if 2 * r + 1 < len(opts):
                            (j1, p1), (j2, p2) = opts[2 * r], opts[2 * r + 1]
                            if all(int(t[b, j1]) == int(t[b, j2]) for t in (s1, s2, name, extra)):
                                pairs[r].append((b, j1, j2, p1, p2))
                for r in range(3):
                    if not pairs[r]:
                        continue
                    x2 = x.clone()
                    for b, j1, j2, p1, p2 in pairs[r]:
                        x2[b, p1], x2[b, p2] = x[b, p2].clone(), x[b, p1].clone()
                    lg2 = net.heads(x2, mask, ins[5], ins[6], None, None, tc, tk, ta)[0]
                    for b, j1, j2, _, _ in pairs[r]:
                        oa, ob, na, nb = (float(v) for v in (lg0[b, j1], lg0[b, j2], lg2[b, j1], lg2[b, j2]))
                        if abs(oa - ob) > 1e-4:
                            swap[name_].append((abs(na - ob) < abs(na - oa)) and (abs(nb - oa) < abs(nb - ob)))
    own, own_pick = np.array(own), np.array(own_pick)
    res = {"pilot": a.pilot or f"un-distilled P1 from {a.start} (emb_scale {a.emb_scale})", "probes": len(probes),
           "fold_max_err": fold_err,
           "own_card_attention": {"options": len(own), "min": float(own.min()), "mean": float(own.mean()), "pick_min": float(own_pick.min()),
                                  "card_naming_options_without_zone_token": unfound},
           "swap_pass_share": {"P1": float(np.mean(swap["m"])), "n_pairs": len(swap["m"]), "start": float(np.mean(swap["s"])) if swap["s"] else None,
                               "start_n_pairs": len(swap["s"])},
           "cosines": {"P1": cosines(m, table), "start": cosines(s, table)},
           "policy_vs_start": {"mean_TV": float(np.mean(tv)), "argmax_agreement": float(np.mean(agree)), "n_rows": len(tv)}}
    res["gates"] = {"fold<1e-4": res["fold_max_err"] < 1e-4, "own>=0.95": res["own_card_attention"]["min"] >= 0.95,
                    "swap>=0.9": res["swap_pass_share"]["P1"] >= 0.9, "TV<=0.03": res["policy_vs_start"]["mean_TV"] <= 0.03,
                    "agree>=0.95": res["policy_vs_start"]["argmax_agreement"] >= 0.95,
                    "rebuilt(hand/prompt>=0.8, two trainers<=0.9)": res["cosines"]["P1"]["same_card_hand_vs_prompt_computer_search"] >= 0.8
                    and res["cosines"]["P1"]["two_trainers_hand_computer_search_vs_item_finder"] <= 0.9}
    Path(ROOT / a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
