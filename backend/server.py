"""Interview Lab API. Stdlib only. Contract: API.md. Data layout: FORMAT.md."""
import fnmatch, io, json, os, re, shutil, sys, threading, time, traceback, uuid, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

import grade, pack, runner

DATA = os.environ.get("ILAB_DATA", "/data")
SETS, EXPORTS = os.path.join(DATA, "sets"), os.path.join(DATA, "exports")
HOSTS = {"127.0.0.1:8765", "localhost:8765"}
ORIGINS = {"http://" + h for h in HOSTS}
MAX_ZIP, MAX_FILES, MAX_UNPACKED, MAX_FILE = 50 << 20, 2000, 50 << 20, 1 << 20
DROP = ("reference/", "mutants.json", "bugs.json")
EXT_LANG = {".py": "python", ".go": "go", ".java": "java", ".ts": "typescript", ".js": "javascript", ".mjs": "javascript",
            ".c": "c", ".cpp": "cpp", ".cc": "cpp"}
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
IMG_STATE = {}           # image -> ready | pulling | missing
_locks, _busy = {}, {}   # per set: session read-modify-write lock, and one run/submit at a time
_glock = threading.Lock()


class HTTPError(Exception):
    def __init__(self, code, msg): super().__init__(msg); self.code = code


def lock(n, kind=_locks):
    with _glock: return kind.setdefault(n, threading.Lock())


# ---------------------------------------------------------------- set storage

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


GRACE_S = 5   # ponytail: autosave lag + one request; raise if real rounds show false "after time" on the final grade


def deadline(s): return s["start"] + s["minutes"] * 60
def cutoff(s): return s.get("ended") or deadline(s)          # ended <= deadline from this round on
def late(s, t): return t > cutoff(s)                          # did an action that started at t come after the close?
def minute(s, t): return round((t - s["start"]) / 60, 1)


def clock(s):
    """(minutes used now, minutes left, expired); left/expired freeze at the close."""
    now = time.time(); stop = min(now, s["ended"]) if s.get("ended") else now
    left = s["minutes"] - (stop - s["start"]) / 60
    return (now - s["start"]) / 60, max(left, 0), left <= 0


def closed(s): return bool(s.get("ended")) or clock(s)[2]    # failed names and the "ended" status only


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


def public(res, show_names):
    return {k: v for k, v in res.items() if k != "failed" or show_names}


def state(n):
    mutate(n, time_reveals)
    d, m, s = sdir(n), manifest(n), session(n)
    used, left, expired = clock(s)
    names = closed(s)
    results = jload(os.path.join(d, "results.json"), {})
    parts = []
    for f in s["revealed"]:
        p = os.path.join(d, f)
        parts.append({"file": os.path.basename(f), "md": open(p).read() if os.path.isfile(p) else ""})
    return ready_info(n) | {
        "start": s["start"], "now": time.time(), "left_s": round(left * 60, 1), "expired": expired, "ended": bool(s.get("ended")),
        "problem": open(os.path.join(d, "problem.md")).read(), "parts": parts,
        "unlocked": s["unlocked"], "has_next": bool(locked(s, m)),
        "has_submit": bool(m.get("hidden_tests")), "has_mytests": bool(m.get("your_tests")),
        "run_entry": m.get("run_entry"), "testcases_count": len(m.get("testcases", [])),
        "files": sorted(work_files(n)),
        "results": {t: public(r, names) for t, r in results.items() if t != "final"},
        "final": results.get("final"), "events": s["events"]}


# ---------------------------------------------------------------- import

