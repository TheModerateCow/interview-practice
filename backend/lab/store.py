"""Set storage under data/sets/<name>/: manifest, session.json (clock, events, reveals) and the work folder."""
import json, os, re, threading, time

from sandbox import grade

DATA = os.environ.get("ILAB_DATA", "/data")
SETS, EXPORTS = os.path.join(DATA, "sets"), os.path.join(DATA, "exports")
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_locks, _busy = {}, {}   # per set: session read-modify-write lock, and one run/submit at a time
_glock = threading.Lock()


class HTTPError(Exception):
    def __init__(self, code, msg): super().__init__(msg); self.code = code


def lock(n, kind=_locks):
    with _glock: return kind.setdefault(n, threading.Lock())


def sdir(n):
    if not NAME_RE.fullmatch(n or "") or not os.path.isfile(os.path.join(SETS, n, "manifest.json")):
        raise HTTPError(404, f"no set named {n!r}")
    return os.path.join(SETS, n)


def jload(p, default=None):
    try: return json.load(open(p))
    except FileNotFoundError: return default


def jsave(p, obj):
    t = p + ".tmp"
    with open(t, "w") as f: json.dump(obj, f, indent=1)
    os.replace(t, p)


def manifest(n): return jload(os.path.join(sdir(n), "manifest.json"))
def session(n): return jload(os.path.join(sdir(n), "session.json"))


def work_path(n, rel):
    work = os.path.realpath(os.path.join(sdir(n), "work"))
    if not rel or "\x00" in rel or "\\" in rel or rel.startswith("/"): raise HTTPError(400, "bad path")
    if rel.split("/")[0] == ".hidden": raise HTTPError(400, "bad path")
    p = os.path.realpath(os.path.join(work, rel))
    if not p.startswith(work + os.sep): raise HTTPError(400, "path escapes the work folder")
    return p


def work_files(n):
    return grade.read_tree(os.path.join(sdir(n), "work"))


def deadline(s): return s["start"] + s["minutes"] * 60
def cutoff(s): return s.get("ended") or deadline(s)          # ended <= deadline from this round on
def late(s, t): return t > cutoff(s)                          # did an action that started at t come after the close?
def minute(s, t): return round((t - s["start"]) / 60, 1)


def clock(s):
    """(minutes used now, minutes left, expired); left/expired freeze at the close."""
    now = time.time(); stop = min(now, s["ended"]) if s.get("ended") else now
    left = s["minutes"] - (stop - s["start"]) / 60
    return (now - s["start"]) / 60, max(left, 0), left <= 0


def closed(s): return bool(s.get("ended")) or clock(s)[2]    # the "ended" status only


def log(s, text, t=None):
    t = t or time.time()
    s["events"].append([minute(s, t), text + (" (after time)" if late(s, t) else "")])


def mutate(n, fn):
    """Read-modify-write session.json under the set's lock. fn(session, manifest) -> result."""
    with lock(n):
        s = session(n)
        if not s or not s.get("start"): raise HTTPError(409, "not started")
        r = fn(s, manifest(n))
        jsave(os.path.join(sdir(n), "session.json"), s)
        return r


def reveal(s, entry, reason):
    s["revealed"].append(entry["file"])
    if entry.get("unlocks") and entry["unlocks"] not in s["unlocked"]: s["unlocked"].append(entry["unlocks"])
    log(s, f"revealed {os.path.basename(entry['file'])} ({reason})")


def locked(s, m): return [r for r in m.get("reveal", []) if r["file"] not in s["revealed"]]


def time_reveals(s, m):
    if s.get("ended"): return
    left = clock(s)[1]
    for r in locked(s, m):
        if r.get("or_minutes_left") is not None and left <= r["or_minutes_left"]:
            reveal(s, r, f"{r['or_minutes_left']:g} min left")


def ready_info(n):
    m, s = manifest(n), session(n)
    st = "ready" if not s or not s.get("start") else ("ended" if closed(s) else "running")
    return {k: m.get(k) for k in ("name", "title", "company", "role", "round", "language", "difficulty", "minutes", "rules")} | {"status": st}


def state(n):
    mutate(n, time_reveals)
    d, m, s = sdir(n), manifest(n), session(n)
    used, left, expired = clock(s)
    results = jload(os.path.join(d, "results.json"), {})
    parts = []
    for f in s["revealed"]:
        p = os.path.join(d, f)
        parts.append({"file": os.path.basename(f), "md": open(p).read() if os.path.isfile(p) else ""})
    return ready_info(n) | {
        "start": s["start"], "now": time.time(), "left_s": round(left * 60, 1), "expired": expired, "ended": bool(s.get("ended")),
        "problem": open(os.path.join(d, "problem.md")).read(), "parts": parts,
        "unlocked": s["unlocked"], "has_next": bool(locked(s, m)),
        "has_submit": bool(m.get("hidden_tests")), "has_mytests": bool(m.get("your_tests")), "has_examples": bool(m.get("examples")),
        "run_entry": m.get("run_entry"), "testcases_count": len(m.get("testcases", [])),
        "files": sorted(work_files(n)),
        "results": {t: r for t, r in results.items() if t != "final"},
        "final": results.get("final"), "events": s["events"]}


def require_started(n):
    s = session(n)
    if not s or not s.get("start"): raise HTTPError(409, "not started")
    return s
