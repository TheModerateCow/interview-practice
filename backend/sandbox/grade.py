"""Hidden-test grading inside a runner container. Same JSON shape and CLI as the skill's grade.py:

    python3 grade.py <code_dir> <tests_file> [-k EXPR] [--names] [--timeout SEC]

EXPR: a test-name substring ("test_p1_") or "not <substring>". The test command runs in the runner container
and leaves its report in the output tar; parsing happens here.
"""
import json, os, sys
from pathlib import Path
try: from sandbox import runner; from sandbox.toolchains import BY_EXT, TOOLCHAINS, _s   # imported by the server
except ImportError: import runner; from toolchains import BY_EXT, TOOLCHAINS, _s   # run as a script

LANG_BY_EXT = {e: t.name for e, t in BY_EXT.items() if t.grades}


def prune(src, lang, pat, neg):
    """Go/Java compile the whole test file, so tests for levels the candidate hasn't reached (methods that don't
    exist yet) would break the build for every level. Drop test functions the -k filter excludes.
    Where a test starts and ends is the toolchain's test_start (gofmt / conventional layout)."""
    start = TOOLCHAINS[lang].test_start
    out, skip_until = [], None
    for line in src.splitlines(keepends=True):
        if skip_until is not None:
            if line.rstrip("\r\n") == skip_until: skip_until = None
            continue
        hit = start(line)
        if hit:
            name, end = hit
            if (pat.lower() in name.lower()) == neg:
                skip_until = end
                if line.rstrip().endswith("}") and line.count("{") == line.count("}"): skip_until = None  # one-liner
                continue
        out.append(line)
    return "".join(out)


def grade(files, tests, lang, k=None, limit=45, names=False):
    """files: {relpath: bytes} incl. the test files; tests: relpaths of test files. Returns the grade.py JSON dict."""
    tc = TOOLCHAINS.get(lang)
    if not tc or not tc.grades: return {"status": "could not be graded", "last_line": f"no runner for {lang}"}
    neg = bool(k) and k.startswith("not "); pat = (k[4:] if neg else k) if k else None
    files = dict(files)
    if pat and tc.test_start:
        for t in tests: files[t] = prune(_s(files[t]), lang, pat, neg)
    sh, files = tc.grade_sh(files, tests, k, pat, neg)
    out, timed_out = runner.container(lang, files, sh, limit)
    if timed_out:
        return {"status": "did not finish", "limit_s": limit}
    res, status = tc.parse(out, k, pat, neg)
    if status: return status
    if not res: return {"status": "no tests selected", "k": k}
    bad = [n for n, e in res.items() if e is not None]
    o = {"status": "graded", "passed": len(res) - len(bad), "total": len(res)}
    if bad: o["last_error"] = res[bad[-1]]
    if names: o["failed"] = bad
    return o


def read_tree(d, skip=(".git", "node_modules", "__pycache__", ".pytest_cache")):
    files = {}
    for root, dirs, fs in os.walk(d):
        dirs[:] = [x for x in dirs if x not in skip]
        for f in fs:
            p = os.path.join(root, f)
            if os.path.islink(p): continue
            files[os.path.relpath(p, d).replace(os.sep, "/")] = Path(p).read_bytes()
    return files


if __name__ == "__main__":
    a = sys.argv[1:]; code, tests = a[0], a[1]
    k = a[a.index("-k") + 1] if "-k" in a else None
    lim = float(a[a.index("--timeout") + 1]) if "--timeout" in a else 90
    ext = os.path.splitext(tests)[1]; base = os.path.basename(tests)
    if ext not in LANG_BY_EXT:
        print(json.dumps({"status": "could not be graded", "last_line": f"no runner for {ext} files"})); sys.exit()
    files = read_tree(code); files[base] = Path(tests).read_bytes()
    try:
        print(json.dumps(grade(files, [base], LANG_BY_EXT[ext], k, lim, "--names" in a)))
    except runner.DockerError as e:
        print(json.dumps({"status": "could not be graded", "last_line": str(e)}))