def do_import(body):
    if len(body) > MAX_ZIP: raise HTTPError(400, "zip is larger than 50 MB")
    try: z = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile: raise HTTPError(400, "not a zip file")
    infos = z.infolist()
    if len(infos) > MAX_FILES: raise HTTPError(400, f"zip has more than {MAX_FILES} entries")
    if sum(i.file_size for i in infos) > MAX_UNPACKED: raise HTTPError(400, "zip unpacks to more than 50 MB")
    for i in infos:
        nm = i.filename
        parts = nm.split("/")
        if nm.startswith("/") or "\\" in nm or ".." in parts or re.match(r"^[A-Za-z]:", nm) or "\x00" in nm:
            raise HTTPError(400, f"unsafe path in zip: {nm!r}")
        if (i.external_attr >> 16) & 0o170000 == 0o120000: raise HTTPError(400, f"symlink in zip: {nm!r}")
    names = [i.filename for i in infos if not i.is_dir()]
    prefix = ""
    if "manifest.json" not in names:
        tops = {x.split("/")[0] for x in names}
        if len(tops) == 1 and f"{next(iter(tops))}/manifest.json" in names: prefix = next(iter(tops)) + "/"
        else: raise HTTPError(400, "manifest.json not found at the top of the zip")
    keep = {}
    for i in infos:
        if i.is_dir(): continue
        rel = i.filename[len(prefix):]
        if rel.startswith(DROP) or rel in DROP: continue   # reference/, mutants.json, bugs.json are deleted
        if rel in ("manifest.json", "problem.md") or rel.startswith(("starter/", ".hidden/")): keep[rel] = i
    try: m = json.loads(z.read(keep["manifest.json"]))
    except (ValueError, KeyError): raise HTTPError(400, "manifest.json is not valid JSON")
    errs = pack.validate(m, lambda p: p in keep or (p.endswith("/") and any(k.startswith(p) for k in keep)))
    if errs: raise HTTPError(400, "invalid set: " + "; ".join(errs))
    n = m["name"]
    dest = os.path.join(SETS, n)
    with lock(n):
        s = jload(os.path.join(dest, "session.json"))
        if s and s.get("start"):
            raise HTTPError(409, f"set {n!r} was already started. Change \"name\" in manifest.json to import it again.")
        tmp = os.path.join(SETS, f".import-{uuid.uuid4().hex}")
        try:
            total = 0
            for rel, i in keep.items():
                p = os.path.realpath(os.path.join(tmp, rel))
                if not p.startswith(os.path.realpath(tmp) + os.sep): raise HTTPError(400, f"unsafe path in zip: {rel!r}")
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with z.open(i) as src, open(p, "wb") as out:
                    while chunk := src.read(1 << 16):
                        total += len(chunk)
                        if total > MAX_UNPACKED: raise HTTPError(400, "zip unpacks to more than 50 MB")
                        out.write(chunk)
            shutil.copytree(os.path.join(tmp, "starter"), os.path.join(tmp, "work"))
            shutil.rmtree(dest, ignore_errors=True)
            os.replace(tmp, dest)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return {"name": n}


# ---------------------------------------------------------------- actions

def start(n):
    with lock(n):
        m, p = manifest(n), os.path.join(sdir(n), "session.json")
        s = jload(p)
        if not s or not s.get("start"):
            unlocks = {r.get("unlocks") for r in m.get("reveal", [])}
            s = {"start": time.time(), "minutes": m["minutes"], "hints": [], "events": [], "ended": None,
                 "unlocked": [t for t in m.get("tags", ["test_"]) if t not in unlocks], "revealed": []}
            log(s, "start")
            jsave(p, s)
    return state(n)


def busy(n):
    lk = lock(n, _busy)
    if not lk.acquire(blocking=False): raise HTTPError(409, "another Run/Submit is still running for this set")
    return lk


def require_started(n):
    s = session(n)
    if not s or not s.get("start"): raise HTTPError(409, "not started")
    return s


def norm(t): return "\n".join(l.rstrip() for l in t.rstrip().splitlines())


