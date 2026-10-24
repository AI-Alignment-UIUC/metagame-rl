"""The unattended research loop (log #176). A supervisor outside Claude watches the runs at no token cost and starts a
short, fresh `claude -p` round (notes/round.md) only when something happened, so no session lives long enough to
compact and a dead session loses nothing. Launches go through `launch`, which applies the method's limits as code
(method §1, §5, §8, §10): free slots and RAM, the lineage cap and the prevention floor, at most 2 unadopted
components, no repeated flag, no silent repeat of a launched configuration. Launched runs are detached from the
session that started them, so they outlive it.

  .venv/Scripts/python notes/scripts/loop.py state                  # rebuild runs/loop/state.md and print it
  .venv/Scripts/python notes/scripts/loop.py launch C50-fresh-s1 --candidate C50 --record runs/screens/C50/record.md \
      --kind screen --start prevention --from fresh -- sh runs/screens/C50/chain.sh
  .venv/Scripts/python notes/scripts/loop.py stop C50-fresh-s1      # its STOP file: it ends after the current iteration
  .venv/Scripts/python notes/scripts/loop.py ack C50-fresh-s1 "#181"   # the ended run has its log entry
  .venv/Scripts/python notes/scripts/loop.py pause [hours] | resume | disable | enable
  .venv/Scripts/python notes/scripts/loop.py round [--dry]          # start a round now
  .venv/Scripts/python notes/scripts/loop.py daemon                 # the Task Scheduler entry (task metagame-loop)
  .venv/Scripts/python notes/scripts/loop.py rehash                 # Evan only: accept a change to a frozen file
  .venv/Scripts/python notes/scripts/loop.py install | seed | selftest

State lives in runs/loop/: registry.json (launched runs), sup.json (the supervisor's own), rounds.jsonl and rounds/
(each round's JSON result), handoff.md, state.md, frozen.json, daemon.log, and the switches PAUSE, DISABLED and ALERT.
Interactive sessions touch runs/loop/seen through a hook (.claude/settings.json); no round starts within SEEN_MIN
minutes of it.
"""
import argparse
import ctypes
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOOP = ROOT / "runs" / "loop"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
CLAUDE = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude.exe")
SH = shutil.which("sh") or r"C:\Program Files\Git\usr\bin\sh.exe"
MEMORY = Path.home() / ".claude" / "projects" / "C--Users-evanc-Desktop-333" / "memory"
# The ground truth and its scorer: a round never edits them; a change halts the loop until Evan runs `rehash`.
FROZEN = ["rl/answer_key.py", "notes/data/2000-super-trainer-showdown-california"]

MAX_SLOTS = 3            # method §1: at most 3 screens; pilot trainers count as slots
# What a run holds (#161, #175: a soft-target trainer about 8 GB, a plain fork about 5, a lists h2h 3.3); a launch
# leaves at least RAM_CRIT_GB free after it.
FOOTPRINT_GB = {"pilot": 8.0, "screen": 5.0, "probe": 3.5}
RAM_LOW_GB = 5.0         # wakes a round
RAM_CRIT_GB = 3.0        # two ticks running: the newest trainer gets its STOP file
ROUNDS_PER_DAY = 12      # Evan's cap (log #176)
TICK_S = 600
HEARTBEAT_H = 4.0
EVENT_GAP_MIN = 20       # after a round ends, before an event starts the next one
SLOT_GAP_H = 2.0         # a free slot alone wakes a round at most this often
SEEN_MIN = 45
ROUND_TIMEOUT_MIN = 120
LOOK_OFFSETS = (3, 5, 10, 15, 20, 30)   # method §9
HUMAN = (13.5, 28.0, 18.0)   # the 24 STS 2000 lists' median Pokémon / Trainers / Energy (rl/lab.py HUMAN_SHAPE)
TRAINERS = ("rl.metagame", "rl.train")
SKIP_FLAGS = {"--reseed", "--seed", "--run", "--stop-file", "--out", "--iters", "--resume"}
DRY_ENV, ROUND_ENV = "METAGAME_LOOP_DRY", "METAGAME_LOOP_ROUND"
# What a round may run (Evan, log #176): read anything, run the project's Python and node, read-only git and nvidia-smi.
# Edits are allowed everywhere but runs/loop/ only in a dry round; commits, pushes and deletes are not on the list.
TOOLS = ["Read", "Glob", "Grep", "Agent", "TodoWrite",
         "Bash(.venv/Scripts/python *)", "Bash(.venv/Scripts/python.exe *)", "Bash(node *)", "Bash(nvidia-smi*)",
         "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)", "Bash(git show*)", "Bash(git grep *)",
         "Bash(ls*)", "Bash(cat *)", "Bash(head *)", "Bash(tail *)", "Bash(grep *)", "Bash(wc *)", "Bash(sed -n *)",
         "Bash(date*)", "Bash(echo *)", "Bash(paste *)", "Bash(cut *)", "Bash(sort *)", "Bash(uniq *)", "Bash(tr *)",
         "PowerShell(Get-*)"]


def stamp(t=None) -> str:
    return datetime.fromtimestamp(t or time.time()).strftime("%Y-%m-%d %H:%M")


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def log(msg: str) -> None:
    LOOP.mkdir(parents=True, exist_ok=True)
    with open(LOOP / "daemon.log", "a", encoding="utf-8") as f:
        f.write(f"{stamp()} {msg}\n")


# ---- the machine ------------------------------------------------------------------------------------------------

def _k32():
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = ctypes.c_void_p
    k.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    k.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    k.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_ulonglong)] * 4
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    return k


