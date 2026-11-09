"""Central (GPU) inference for rollout workers (env/remote_worker.js).

The workers play the games; whenever a batch of their decisions needs a policy they send it
here as a framed request (env/framing.js). `RemotePool.collect` runs one collection round: it
sends every worker its "collect" command and, until all of them answer, serves inference
requests in large batches across workers, one forward pass per model slot (0 = the learner,
k = league snapshots), sampling the masked actions on the GPU.
"""
import json
import queue
import struct
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
import torch

from rl import limits

ROOT = Path(__file__).resolve().parent.parent
JSON_FRAME, REQUEST, RESPONSE = 1, 2, 3
DT = {"uint8": np.uint8, "int16": np.int16, "int32": np.int32, "float32": np.float32}
TOKEN_INPUTS = ("tok_card", "tok_kind", "tok_aux", "glob", "slots", "cand", "n_cand")
CHUNK = 2048                # rows a forward pass at most, in a batch with a search's requests (log #148)
CHAIN_GUARD = 5000          # rows in a row a chain pilot may be served without one chain row before the server raises


def trim_inputs(inputs: list, model) -> list:
    """A token batch cut to its longest state and option list (tokens fill from the front and options are counted, so
    the encoder's bounds, env/tokens.js, cost no compute here). A chain pilot (rl/token_model.py chain = K) also keeps
    the last K candidate rows, its chain rows."""
    live = (inputs[1] > 0).long() * torch.arange(1, inputs[1].shape[1] + 1, device=inputs[1].device)
    L = max(13, int(live.amax()))
    M = max(1, int(inputs[6].max()))
    K = int(getattr(model, "chain", 0) or 0)
    out = list(inputs)
    out[:3] = [x[:, :L] for x in out[:3]]
    out[5] = torch.cat([out[5][:, :M * 6], out[5][:, -K * 6:]], 1) if K else out[5][:, :M * 6]
    return out


def enc_of(model) -> dict:
    """The token encoder options a model reads (env/tokens.js canon, chain, history): one slotEnc entry."""
    cfg = getattr(model, "cfg", {})
    return {"canon": int(bool(cfg.get("state_canon", 0))), "chain": int(cfg.get("chain", 0) or 0), "history": int(cfg.get("history", 0) or 0)}


def pack_arrays(header: dict, arrays: list) -> bytes:
    meta, offset, parts = [], 0, []
    for name, arr in arrays:
        arr = np.ascontiguousarray(arr)
        meta.append({"name": name, "dtype": str(arr.dtype), "offset": offset, "length": int(arr.size)})
        b = arr.tobytes()
        parts.append(b + b"\0" * ((8 - len(b) % 8) % 8))
        offset += len(parts[-1])
    h = json.dumps({**header, "arrays": meta}).encode()
    pre = struct.pack("<I", len(h)) + h
    pre += b"\0" * ((8 - len(pre) % 8) % 8)
    return pre + b"".join(parts)


def unpack_arrays(buf: bytes):
    (hl,) = struct.unpack_from("<I", buf, 0)
    header = json.loads(buf[4:4 + hl])
    base = 4 + hl + (8 - (4 + hl) % 8) % 8
    out = {}
    for m in header["arrays"]:
        out[m["name"]] = np.frombuffer(buf, dtype=DT[m["dtype"]], count=m["length"], offset=base + m["offset"])
    return header, out