def run(n, body):
    t0 = time.time()
    require_started(n)
    m, f, stdin = manifest(n), body.get("file") or "", body.get("stdin") or ""
    lang = EXT_LANG.get(os.path.splitext(f)[1])
    if not lang: raise HTTPError(400, f"can't run {f or 'this file'}: supported .py .go .java .ts .js .c .cpp")
    work_path(n, f)
    files = work_files(n)
    if f not in files: raise HTTPError(404, f"{f} not found")
    tcs = m.get("testcases", []) if f == m.get("run_entry") else []
    with_stdin = bool(stdin) or not tcs
    stdins = ([stdin] if with_stdin else []) + [t.get("stdin", "") for t in tcs]
    lk = busy(n)
    try: r = runner.run(lang, files, f, stdins)
    finally: lk.release()
    if r["compile"] and not r["compile"]["ok"]:
        out = {"compile": r["compile"], "stdin_case": None, "testcases": [], "memory_kb": None, "verdict": "Compile Error"}
    else:
        cases = r["cases"]
        sc = cases[0] if with_stdin else None
        tc = [c | {"expected": t["expected"], "stdin": t.get("stdin", ""),
                   "pass": c["verdict"] == "Accepted" and norm(c["stdout"]) == norm(t["expected"])}
              for c, t in zip(cases[1 if with_stdin else 0:], tcs)]
        bad = next((c["verdict"] for c in cases if c["verdict"] != "Accepted"), None)
        verdict = bad or ("Wrong Answer" if any(not c["pass"] for c in tc) else "Accepted")
        out = {"compile": r["compile"], "stdin_case": sc, "testcases": tc, "memory_kb": r["memory_kb"], "verdict": verdict}
    mutate(n, lambda s, _: log(s, f"run {f}: {out['verdict']}" + (f", {sum(c['pass'] for c in out['testcases'])}/{len(tcs)} cases" if tcs else ""), t0))
    return out


def grade_tags(n, tags):
    m, d = manifest(n), sdir(n)
    ht = m["hidden_tests"]; base = os.path.basename(ht)
    files = work_files(n); files[base] = open(os.path.join(d, ht), "rb").read()
    lang = m["language"]; lim = m.get("grade_timeout_s", 45)
    return {t: grade.grade(files, [base], lang, t, lim, names=True) for t in tags}


def stamp(s, res, t): return res | {"at": minute(s, t), "after_time": late(s, t)}


def submit(n):
    t0 = time.time()
    s, m = require_started(n), manifest(n)
    if not m.get("hidden_tests"): raise HTTPError(400, "this set has no hidden tests (Run only)")
    lk = busy(n)
    try:
        tags = [t for t in m.get("tags", ["test_"]) if t in s["unlocked"]]
        res = grade_tags(n, tags)
    finally: lk.release()

    def apply(s, m):
        rp = os.path.join(sdir(n), "results.json")
        allr = jload(rp, {})
        for t, r in res.items(): allr[t] = stamp(s, r, t0)
        jsave(rp, allr)
        log(s, "submit: " + ", ".join(f"{t} {r['passed']}/{r['total']}" if r["status"] == "graded" else f"{t} {r['status']}" for t, r in res.items()), t0)
        new = []
        if not s.get("ended"):
            for t, r in res.items():
                if r["status"] == "graded" and r["total"] and r["passed"] == r["total"]:
                    for e in locked(s, m):
                        if e.get("after_tag") == t: reveal(s, e, f"{t} passed"); new.append(os.path.basename(e["file"]))
        return allr, new, closed(s)
    allr, new, names = mutate(n, apply)
    return {"results": {t: public(allr[t], names) for t in res}, "revealed": new, "state": state(n)}


def mytests(n):
    t0 = time.time()
    s, m = require_started(n), manifest(n)
    pat = m.get("your_tests")
    if not pat: raise HTTPError(400, "this set has no your_tests pattern")
    files = work_files(n)
    tests = sorted(f for f in files if fnmatch.fnmatch(f, pat) or fnmatch.fnmatch(os.path.basename(f), pat))
    if not tests: r = {"status": "no tests selected", "k": None, "last_line": f"no files match {pat}"}
    else:
        lk = busy(n)
        try: r = grade.grade(files, tests, m["language"], None, m.get("grade_timeout_s", 45), names=True)
        finally: lk.release()
    mutate(n, lambda s, _: log(s, "my tests: " + (f"{r['passed']}/{r['total']}" if r["status"] == "graded" else r["status"]), t0))
    return r