def creation_time(pid: int):
    """The process's creation time if it is still running, else None (with it, a reused pid is not mistaken for a run)."""
    k = _k32()
    h = k.OpenProcess(0x1000, 0, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        code = ctypes.c_ulong()
        if not k.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:  # STILL_ACTIVE
            return None
        t = [ctypes.c_ulonglong() for _ in range(4)]
        k.GetProcessTimes(h, *[ctypes.byref(x) for x in t])
        return t[0].value
    finally:
        k.CloseHandle(h)


def alive(pid, ctime=None) -> bool:
    if not pid:
        return False
    c = creation_time(pid)
    return c is not None and (ctime is None or c == ctime)


class _Mem(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + \
               [(n, ctypes.c_ulonglong) for n in ("total", "avail", "tpf", "apf", "tv", "av", "aev")]


def ram_gb():
    m = _Mem()
    m.dwLength = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.avail / 2 ** 30, m.total / 2 ** 30


def gpu() -> str:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=30,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.split(",")
        return f"{int(out[0]) / 1024:.1f} of {int(out[1]) / 1024:.1f} GB, {int(out[2])}% busy"
    except Exception:
        return "n/a"


def processes() -> dict:
    """pid -> (ppid, name, command line) for every process, from one CIM query."""
    ps = 'Get-CimInstance Win32_Process | ForEach-Object { "$($_.ProcessId)`t$($_.ParentProcessId)`t$($_.Name)`t$($_.CommandLine)" }'
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=90,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except Exception:
        return {}
    procs = {}
    for line in out.decode("utf-8", "ignore").splitlines():
        f = line.split("\t", 3)
        if len(f) == 4 and f[0].isdigit():
            procs[int(f[0])] = (int(f[1]) if f[1].isdigit() else 0, f[2], f[3])
    return procs


TRAINER_RE = re.compile(r"-m rl\.(metagame|train)\b")
JOB_RE = re.compile(r"-m rl\.\w+|notes[/\\]scripts[/\\](?!loop\.py)\w+\.py")


def unregistered(procs: dict, reg: dict) -> list:
    """Project jobs no registered run started: (pid, is a trainer, command)."""
    roots = {e["pid"] for e in reg.values() if e.get("alive")}
    out = []
    for pid, (ppid, name, cmd) in procs.items():
        if not name.lower().startswith("python") or not JOB_RE.search(cmd or ""):
            continue
        p, seen = ppid, set()
        while p and p not in roots and p in procs and p not in seen:
            seen.add(p)
            p = procs[p][0]
        if p not in roots:
            out.append((pid, bool(TRAINER_RE.search(cmd)), cmd))
    # a python launcher and its child are one job: keep the innermost
    pids = {o[0] for o in out}
    return [o for o in out if not any(procs.get(q, (0,))[0] == o[0] for q in pids)]


def spawn(args, out: Path, env=None, err: Path = None):
    """Start a process detached from this one and from the caller's session (it outlives both)."""
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    out.parent.mkdir(parents=True, exist_ok=True)
    fo = open(out, "ab")
    fe = open(err, "ab") if err else subprocess.STDOUT
    try:
        for extra in ((subprocess.CREATE_BREAKAWAY_FROM_JOB,) if os.name == "nt" else ()) + (0,):
            try:
                return subprocess.Popen([str(a) for a in args], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                        stdout=fo, stderr=fe, creationflags=flags | extra)
            except OSError:
                if not extra:
                    raise
    finally:
        fo.close()
        if err:
            fe.close()


# ---- runs -------------------------------------------------------------------------------------------------------

def rows(path: Path, last=True):
    """The first or last JSON row of a log, or None."""
    try:
        with open(path, "rb") as f:
            if last:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 65536))
            lines = [l for l in f.read(65536).splitlines() if l.strip()]
        return json.loads(lines[-1 if last else 0]) if lines else None
    except (OSError, ValueError, IndexError):
        return None