class RemotePool:
    def __init__(self, n: int):
        self.procs = [subprocess.Popen(["node", str(ROOT / "env" / "remote_worker.js")], cwd=ROOT,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0) for _ in range(n)]
        self.q = queue.Queue()
        self.mem = {}           # (worker, key) -> memory state of a pilot with memory (token_model memory_step)
        self.pace = 0.0         # > 0: after each served batch, rest pace x its GPU time (0.25 holds the GPU to ~80%)
        for i, p in enumerate(self.procs):
            threading.Thread(target=self._reader, args=(i, p), daemon=True).start()

    def _reader(self, i, p):
        f = p.stdout
        while True:
            head = f.read(5)
            if len(head) < 5:
                self.q.put((i, None, None))
                return
            length, kind = struct.unpack("<IB", head)
            payload = bytearray()
            while len(payload) < length - 1:
                chunk = f.read(length - 1 - len(payload))
                if not chunk:
                    self.q.put((i, None, None))
                    return
                payload += chunk
            self.q.put((i, kind, bytes(payload)))

    def _send(self, i, kind, payload: bytes):
        p = self.procs[i]
        p.stdin.write(struct.pack("<IB", len(payload) + 1, kind) + payload)
        p.stdin.flush()

    def send_json(self, i, obj):
        self._send(i, JSON_FRAME, json.dumps(obj).encode())

    @staticmethod
    def _json(payload):
        r = json.loads(payload)
        if not r.get("ok"):
            raise RuntimeError("rollout worker failed: " + r.get("error", "?"))
        return r

    def ask_all(self, msgs: list) -> list:
        """A JSON command to every worker, waiting for each reply (no inference served)."""
        return self.collect(msgs, {}, "cpu")

    def collect(self, msgs: list, models: dict, device: str) -> list:
        """One round of commands, serving inference for `models` ({slot: nn.Module}) meanwhile."""
        self.mem = {}                                     # the models may have changed; no game spans rounds
        self._canon_guard(msgs, models)
        for i, m in enumerate(msgs):
            self.send_json(i, m)
        replies = [None] * len(msgs)
        while any(r is None for r in replies):
            frames = [self.q.get()]
            while True:                                   # take everything already waiting
                try:
                    frames.append(self.q.get_nowait())
                except queue.Empty:
                    break
            requests = []
            for i, kind, payload in frames:
                if kind is None:
                    raise RuntimeError(f"rollout worker {i} exited")
                if kind == JSON_FRAME:
                    replies[i] = self._json(payload)
                elif kind == REQUEST:
                    requests.append((i,) + unpack_arrays(payload))
            if requests:
                self._serve(requests, models, device)
        return replies

    @torch.no_grad()
    def _serve(self, requests, models, device):
        pace = max(self.pace, limits.SERVER_PACE)          # RL_GPU_SHARE sets the least rest (rl/limits.py)
        t0 = time.perf_counter() if pace > 0 and device == "cuda" else None
        self._serve_batches(requests, models, device)
        if t0 is not None:                     # the responses are already sent: the workers play on meanwhile
            torch.cuda.synchronize()
            time.sleep((time.perf_counter() - t0) * pace)

    @torch.no_grad()
    def _serve_batches(self, requests, models, device):
        for i, _, a in requests:                          # finished games: drop their memory states
            for uid in a.get("drop", ()):
                self.mem.pop((i, 2 * int(uid)), None)
                self.mem.pop((i, 2 * int(uid) + 1), None)
        by_slot = {}
        for r in requests:
            by_slot.setdefault((r[1]["slot"], bool(r[1].get("greedy"))), []).append(r)
        for (slot, greedy), group in by_slot.items():
            model = models[slot]
            ns = [h["n"] for _, h, _ in group]
            B = sum(ns)
            searched = any("topk" in h for _, h, _ in group)     # PolicySearchAgent's requests (log #148)
            K = max(int(h.get("topk") or 0) for _, h, _ in group)   # with K > 0 they want the top K options too

            def cat(k):
                return torch.from_numpy(np.concatenate([a[k] for _, _, a in group])).to(device)

            if group[0][1]["encoding"] == "tokens":
                inputs = [cat(k) for k in TOKEN_INPUTS]
                inputs = [x.view(B, -1) if k != "n_cand" else x for k, x in zip(TOKEN_INPUTS, inputs)]
                self._chain_guard(model, inputs[5], B)
                inputs = trim_inputs(inputs, model)
                if getattr(model, "memory", "none") != "none":
                    keys = [(i, int(k)) for i, _, a in group for k in a["keys"]]
                    logits, value, states = model(*inputs, mem_states=[self.mem.get(k) for k in keys])
                    for k, st in zip(keys, states):
                        self.mem[k] = st
                elif searched and B > CHUNK:   # a search's line batches can be large: forward in chunks (log #148)
                    parts = [model(*[x[c:c + CHUNK] for x in inputs]) for c in range(0, B, CHUNK)]
                    logits, value = torch.cat([p[0] for p in parts]), torch.cat([p[1] for p in parts])
                else:
                    logits, value = model(*inputs)
            else:
                logits, value = model(cat("obs").view(B, -1))
            rows, cols, row = [], [], 0
            for _, h, a in group:
                rows.append(np.repeat(np.arange(h["n"]) + row, np.diff(a["legal_offsets"])))
                cols.append(a["legal_ids"])
                row += h["n"]
            mask = torch.zeros(logits.shape, dtype=torch.bool, device=device)
            mask[torch.from_numpy(np.concatenate(rows)).to(device),
                 torch.from_numpy(np.concatenate(cols).astype(np.int64)).to(device)] = True
            logp_all = torch.log_softmax(logits.float().masked_fill(~mask, -1e9), -1)
            # "sampled" marks a sampled action (a greedy one is not), since only sampled ones train the policy (rl/train.py).
            if greedy:
                action = logp_all.argmax(-1)
                sampled = torch.zeros(B, dtype=torch.bool, device=device)
            else:
                action = torch.multinomial(logp_all.exp(), 1).squeeze(1)
                sampled = torch.ones(B, dtype=torch.bool, device=device)
            logp = logp_all.gather(1, action[:, None]).squeeze(1)
            action, sampled = action.int().cpu().numpy(), sampled.cpu().numpy().astype(np.uint8)
            logp, value = logp.cpu().numpy(), value.float().cpu().numpy()
            top = None
            if K:                              # each row's K most likely legal options, best first; -1 past its legal ones
                tv, ti = logp_all.topk(min(K, logp_all.shape[1]), -1)
                ti = torch.where(tv > -1e8, ti, torch.full_like(ti, -1))
                top = np.full((B, K), -1, dtype=np.int32)
                top[:, :ti.shape[1]] = ti.int().cpu().numpy()
                top_lp = np.full((B, K), -1e9, dtype=np.float32)   # their log-probabilities (C133; extra, nothing reads it but C133)
                top_lp[:, :tv.shape[1]] = tv.float().cpu().numpy()
            start = 0
            for (i, h, _), n in zip(group, ns):
                sl = slice(start, start + n)
                extra = [("top", top[sl].reshape(-1)), ("top_lp", top_lp[sl].reshape(-1))] if h.get("topk") else []
                self._send(i, RESPONSE, pack_arrays({"id": h["id"], "n": n, **({"k": K} if extra else {})},
                                                    [("action", action[sl]), ("logp", logp[sl]), ("value", value[sl]),
                                                     ("sampled", sampled[sl])] + extra))
                start += n

    @staticmethod
    def _canon_guard(msgs, models):
        """A state_canon pilot reads the one-token-per-card-per-zone encoding (env/tokens.js canon) and no other model reads
        it, so a token command must send "canon" exactly when its models are canon pilots (the flag loss of log #94 again:
        a worker left on the old encoding feeds the pilot tokens it was never trained on). Refuses a mismatch, and a game
        that mixes canon and other models without "slotEnc" (the workers then encode once). With "slotEnc" (one entry per model
        slot, env/remote_worker.js) each seat is encoded by its own model, so the mix is allowed: the entries must match the
        models' configs."""
        on = {bool(getattr(m, "cfg", {}).get("state_canon", 0)) for m in models.values()}
        if len(on) > 1:
            for m in msgs:
                if m.get("encoding") != "tokens":
                    continue
                se = m.get("slotEnc") or {}
                if {str(s): enc_of(x) for s, x in models.items()} != se:
                    raise RuntimeError("state_canon pilots and other models cannot share a round unless slotEnc covers every "
                                       "model slot with its model's options: the workers encode one way")
        for m in msgs:
            if m.get("cmd") in ("collect", "games", "qprobe") and m.get("encoding") == "tokens" and bool(m.get("canon")) != (True in on):
                raise RuntimeError(f"state_canon pilot {'served' if True in on else 'not in use, yet'} a command with canon="
                                   f"{m.get('canon')!r}; the workers' commands must send \"canon\" from the model config")

    def _chain_guard(self, model, cand, B):
        """A chain pilot whose workers encode no chain rows (a command without "chain", the flag loss of log #94) would
        play as if it had none: after CHAIN_GUARD rows in a row with no chain row in its batches, raise."""
        K = int(getattr(model, "chain", 0) or 0)
        if not K:
            return
        unseen = self.__dict__.setdefault("chain_unseen", {})      # id(model) -> rows served since its last chain row
        has = bool((cand.view(B, -1, 6)[:, -K:, 0] > 0).any())
        n = 0 if has else unseen.get(id(model), 0) + B
        unseen[id(model)] = n
        if n >= CHAIN_GUARD:
            raise RuntimeError(f"chain pilot served without chain rows: {n} rows in a row with none (chain {K}); "
                               "the workers' commands must send \"chain\"")

    def close(self):
        for i in range(len(self.procs)):
            try:
                self.send_json(i, {"cmd": "quit"})
            except OSError:
                pass
