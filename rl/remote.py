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
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
JSON_FRAME, REQUEST, RESPONSE = 1, 2, 3
DT = {"uint8": np.uint8, "int16": np.int16, "int32": np.int32, "float32": np.float32}
TOKEN_INPUTS = ("tok_card", "tok_kind", "tok_aux", "glob", "slots", "cand", "n_cand")


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
        self.capture = None     # {worker: [(inputs, pooled)]} while set: slot 0's token inputs and pooled states
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
        by_slot = {}
        for r in requests:
            by_slot.setdefault((r[1]["slot"], bool(r[1].get("greedy"))), []).append(r)
        for (slot, greedy), group in by_slot.items():
            model = models[slot]
            ns = [h["n"] for _, h, _ in group]
            B = sum(ns)

            def cat(k):
                return torch.from_numpy(np.concatenate([a[k] for _, _, a in group])).to(device)

            if group[0][1]["encoding"] == "tokens":
                inputs = [cat(k) for k in TOKEN_INPUTS]
                inputs = [x.view(B, -1) if k != "n_cand" else x for k, x in zip(TOKEN_INPUTS, inputs)]
                if self.capture is not None and slot == 0:
                    logits, value, pooled = model(*inputs, return_pooled=True)
                    pooled, start = pooled.float().cpu().numpy(), 0
                    for (i, h, a), n in zip(group, ns):
                        self.capture.setdefault(i, []).append(
                            ({k: a[k].reshape(n, -1) for k in TOKEN_INPUTS[:5]}, pooled[start:start + n]))
                        start += n
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
            action = logp_all.argmax(-1) if greedy else torch.multinomial(logp_all.exp(), 1).squeeze(1)
            logp = logp_all.gather(1, action[:, None]).squeeze(1)
            action = action.int().cpu().numpy()
            logp, value = logp.cpu().numpy(), value.float().cpu().numpy()
            start = 0
            for (i, h, _), n in zip(group, ns):
                sl = slice(start, start + n)
                self._send(i, RESPONSE, pack_arrays({"id": h["id"], "n": n},
                                                    [("action", action[sl]), ("logp", logp[sl]), ("value", value[sl])]))
                start += n

    def close(self):
        for i in range(len(self.procs)):
            try:
                self.send_json(i, {"cmd": "quit"})
            except OSError:
                pass
