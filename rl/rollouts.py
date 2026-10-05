"""Reads the binary rollout files written by env/runner.js (packRollout)."""
import json
import struct

import numpy as np

DTYPES = {"uint8": np.uint8, "int16": np.int16, "int32": np.int32, "float32": np.float32}


def read_rollout(path: str) -> dict:
    with open(path, "rb") as f:
        buf = f.read()
    (header_len,) = struct.unpack_from("<I", buf, 0)
    header = json.loads(buf[8:8 + header_len].decode("utf-8"))
    base = 8 + header_len + (-header_len) % 8
    out = {"header": header}
    for s in header["sections"]:
        dt = DTYPES[s["dtype"]]
        out[s["name"]] = np.frombuffer(buf, dtype=dt, count=s["length"], offset=base + s["offset"]).copy()
    out["obs"] = out["obs"].reshape(header["T"], header["obsSize"])
    return out


def concat(rollouts: list) -> dict:
    """Merges rollouts from several workers; trajectory ids are made unique per file."""
    out = {}
    traj_base = 0
    legal_base = 0
    keys = ("obs", "action", "logp", "value", "reward", "done", "legal_ids")
    extra = sorted({k for r in rollouts for k in r if k.startswith("obs.")})   # token fields
    parts = {k: [] for k in keys + ("traj", "legal_offsets") + tuple(extra)}
    for r in rollouts:
        for k in keys + tuple(extra):
            parts[k].append(r[k])
        parts["traj"].append(r["traj"].astype(np.int64) + traj_base)
        parts["legal_offsets"].append(r["legal_offsets"][:-1].astype(np.int64) + legal_base)
        traj_base += int(r["traj"].max()) + 1 if len(r["traj"]) else 0
        legal_base += len(r["legal_ids"])
    for k, v in parts.items():
        out[k] = np.concatenate(v) if v else np.zeros(0)
    out["legal_offsets"] = np.concatenate([out["legal_offsets"], [legal_base]]).astype(np.int64)
    return out
