"""What a candidate does in a round: Start, Run, Submit, My tests, Next part, End, Export, Delete."""
import fnmatch, io, os, shutil, time, zipfile

from sandbox import grade, lsp, runner
from lab.store import (DATA, EXPORTS, HTTPError, _busy, closed, deadline, jload, jsave, late, lock, locked, log, manifest,
                       minute, mutate, public, ready_info, require_started, reveal, sdir, session, state, work_files, work_path)

EXT_LANG = {".py": "python", ".go": "go", ".java": "java", ".ts": "typescript", ".js": "javascript", ".mjs": "javascript",
            ".c": "c", ".cpp": "cpp", ".cc": "cpp"}
GRACE_S = 5   # ponytail: autosave lag + one request; raise if real rounds show false "after time" on the final grade


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
    stdins = [stdin] + [t.get("stdin", "") for t in tcs]   # always one run with the stdin box, so Run always shows stdout
    lk = busy(n)
    try: r = runner.run(lang, files, f, stdins)
    finally: lk.release()
    if r["compile"] and not r["compile"]["ok"]:
        if r["compile"]["log"].startswith("Nothing to run") and not m.get("your_tests"):   # no My tests button: don't point at it
            r["compile"]["log"] = r["compile"]["log"].split(" Test it with")[0] + " Check it with Submit.\n"
        out = {"compile": r["compile"], "stdin_case": None, "testcases": [], "memory_kb": None, "verdict": "Compile Error"}
    else:
        cases = r["cases"]
        sc = cases[0]
        tc = [c | {"expected": t["expected"], "stdin": t.get("stdin", ""),
                   "pass": c["verdict"] == "Accepted" and norm(c["stdout"]) == norm(t["expected"])}
              for c, t in zip(cases[1:], tcs)]
        # an empty stdin box next to testcases is only there to show stdout: the testcases decide the verdict
        judged = cases[1:] if tcs and not stdin else cases
        bad = next((c["verdict"] for c in judged if c["verdict"] != "Accepted"), None)
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
    """Newest mtime under final/ (the code at the close) if it exists, else work/ (0 if empty)."""
    d = os.path.join(sdir(n), "final")
    if not os.path.isdir(d): d = os.path.join(sdir(n), "work")
    return max((os.path.getmtime(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs), default=0)


def end(n):
    """The one close: idempotent; waits for an in-flight Run/Submit; grades the unlocked tags once."""
    require_started(n); m = manifest(n)
    lk = lock(n, _busy)
    if not lk.acquire(timeout=m.get("grade_timeout_s", 45) + 30): raise HTTPError(409, "a Run/Submit is still running")
    try:
        def close(s, _):
            if s.get("ended"): return False
            now = time.time()
            if now > deadline(s): s["ended"] = deadline(s); log(s, "time up", s["ended"])
            else: s["ended"] = now; log(s, "end", now)
            return True
        if mutate(n, close):   # this call closed the round: snapshot the code once (copytree keeps mtimes)
            shutil.copytree(os.path.join(sdir(n), "work"), os.path.join(sdir(n), "final"), dirs_exist_ok=True)
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
        fd = os.path.join(d, "final")   # the code at the close; absent for rounds closed before this existed
        for rel, data in sorted(grade.read_tree(fd).items() if os.path.isdir(fd) else []): z.writestr("final/" + rel, data)
    data = b.getvalue()
    os.makedirs(EXPORTS, exist_ok=True)
    with open(os.path.join(EXPORTS, f"{n}-{time.strftime('%Y%m%d-%H%M%S')}.zip"), "wb") as f: f.write(data)
    return data


def delete(n):
    """Soft delete: move the set folder to data/deleted/<name>-<stamp>/. Nothing is erased; exports/ is untouched."""
    wait = lock(n, _busy)   # a Run/Submit/grade holds this; refuse rather than move the folder under it
    if not wait.acquire(blocking=False): raise HTTPError(409, "This round is in progress. End it first, then delete it.")
    try:
        with lock(n):
            i = ready_info(n)
            if i["status"] == "running": raise HTTPError(409, "This round is in progress. End it first, then delete it.")
            dest = os.path.join(DATA, "deleted", f"{n}-{time.strftime('%Y%m%d-%H%M%S')}")
            while os.path.exists(dest): dest += "-x"
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            os.replace(sdir(n), dest)
    finally: wait.release()
    lsp.stop(n)
    return {"name": n, "title": i["title"], "moved_to": dest}