def next_part(n):
    def f(s, m):
        lk = locked(s, m)
        if not lk: raise HTTPError(409, "no locked part left")
        reveal(s, lk[0], "asked to move on")
    mutate(n, f)
    return state(n)


def last_edit(n):
    """Newest mtime under work/ (0 if empty)."""
    return max((os.path.getmtime(os.path.join(r, f)) for r, _, fs in os.walk(os.path.join(sdir(n), "work")) for f in fs), default=0)


def end(n):
    """The one close: idempotent; waits for an in-flight Run/Submit; grades the unlocked tags once."""
    require_started(n); m = manifest(n)
    lk = lock(n, _busy)
    if not lk.acquire(timeout=m.get("grade_timeout_s", 45) + 30): raise HTTPError(409, "a Run/Submit is still running")
    try:
        def close(s, _):
            if s.get("ended"): return
            now = time.time()
            if now > deadline(s): s["ended"] = deadline(s); log(s, "time up", s["ended"])
            else: s["ended"] = now; log(s, "end", now)
        mutate(n, close)
        s = session(n)
        rp = os.path.join(sdir(n), "results.json")
        if m.get("hidden_tests") and "final" not in jload(rp, {}):
            res = grade_tags(n, [t for t in m.get("tags", ["test_"]) if t in s["unlocked"]])
            after = last_edit(n) > deadline(s) + GRACE_S
            def apply(s, _):
                allr = jload(rp, {})
                allr["final"] = {t: r | {"at": minute(s, s["ended"]), "after_time": after} for t, r in res.items()}; jsave(rp, allr)
            mutate(n, apply)
    finally: lk.release()
    return state(n)


def export(n):
    require_started(n)
    d = sdir(n); b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, data in sorted(work_files(n).items()): z.writestr("submission/" + rel, data)
        for f in ("session.json", "results.json", "manifest.json"):
            p = os.path.join(d, f)
            z.writestr(f, open(p, "rb").read() if os.path.isfile(p) else b"{}")
    data = b.getvalue()
    os.makedirs(EXPORTS, exist_ok=True)
    with open(os.path.join(EXPORTS, f"{n}-{time.strftime('%Y%m%d-%H%M%S')}.zip"), "wb") as f: f.write(data)
    return data


def health():
    try:
        runner.api("GET", "/version", timeout=5); ok, err = True, None
    except runner.DockerError as e: ok, err = False, str(e)
    return {"ok": True, "docker": ok, "error": err,
            "images": {lang: IMG_STATE.get(img, "missing") for lang, img in runner.IMAGES.items() if lang not in ("cpp", "typescript")}}


def image_keeper():
    """Sweep leftover runners, then pull any missing runner image. Retries while Docker is unreachable."""
    swept = False
    while True:
        try:
            if not swept: runner.sweep(); swept = True
            for img in dict.fromkeys(runner.IMAGES.values()):
                if IMG_STATE.get(img) == "ready": continue
                if runner.image_ready(img): IMG_STATE[img] = "ready"; continue
                if img.startswith("ilab-"): IMG_STATE[img] = "missing"; continue   # built by compose / install.sh
                IMG_STATE[img] = "pulling"; runner.pull(img)
                IMG_STATE[img] = "ready" if runner.image_ready(img) else "missing"
        except Exception as e:  # never let the keeper thread die
            print("image keeper:", e, file=sys.stderr)
            for img, st in IMG_STATE.items():
                if st == "pulling": IMG_STATE[img] = "missing"
        time.sleep(30 if all(v == "ready" for v in IMG_STATE.values()) and IMG_STATE else 10)