def tail_rows(path: Path, n: int = 5, window: int = 1 << 21) -> list:
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - window))
            lines = f.read().splitlines()[1:]
    except OSError:
        return []
    out = []
    for l in lines[-n:]:
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def ground_truth(path: Path):
    """A screen's last rows against the human lists, read as screen_watch.py reads them: the 12 decks with the best
    results, their mean shape and its L1 distance from the human medians (last row and mean of 5), the population's
    median, and the share of games ended by deck-out."""
    rs = [r for r in tail_rows(path) if r.get("shapes") and r.get("z")]
    if not rs:
        return None

    def top12(r):
        z = [-1 if x is None else x for x in r["z"]]
        idx = sorted(range(len(z)), key=lambda i: -z[i])[:12]
        return [sum(r["shapes"][i][k] for i in idx) / len(idx) for k in range(3)]

    dist = [sum(abs(a - h) for a, h in zip(top12(r), HUMAN)) for r in rs]
    last = rs[-1]
    med = [sorted(s[k] for s in last["shapes"])[len(last["shapes"]) // 2] for k in range(3)]
    n = max(1, sum(last.get("endings", {}).values()))
    return {"iter": last.get("iter"), "top12": top12(last), "dist": dist[-1], "dist5": sum(dist) / len(dist),
            "median": med, "deckout": last.get("endings", {}).get("deck-out", 0) / n}


def iteration(row):
    return None if row is None else row.get("iter", row.get("iteration"))


def progress(e) -> Path:
    return ROOT / (e.get("progress") or (e["run"] + "/log.jsonl"))


def looks(e) -> list:
    if e.get("looks"):
        return e["looks"]
    base = e.get("it0")
    if base is None:
        base = iteration(rows(progress(e), last=False))
        base = None if base is None else base - 1
    return [] if base is None else [base + o for o in LOOK_OFFSETS]


def registry(mark=True) -> dict:
    reg = load(LOOP / "registry.json", {})
    if mark:
        for e in reg.values():
            e["alive"] = not e.get("legacy") and alive(e.get("pid"), e.get("ctime"))
    return reg


def save_registry(reg: dict) -> None:
    save(LOOP / "registry.json", {k: {f: v for f, v in e.items() if f != "alive"} for k, e in reg.items()})


def invocations(cmd: list) -> list:
    """Token lists of the python commands a launch runs: the command itself, or each python line of the .sh it runs."""
    script = next((c for c in cmd if c.endswith(".sh")), None)
    if script is None:
        return [cmd] if any("python" in c for c in cmd) else []
    text = (ROOT / script).read_text(encoding="utf-8", errors="ignore").replace("\\\n", " ")
    out = []
    for line in text.splitlines():
        if "python" in line and not line.lstrip().startswith("#"):
            try:
                out.append(shlex.split(line, comments=True))
            except ValueError:
                continue
    return out


def flag_pairs(toks: list) -> list:
    pairs, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t.startswith("--") and len(t) > 2:
            if "=" in t:
                f, v = t.split("=", 1)
            else:
                nxt = toks[i + 1] if i + 1 < len(toks) else None
                v = nxt if nxt is not None and not nxt.startswith("--") and not re.match(r"\d?>|<|&|\|", nxt) else True
                f = t
                i += v is not True
            pairs.append((f, v))
        i += 1
    return pairs


def repeated(toks: list) -> list:
    seen, rep = set(), []
    for f, _ in flag_pairs(toks):
        if f in seen and f not in rep:
            rep.append(f)
        seen.add(f)
    return rep


def trainer(cmd: list):
    for toks in invocations(cmd):
        if "-m" in toks and any(m in toks for m in TRAINERS):
            return toks
    return None


def signature(cmd: list):
    """The training command's module, flags and values, without seeds and the paths that only name the run."""
    t = trainer(cmd)
    if not t:
        return None
    mod = next(m for m in TRAINERS if m in t)
    return json.dumps([mod] + sorted([f, str(v)] for f, v in flag_pairs(t) if f not in SKIP_FLAGS))


def seeds(cmd: list) -> dict:
    t = trainer(cmd) or []
    return {f: str(v) for f, v in flag_pairs(t) if f in ("--seed", "--reseed")}


def floor_problems(reg: dict, start: str, frm: str) -> list:
    """Method §8 for a new screen: at most 2 live on one start state, at most half of 10 from one state, and one
    prevention start in every 4."""
    screens = sorted((e for e in reg.values() if e.get("kind") == "screen"), key=lambda e: e.get("launched", ""))
    p = []
    if frm != "fresh":
        live_same = sum(1 for e in screens if e.get("alive") and e.get("from") == frm)
        if live_same >= 2:
            p.append(f"2 live screens already start from {frm} (§8: at most 2 of 3 slots on one lineage)")
        n = sum(1 for e in screens[-9:] if e.get("from") == frm) + 1
        if n > 5:
            p.append(f"{n} of the last 10 screens would start from {frm} (§8: at most half from one state)")
    last3 = screens[-3:]
    if start != "prevention" and len(last3) == 3 and all(e.get("start") != "prevention" for e in last3):
        p.append("none of the last 3 screens was a prevention start, so this one must be (§8: one in every 4)")
    return p


def launch_problems(a, cmd: list, reg: dict, free_gb: float, slots_used: int) -> list:
    p = []
    if not re.fullmatch(r"C\d+[a-z]?", a.candidate or ""):
        p.append("--candidate must be a candidate id like C50 (§10)")
    rec = ROOT / a.record if a.record else None
    if not rec or not rec.is_file():
        p.append("--record must name the run's record, written before launch (§10)")
    else:
        text = rec.read_text(encoding="utf-8", errors="ignore").lower()
        p += [f"the record has no {w} (§10)" for w in ("bands", "kill") if w not in text]
    if not cmd:
        p.append("no command after --")
    old = reg.get(a.name)
    if old and not a.resume:
        p.append(f"{a.name} is already registered; pick a new name, or pass --resume to continue it")
    if old and old.get("alive"):
        p.append(f"{a.name} is still running (pid {old['pid']})")
    slot = a.kind in ("screen", "pilot")
    if slot and slots_used >= MAX_SLOTS:
        p.append(f"{slots_used} of {MAX_SLOTS} slots are busy (§1)")
    need = FOOTPRINT_GB[a.kind] + RAM_CRIT_GB
    if free_gb < need:
        p.append(f"free RAM {free_gb:.1f} GB is under the {need:.1f} GB a {a.kind} needs ({FOOTPRINT_GB[a.kind]:.1f} "
                 f"held, {RAM_CRIT_GB:.0f} left over; #175)")
    if len(a.components) > 2:
        p.append(f"{len(a.components)} unadopted components; a launch stacks at most 2 on a recipe (§10)")
    for toks in invocations(cmd):
        rep = repeated(toks)
        if rep:
            p.append(f"flag(s) {', '.join(rep)} passed twice in one command (§10)")
    if a.kind == "screen" and not a.evan_row and not a.resume:
        p += floor_problems(reg, a.start, a.frm)
    sig = signature(cmd)
    if sig and not a.resume:
        same = [k for k, e in reg.items() if e.get("sig") == sig and k != a.name]
        if same and not a.replicate_of:
            p.append(f"the same configuration as {same[0]}; a replication passes --replicate-of {same[0]} and a new "
                     f"seed (§5: no silent repeats)")
        if a.replicate_of:
            base = reg.get(a.replicate_of)
            if not base:
                p.append(f"--replicate-of {a.replicate_of} is not registered")
            elif base.get("seeds") == seeds(cmd):
                p.append(f"the same seeds as {a.replicate_of}: a replication needs a new --reseed or --seed")
    return p


def live_slots(reg: dict, procs: dict) -> int:
    own = sum(1 for e in reg.values() if e.get("alive") and e.get("kind") in ("screen", "pilot"))
    return own + sum(1 for _, is_trainer, _ in unregistered(procs, reg) if is_trainer)


def resolve(cmd: list) -> list:
    if cmd[0] == "sh" or cmd[0].endswith(".sh"):
        return [SH] + (cmd[1:] if cmd[0] == "sh" else cmd)
    if cmd[0].startswith(".venv"):
        return [str(ROOT / cmd[0])] + cmd[1:]
    return cmd


def launch(a, cmd: list) -> None:
    if os.environ.get(DRY_ENV):
        sys.exit(f"dry run: launch refused (it would run {' '.join(cmd)})")
    reg = registry()
    free, _ = ram_gb()
    problems = launch_problems(a, cmd, reg, free, live_slots(reg, processes()))
    if problems:
        print("launch refused:\n  - " + "\n  - ".join(problems))
        sys.exit(2)
    run = ROOT / a.run
    run.mkdir(parents=True, exist_ok=True)
    p = spawn(resolve(cmd), run / "launch.log", env=dict(os.environ))
    e = {"candidate": a.candidate, "kind": a.kind, "run": a.run.replace("\\", "/"), "record": a.record,
         "start": a.start, "from": a.frm, "components": a.components, "evan_row": a.evan_row,
         "looks": [int(x) for x in a.looks.split(",")] if a.looks else None, "look_wait": a.look_wait, "until": a.until,
         "progress": a.progress or None, "cmd": cmd, "sig": signature(cmd), "seeds": seeds(cmd),
         "replicate_of": a.replicate_of, "pid": p.pid, "ctime": creation_time(p.pid), "launched": stamp(),
         "git": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                               text=True).stdout.strip(), "it0": None}
    if a.resume or e["looks"] is None:
        e["it0"] = iteration(rows(progress(e)))
    if a.name in reg:
        e["history"] = reg[a.name].get("history", []) + [{k: reg[a.name].get(k) for k in ("pid", "launched", "acked")}]
    reg[a.name] = e
    save_registry(reg)
    sup = load(LOOP / "sup.json", {})
    sup.get("ended", {}).pop(a.name, None)
    sup.get("looked", {}).pop(a.name, None)
    save(LOOP / "sup.json", sup)
    print(f"{a.name}: pid {p.pid}, looks at {looks(e) or 'offsets ' + str(LOOK_OFFSETS) + ' from its first iteration'}")


def stop_file(e) -> Path:
    """The STOP file of the run's first trainer, with a chain script's own variables (run=...) filled in."""
    cmd = e.get("cmd", [])
    script = next((c for c in cmd if c.endswith(".sh")), None)
    var = {"run": e["run"]}
    if script and (ROOT / script).exists():
        text = (ROOT / script).read_text(encoding="utf-8", errors="ignore")
        var.update((m.group(1), m.group(2).strip('"')) for m in re.finditer(r"^(\w+)=(\S+)\s*$", text, re.M))
    for toks in invocations(cmd):
        for f, v in flag_pairs(toks):
            if f == "--stop-file" and v is not True:
                return ROOT / re.sub(r"\$\{?(\w+)\}?", lambda m: var.get(m.group(1), m.group(0)), v)
    return ROOT / e["run"] / "STOP"


# ---- integrity --------------------------------------------------------------------------------------------------

def frozen_hashes() -> dict:
    out = {}
    for rel in FROZEN:
        p = ROOT / rel
        for f in (sorted(p.rglob("*")) if p.is_dir() else [p]):
            if f.is_file():
                out[f.relative_to(ROOT).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def frozen_changes() -> list:
    ref = load(LOOP / "frozen.json", None)
    now = frozen_hashes()
    if ref is None:
        save(LOOP / "frozen.json", now)
        return []
    return sorted(k for k in set(ref) | set(now) if ref.get(k) != now.get(k))


# ---- the supervisor ---------------------------------------------------------------------------------------------

def rounds_today() -> int:
    day = datetime.now().strftime("%Y%m%d")
    try:
        lines = (LOOP / "rounds.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    return sum(1 for l in lines if '"start"' in l and json.loads(l).get("ts", "").startswith(day))


def blocked(sup: dict):
    now = time.time()
    if (LOOP / "DISABLED").exists():
        return "disabled"
    if (LOOP / "ALERT").exists():
        return "integrity alert (runs/loop/ALERT)"
    if (LOOP / "PAUSE").exists():
        until = (LOOP / "PAUSE").read_text(encoding="utf-8").strip()
        if not until or until > stamp():
            return f"paused{' until ' + until if until else ''}"
    seen = LOOP / "seen"
    if seen.exists() and now - seen.stat().st_mtime < SEEN_MIN * 60:
        return f"Evan's session active {int((now - seen.stat().st_mtime) / 60)} min ago"
    r = sup.get("round")
    if r and alive(r.get("pid"), r.get("ctime")):
        return f"round {r['ts']} running"
    if rounds_today() >= ROUNDS_PER_DAY:
        return f"daily cap of {ROUNDS_PER_DAY} rounds reached"
    return None


def wake_reason(sup: dict, free_slots: int):
    now = time.time()
    since_end = now - sup.get("last_end", 0)
    if sup.get("pending") and since_end >= EVENT_GAP_MIN * 60:
        return "; ".join(sup["pending"])
    if free_slots and since_end >= SLOT_GAP_H * 3600:
        return f"{free_slots} free slot(s)"
    if now - sup.get("last_start", 0) >= HEARTBEAT_H * 3600:
        return "heartbeat (no round for 4 h)"
    return None


def finish_round(sup: dict) -> None:
    r = sup.get("round")
    if not r:
        return
    if alive(r.get("pid"), r.get("ctime")):
        if time.time() - r["start"] < ROUND_TIMEOUT_MIN * 60:
            return
        subprocess.run(["taskkill", "/PID", str(r["pid"]), "/T", "/F"], capture_output=True)
        r["timeout"] = True
    out = LOOP / "rounds" / f"{r['ts']}.json"
    res = load(out, {}) if out.exists() else {}
    row = {"ts": r["ts"], "event": "end", "dry": r.get("dry"), "minutes": round((time.time() - r["start"]) / 60),
           "timeout": r.get("timeout", False), "turns": res.get("num_turns"), "cost_usd": res.get("total_cost_usd"),
           "error": res.get("is_error"), "denied": [d.get("tool_name") for d in res.get("permission_denials", [])],
           "result": (res.get("result") or "")[-400:]}
    append(LOOP / "rounds.jsonl", row)
    log(f"round {r['ts']} ended: {row['minutes']} min, {row['turns']} turns, denied {len(row['denied'])}")
    sup["last_end"], sup["round"] = time.time(), None


def tick(sup: dict) -> None:
    sup.setdefault("pending", [])
    sup.setdefault("ended", {})
    sup.setdefault("looked", {})

    def add(ev):
        if ev not in sup["pending"]:
            sup["pending"].append(ev)

    bad = frozen_changes()
    if bad and not (LOOP / "ALERT").exists():
        (LOOP / "ALERT").write_text(f"{stamp()} frozen files changed: {', '.join(bad)}\nNo round starts until Evan "
                                    f"checks them and runs `loop.py rehash`.\n", encoding="utf-8")
        log("ALERT: " + ", ".join(bad))
    reg = registry()
    for rid, e in reg.items():
        if e.get("legacy") or e.get("acked"):
            continue
        it = iteration(rows(progress(e)))
        if not e["alive"]:
            if rid not in sup["ended"]:
                sup["ended"][rid] = stamp()
                add(f"{rid} ended at iteration {it}")
            continue
        due = [lk for lk in looks(e) if it is not None and it >= lk > sup["looked"].get(rid, -1)]
        if due:
            # a run whose own watcher reads the look (--look-wait) wakes a round only when the readings can be there
            seen = sup.setdefault("reached", {}).setdefault(rid, {}).setdefault(str(due[-1]), time.time())
            if time.time() - seen >= (e.get("look_wait") or 0) * 60:
                sup["looked"][rid] = due[-1]
                add(f"{rid} reached its look at {due[-1]} (now {it})")
    free, _ = ram_gb()
    sup["crit"] = sup.get("crit", 0) + 1 if free < RAM_CRIT_GB else 0
    if sup["crit"] >= 2:
        live = sorted((e for e in reg.values() if e["alive"] and e.get("kind") in ("screen", "pilot")),
                      key=lambda e: e["launched"])
        if live:
            name = next(k for k, v in reg.items() if v is live[-1])
            stop_file(live[-1]).write_text("stop: RAM critical (loop.py)\n")
            add(f"free RAM {free:.1f} GB twice running: wrote {name}'s STOP file (newest trainer)")
            log(f"RAM {free:.1f} GB: stopped {name}")
        sup["crit"] = 0
    elif free < RAM_LOW_GB:
        add(f"free RAM {free:.1f} GB")
    finish_round(sup)
    why = blocked(sup)
    if why:
        sup["blocked"] = why
        return
    sup["blocked"] = None
    reason = wake_reason(sup, max(0, MAX_SLOTS - live_slots(reg, processes())))
    if reason:
        start_round(sup, reason)


def start_round(sup: dict, reason: str, dry: bool = False) -> None:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    write_state(reason, dry)
    prompt = (f"[metagame-loop] Unattended round {ts}{' (DRY RUN)' if dry else ''}. "
              f"Read notes/round.md and follow it exactly.")
    edits = ["Edit(runs/loop/**)", "Write(runs/loop/**)"] if dry else ["Edit", "Write"]
    args = [CLAUDE, "-p", prompt, "--model", "opus", "--permission-mode", "dontAsk", "--output-format", "json",
            "--add-dir", str(MEMORY), "--allowedTools", *TOOLS, *edits]
    # Evan (log #177): rounds run on his Claude plan's login, never on a billed API key
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    env.update({ROUND_ENV: ts, **({DRY_ENV: "1"} if dry else {})})
    out = LOOP / "rounds" / f"{ts}.json"
    p = spawn(args, out, env=env, err=out.with_suffix(".err"))
    sup["round"] = {"ts": ts, "pid": p.pid, "ctime": creation_time(p.pid), "reason": reason, "dry": dry,
                    "start": time.time()}
    sup["pending"], sup["last_start"], sup["reached"] = [], time.time(), {}
    append(LOOP / "rounds.jsonl", {"ts": ts, "event": "start", "dry": dry, "reason": reason, "pid": p.pid})
    log(f"round {ts} started{' (dry)' if dry else ''}: {reason}")


def daemon() -> None:
    me = LOOP / "daemon.json"
    d = load(me, {})
    if alive(d.get("pid"), d.get("ctime")):
        return
    save(me, {"pid": os.getpid(), "ctime": creation_time(os.getpid()), "started": stamp()})
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x1)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED: no sleep
    log("supervisor started")
    while not (LOOP / "DISABLED").exists():
        try:
            sup = load(LOOP / "sup.json", {})
            tick(sup)
            save(LOOP / "sup.json", sup)
        except Exception:
            log("tick failed:\n" + traceback.format_exc())
        time.sleep(TICK_S)
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    log("disabled: supervisor exits")


# ---- the state a round starts from ------------------------------------------------------------------------------

def section(text: str, start: str, stop_re: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    m = re.compile(stop_re, re.M).search(text, i + len(start))
    return text[i:m.start() if m else len(text)].strip()


def write_state(reason: str = "", dry: bool = False) -> str:
    reg, sup, procs = registry(), load(LOOP / "sup.json", {}), processes()
    free, total = ram_gb()
    bad = frozen_changes()
    L = [f"# Loop state, {stamp()}", "", "Rebuilt by `notes/scripts/loop.py state` before every round; do not edit.", ""]
    if reason:
        L.append(f"**Why this round:** {reason}." + (" **DRY RUN** (notes/round.md, Dry runs)." if dry else ""))
    r = sup.get("round")
    L.append(f"**Loop:** {blocked(sup) or 'on'}; {rounds_today()} of {ROUNDS_PER_DAY} rounds today; last round "
             f"{'ended ' + stamp(sup['last_end']) if sup.get('last_end') else 'none'}"
             f"{'; round ' + r['ts'] + ' recorded as running' if r else ''}.")
    L.append(f"**Machine:** RAM free {free:.1f} of {total:.1f} GB; GPU {gpu()}; slots busy {live_slots(reg, procs)} of "
             f"{MAX_SLOTS}.")
    L.append("**Integrity:** " + ("frozen files unchanged." if not bad else "CHANGED: " + ", ".join(bad)
                                  + " (the loop halts; Evan checks them)."))
    L += ["", "## Live runs (registered)", ""]
    live = [(k, e) for k, e in reg.items() if e["alive"]]
    if live:
        L += ["| run | C | kind | start | iteration | looks | launched |", "|---|---|---|---|---|---|---|"]
        for k, e in live:
            it = iteration(rows(progress(e)))
            lk = looks(e)
            nxt = next((x for x in lk if it is None or x > it), None)
            L.append(f"| {k} | {e['candidate']} | {e['kind']} | {e['start']} from {Path(e['from']).name} | {it} | "
                     f"{','.join(map(str, lk)) or 'from first iteration'} (next {nxt}) | {e['launched']} |")
    else:
        L.append("None.")
    L += ["", "## Ground truth (the 24 STS 2000 lists)", "",
          "Median 13.5 / 28 / 18 Pokémon / Trainers / Energy, 8 archetypes. Targets (method §3): the best decks' shape "
          "within 5 of each median, at least 3 archetypes, the best decks at least 0.5 against the lists under a pilot "
          "that passes the pilot rows. A consistent deviation (more Energy, fewer Trainers, one type) means part of the "
          "process is wrong. Live screens first, then the last 3 finished ones for reference:", "",
          "| screen | iteration | best 12 P / T / E | distance (last; mean of 5) | population median | deck-outs |",
          "|---|---|---|---|---|---|"]
    shown = [(k, e) for k, e in reg.items() if e["alive"] and e.get("kind") == "screen"]
    shown += sorted(((k, e) for k, e in reg.items() if not e["alive"] and e.get("kind") == "screen"),
                    key=lambda x: x[1].get("launched", ""))[-3:]
    for k, e in shown:
        g = ground_truth(progress(e))
        if g:
            L.append(f"| {k}{' (live)' if e['alive'] else ''} | {g['iter']} | "
                     f"{' / '.join(f'{x:.1f}' for x in g['top12'])} | {g['dist']:.1f}; {g['dist5']:.1f} | "
                     f"{' / '.join(f'{x:g}' for x in g['median'])} | {g['deckout']:.2f} |")
    ended = [(k, e) for k, e in reg.items() if not e["alive"] and not e.get("legacy") and not e.get("acked")]
    L += ["", "## Ended, not yet logged", ""]
    L += [f"- {k} ({e['candidate']}, {e['run']}): ended by {sup.get('ended', {}).get(k, 'now')}, last iteration "
          f"{iteration(rows(progress(e)))}; log it, then `loop.py ack {k} \"#nnn\"`." for k, e in ended] or ["None."]
    un = unregistered(procs, reg)
    L += ["", "## Project jobs not started through loop.py", ""]
    L += [f"- pid {pid}{' (trainer, counts as a slot)' if t else ''}: {cmd[:220]}" for pid, t, cmd in un] or ["None."]
    screens = sorted((e for e in reg.values() if e.get("kind") == "screen"), key=lambda e: e.get("launched", ""))
    counts = {}
    for e in screens[-10:]:
        counts[e["from"]] = counts.get(e["from"], 0) + 1
    L += ["", "## Exploration floor (method §8, enforced by `loop.py launch`)", "",
          f"- Last 10 screens by start state: " + "; ".join(f"{n} from {k}" for k, n in counts.items()) + ".",
          f"- Starts of the last 4: {', '.join(e['start'] for e in screens[-4:]) or 'none'}."]
    for s in sorted(counts):
        why = floor_problems(reg, "escape", s)
        if why:
            L.append(f"- A new escape screen from {s} is refused: {'; '.join(why)}.")
    if floor_problems(reg, "escape", "fresh"):
        L.append("- The next screen must be a prevention start.")
    handoff = LOOP / "handoff.md"
    L += ["", "## Last handoff (runs/loop/handoff.md)", ""]
    L += [handoff.read_text(encoding="utf-8").strip()] if handoff.exists() else ["None yet."]
    logtext = (ROOT / "notes" / "progress-log.md").read_text(encoding="utf-8", errors="ignore")
    L += ["", "## Last 3 log entries", ""] + [h for h in re.findall(r"^### #\d+ .*$", logtext, re.M)[-3:]]
    readme = (ROOT / "README.md").read_text(encoding="utf-8", errors="ignore")
    L += ["", "## README Next", "", section(readme, "**Next:**", r"^<!-- status:end -->")]
    req = (ROOT / "notes" / "evan-requests.md").read_text(encoding="utf-8", errors="ignore")
    L += ["", "## Evan's open requests (notes/evan-requests.md)", "", section(req, "## Not tried yet", r"^## ")]
    text = "\n".join(L) + "\n"
    LOOP.mkdir(parents=True, exist_ok=True)
    (LOOP / "state.md").write_text(text, encoding="utf-8")
    return text


# ---- setup, switches, selftest ----------------------------------------------------------------------------------

def install() -> None:
    """Register the Task Scheduler entry: the supervisor at logon and every 10 minutes (one instance; it exits when
    DISABLED)."""
    pyw = ROOT / ".venv" / "Scripts" / "pythonw.exe"
    ps = (f"$a = New-ScheduledTaskAction -Execute '{pyw}' -Argument 'notes\\scripts\\loop.py daemon' "
          f"-WorkingDirectory '{ROOT}'\n"
          "$t = @(New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval "
          "(New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 3650))\n"
          "try { $t += New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME } catch {}\n"
          "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
          "-ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew\n"
          "Register-ScheduledTask -TaskName 'metagame-loop' -Action $a -Trigger $t -Settings $s -Force | Out-Null\n"
          "(Get-ScheduledTaskInfo -TaskName 'metagame-loop').NextRunTime")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())


def seed() -> None:
    """Register past screens (legacy: never live) from their config.json, so the floor counts the real history."""
    reg = registry(mark=False)
    n = 0
    for cfg in sorted((ROOT / "runs" / "screens").glob("*/config.json"), key=lambda p: p.stat().st_ctime):
        name = cfg.parent.name
        if name in reg:
            continue
        c = load(cfg, {})
        frm = (c.get("fork_from") or "").replace("\\", "/")
        reg[name] = {"legacy": True, "kind": "screen", "candidate": "", "run": f"runs/screens/{name}",
                     "start": "escape" if frm else "prevention", "from": frm or "fresh", "acked": "before #176",
                     "launched": stamp(cfg.stat().st_ctime), "sig": None, "seeds": {}}
        n += 1
    save_registry(reg)
    print(f"registered {n} past screens as legacy")


def selftest() -> None:
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    rec = tmp / "record.md"
    rec.write_text("Bands: J 0.4-0.5. Kill: looks 3/5/10.\n")
    chain = tmp / "c.sh"
    chain.write_text("run=runs/screens/x\n.venv/Scripts/python.exe -m rl.metagame --run x --lr 2e-4 \\\n"
                     "  --turnover-every 10 --reseed 7 --turnover-every 5 > x.log 2>&1\n")
    good = ROOT / "runs" / "_loop_selftest.sh"

    def args(**kw):
        d = dict(name="T1", candidate="C50", record=str(rec), kind="screen", start="escape", frm="S479",
                 components=[], evan_row=None, resume=False, replicate_of=None, looks=None, until=None, progress=None)
        d.update(kw)
        return argparse.Namespace(**d)

    def screen(i, frm="S479", start="escape", live=False, **kw):
        return {"kind": "screen", "from": frm, "start": start, "alive": live, "launched": f"2026-10-01 00:{i:02d}", **kw}

    cmd = [".venv/Scripts/python.exe", "-m", "rl.metagame", "--lr", "2e-4", "--reseed", "3"]
    fails = []

    def check(name, problems, expect):
        hit = any(expect in q for q in problems) if expect else not problems
        if not hit:
            fails.append(f"{name}: expected {expect or 'no problem'}, got {problems}")

    check("clean", launch_problems(args(), cmd, {}, 20, 0), None)
    check("candidate", launch_problems(args(candidate="x"), cmd, {}, 20, 0), "--candidate")
    check("record", launch_problems(args(record="nope.md"), cmd, {}, 20, 0), "--record")
    check("slots", launch_problems(args(), cmd, {}, 20, 3), "slots are busy")
    check("ram", launch_problems(args(), cmd, {}, 7, 0), "free RAM")
    check("pilot ram", launch_problems(args(kind="pilot"), cmd, {}, 10, 0), "free RAM")
    check("probe ram", launch_problems(args(kind="probe"), cmd, {}, 7, 3), None)
    check("stack", launch_problems(args(components=["a", "b", "c"]), cmd, {}, 20, 0), "unadopted")
    try:
        good.write_text(chain.read_text())
        check("repeat", launch_problems(args(), ["sh", "runs/_loop_selftest.sh"], {}, 20, 0), "--turnover-every")
    finally:
        good.unlink(missing_ok=True)
    three = {f"s{i}": screen(i) for i in range(3)}
    check("prevention floor", launch_problems(args(), cmd, three, 20, 0), "prevention start")
    check("prevention ok", launch_problems(args(start="prevention", frm="fresh"), cmd, three, 20, 0), None)
    check("evan exempt", launch_problems(args(evan_row=40), cmd, three, 20, 0), None)
    mixed = {f"s{i}": screen(i, start="prevention" if i == 0 else "escape") for i in range(5)}
    check("half of 10", launch_problems(args(), cmd, mixed, 20, 0), "at most half")
    two = {"a": screen(1, live=True), "b": screen(2, live=True), "c": screen(3, frm="fresh", start="prevention")}
    check("lineage", launch_problems(args(), cmd, two, 20, 0), "at most 2 of 3")
    reg = {"R1": {"kind": "pilot", "sig": signature(cmd), "seeds": seeds(cmd)}}
    check("duplicate", launch_problems(args(kind="pilot"), cmd, reg, 20, 0), "same configuration")
    check("same seed", launch_problems(args(kind="pilot", replicate_of="R1"), cmd, reg, 20, 0), "same seeds")
    cmd4 = cmd[:-1] + ["4"]
    check("replication", launch_problems(args(kind="pilot", replicate_of="R1"), cmd4, reg, 20, 0), None)
    check("registered", launch_problems(args(name="R1", kind="pilot"), cmd4, {"R1": {"kind": "pilot"}}, 20, 0),
          "already registered")
    print("\n".join(fails) if fails else f"loop selftest: all checks pass")
    sys.exit(1 if fails else 0)


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["seen"]:  # the interactive-session hook: fast and never fails
        try:
            if not os.environ.get(ROUND_ENV):
                LOOP.mkdir(parents=True, exist_ok=True)
                (LOOP / "seen").touch()
        except OSError:
            pass
        return
    if sys.stdout is not None:  # None under pythonw (the scheduled task)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the notes use −, ≥, ×
    cmd = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description="the unattended loop's supervisor and launcher")
    ap.add_argument("cmd", choices=["state", "launch", "stop", "ack", "pause", "resume", "disable", "enable", "round",
                                    "daemon", "rehash", "seed", "selftest", "install"])
    ap.add_argument("name", nargs="?", help="a run id (launch, stop, ack) or hours (pause)")
    ap.add_argument("ref", nargs="?", help="ack: the log entry, e.g. #181")
    ap.add_argument("--candidate", default="")
    ap.add_argument("--record", default="", help="the run's record (method §10), written before launch")
    ap.add_argument("--run", default="", help="the run's folder (default runs/screens/<name>)")
    ap.add_argument("--kind", choices=["screen", "pilot", "probe"], default="screen",
                    help="screen and pilot runs take a slot; probes run beside them")
    ap.add_argument("--start", choices=["escape", "prevention", "other"], default="escape", help="method §8")
    ap.add_argument("--from", dest="frm", default="fresh", help="the start state (a checkpoint path) or fresh")
    ap.add_argument("--components", default="", help="the unadopted components stacked on the recipe, comma-separated")
    ap.add_argument("--evan-row", type=int, default=None, help="Evan's idea (evan-requests row): exempt from the floor")
    ap.add_argument("--replicate-of", default=None, help="a registered run this one replicates with a new seed")
    ap.add_argument("--resume", action="store_true", help="continue a registered run that stopped")
    ap.add_argument("--looks", default="", help="absolute look iterations, comma-separated (default: method §9 offsets)")
    ap.add_argument("--look-wait", type=float, default=0,
                    help="minutes after a look is reached before it wakes a round (a watcher's readings take ~25)")
    ap.add_argument("--until", type=int, default=None)
    ap.add_argument("--progress", default="", help="the log.jsonl to read iterations from (default <run>/log.jsonl)")
    ap.add_argument("--dry", action="store_true", help="round: a dry round that launches and edits nothing")
    a = ap.parse_args(argv)
    a.components = [c for c in a.components.split(",") if c]
    if a.cmd == "launch":
        if not a.name:
            sys.exit("launch needs a run id")
        a.run = a.run or f"runs/screens/{a.name}"
        launch(a, cmd)
    elif a.cmd in ("stop", "ack"):
        if os.environ.get(DRY_ENV):
            sys.exit(f"dry run: {a.cmd} refused")
        reg = registry(mark=False)
        if a.name not in reg:
            sys.exit(f"{a.name} is not registered")
        if a.cmd == "stop":
            f = stop_file(reg[a.name])
            f.write_text("stop\n")
            print(f"{a.name}: wrote {f.relative_to(ROOT)}; it ends after its current iteration")
        else:
            if not a.ref:
                sys.exit('ack needs the log entry, e.g. ack C50-x "#181"')
            reg[a.name]["acked"] = a.ref
            save_registry(reg)
            print(f"{a.name}: logged in {a.ref}")
    elif a.cmd == "pause":
        until = stamp(time.time() + float(a.name) * 3600) if a.name else ""
        (LOOP / "PAUSE").write_text(until + "\n", encoding="utf-8")
        print(f"paused{' until ' + until if until else ' until `loop.py resume`'}")
    elif a.cmd == "resume":
        (LOOP / "PAUSE").unlink(missing_ok=True)
        print("resumed (rounds still wait out an active session of Evan's)")
    elif a.cmd == "disable":
        (LOOP / "DISABLED").write_text(stamp() + "\n")
        print("disabled: the supervisor exits at its next tick and no round starts")
    elif a.cmd == "enable":
        (LOOP / "DISABLED").unlink(missing_ok=True)
        print("enabled: the scheduled task starts the supervisor within 10 minutes")
    elif a.cmd == "round":
        sup = load(LOOP / "sup.json", {})
        r = sup.get("round")
        if r and alive(r.get("pid"), r.get("ctime")):
            sys.exit(f"round {r['ts']} is running")
        start_round(sup, "started by hand" + (" (dry run)" if a.dry else ""), dry=a.dry)
        save(LOOP / "sup.json", sup)
        print(f"round {sup['round']['ts']} started, pid {sup['round']['pid']}; result in runs/loop/rounds/")
    elif a.cmd == "daemon":
        daemon()
    elif a.cmd == "rehash":
        save(LOOP / "frozen.json", frozen_hashes())
        (LOOP / "ALERT").unlink(missing_ok=True)
        print("frozen hashes recorded; alert cleared")
    elif a.cmd == "seed":
        seed()
    elif a.cmd == "install":
        install()
    elif a.cmd == "selftest":
        selftest()
    else:
        print(write_state())


if __name__ == "__main__":
    main()