# ---------------------------------------------------------------- HTTP

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *a): sys.stderr.write("%s %s\n" % (self.command, self.path))

    def send(self, code, body, ctype="application/json", extra=()):
        data = body if isinstance(body, bytes) else (json.dumps(body).encode() if ctype == "application/json" else body.encode())
        self.send_response(code)
        self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in extra: self.send_header(k, v)
        self.end_headers(); self.wfile.write(data)

    def body(self, limit):
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit: raise HTTPError(413, "request too large")
        return self.rfile.read(n) if n else b""

    def handle_any(self):
        try:
            if self.headers.get("Host") not in HOSTS: raise HTTPError(403, "forbidden host")
            if self.headers.get("X-ILab") != "1": raise HTTPError(403, "missing X-ILab header")
            o = self.headers.get("Origin")
            if o is not None and o not in ORIGINS: raise HTTPError(403, "forbidden origin")
            path = urlsplit(self.path).path
            if not path.startswith("/api/"): raise HTTPError(404, "not found")
            seg = path[len("/api/"):].split("/")
            M = self.command
            if seg == ["health"] and M == "GET": return self.send(200, health())
            if seg == ["import"] and M == "POST": return self.send(200, do_import(self.body(MAX_ZIP)))
            if seg == ["sets"] and M == "GET":
                os.makedirs(SETS, exist_ok=True)
                out = []
                for n in sorted(os.listdir(SETS)):
                    if NAME_RE.fullmatch(n) and os.path.isfile(os.path.join(SETS, n, "manifest.json")):
                        i = ready_info(n); out.append({k: i[k] for k in ("name", "title", "language", "round", "status")})
                return self.send(200, {"sets": out})
            if len(seg) < 2 or seg[0] != "sets": raise HTTPError(404, "not found")
            n = unquote(seg[1]); sdir(n)
            act = seg[2] if len(seg) > 2 else ""
            if act == "" and M == "GET": return self.send(200, ready_info(n))
            if act == "start" and M == "POST": return self.send(200, start(n))
            if act == "state" and M == "GET": require_started(n); return self.send(200, state(n))
            if act == "files":
                require_started(n)
                p = work_path(n, unquote("/".join(seg[3:])))
                if M == "GET":
                    if not os.path.isfile(p): raise HTTPError(404, "no such file")
                    return self.send(200, open(p, "rb").read(), "text/plain; charset=utf-8")
                if M == "PUT":
                    data = self.body(MAX_FILE)
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, "wb") as f: f.write(data)
                    return self.send(200, {"ok": True})
            if act == "run" and M == "POST": return self.send(200, run(n, json.loads(self.body(MAX_FILE) or b"{}")))
            if act == "mytests" and M == "POST": return self.send(200, mytests(n))
            if act == "submit" and M == "POST": return self.send(200, submit(n))
            if act == "next" and M == "POST": return self.send(200, next_part(n))
            if act == "end" and M == "POST": return self.send(200, end(n))
            if act == "export" and M == "GET":
                return self.send(200, export(n), "application/zip", [("Content-Disposition", 'attachment; filename="export.zip"')])
            raise HTTPError(404, "not found")
        except HTTPError as e:
            self.send(e.code, {"error": str(e)})
        except runner.DockerError as e:
            self.send(503, {"error": str(e)})
        except (ValueError, KeyError) as e:
            traceback.print_exc(); self.send(400, {"error": f"bad request: {e}"})
        except Exception as e:
            traceback.print_exc(); self.send(500, {"error": f"internal error: {e}"})

    do_GET = do_POST = do_PUT = do_DELETE = handle_any


if __name__ == "__main__":
    os.makedirs(SETS, exist_ok=True); os.makedirs(EXPORTS, exist_ok=True)
    threading.Thread(target=image_keeper, daemon=True).start()
    print("Interview Lab backend on :8000", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
