"""Hidden-test grading inside a runner container. Same JSON shape and CLI as the skill's grade.py:

    python3 grade.py <code_dir> <tests_file> [-k EXPR] [--names] [--timeout SEC]

EXPR: a test-name substring ("test_p1_") or "not <substring>". The test command runs in the runner container
and leaves its report in the output tar; parsing happens here.
"""
import json, os, re, shlex, sys, xml.etree.ElementTree as ET
try: from sandbox import runner   # imported by the server
except ImportError: import runner   # run as a script: python3 grade.py ...

LANG_BY_EXT = {".py": "python", ".go": "go", ".java": "java", ".ts": "typescript", ".js": "javascript"}

JAVA_RUNNER = r'''
import java.lang.reflect.*;
public class Runner { public static void main(String[] a) throws Exception {
  Class<?> c=Class.forName(a[0]); String pat=a.length>1?a[1].toLowerCase():""; boolean neg=a.length>2;
  for (Method m: c.getDeclaredMethods()) { String n=m.getName();
    if(!n.startsWith("test")||m.getParameterCount()!=0) continue;
    if(!pat.isEmpty() && n.toLowerCase().contains(pat)==neg) continue;
    String err=null; try { m.setAccessible(true); m.invoke(Modifier.isStatic(m.getModifiers())?null:c.getDeclaredConstructor().newInstance()); }
    catch(InvocationTargetException e){ Throwable x=e.getCause(); err=x.getClass().getSimpleName()+": "+x.getMessage(); }
    System.out.println((err==null?"PASS ":"FAIL ")+n+(err==null?"":" | "+err.replace('\n',' ')));
  } } }
'''


def _s(b): return (b or b"").decode(errors="replace")


def lastline(text, marks=("E ", "FAIL", "panic:", "Error", "error")):
    ls = [l.strip() for l in text.splitlines() if l.strip()]
    hit = [l for l in ls if l.startswith(marks)]
    return (hit or ls or [""])[-1][:300]


def first_compile_error(text, rx):
    """The first compiler error line ("x.go:12:5: f.Foo undefined") says more than the trailing FAIL / "1 error"."""
    return next((l.strip()[:300] for l in text.splitlines() if re.search(rx, l)), None)


def _junit(xml_bytes, skip_skipped=False):
    res = {}
    for c in ET.fromstring(xml_bytes).iter("testcase"):
        if skip_skipped and c.find("skipped") is not None: continue
        f = c.find("failure") if c.find("failure") is not None else c.find("error")
        res[c.get("name")] = None if f is None else (f.get("message") or "failed")[:300]
    return res


def prune(src, lang, pat, neg):
    """Go/Java compile the whole test file, so tests for levels the candidate hasn't reached (methods that don't
    exist yet) would break the build for every level. Drop test functions the -k filter excludes.
    Relies on gofmt / conventional layout: a Go test ends at the next "}" in column 0, a Java test at "}" with its indent."""
    out, skip_until = [], None
    for line in src.splitlines(keepends=True):
        if skip_until is not None:
            if line.rstrip("\r\n") == skip_until: skip_until = None
            continue
        m = (re.match(r"func (Test\w*)\(", line) if lang == "go"
             else re.match(r"(\s*)(?:(?:public|private|protected)\s+)?static\s+void\s+(test\w*)\s*\(\s*\)", line))
        if m:
            name = m.group(1) if lang == "go" else m.group(2)
            if (pat.lower() in name.lower()) == neg:
                skip_until = "}" if lang == "go" else m.group(1) + "}"
                if line.rstrip().endswith("}") and line.count("{") == line.count("}"): skip_until = None  # one-liner
                continue
        out.append(line)
    return "".join(out)


def grade(files, tests, lang, k=None, limit=45, names=False):
    """files: {relpath: bytes} incl. the test files; tests: relpaths of test files. Returns the grade.py JSON dict."""
    q = shlex.quote
    neg = bool(k) and k.startswith("not "); pat = (k[4:] if neg else k) if k else None
    tq = " ".join(q(t) for t in tests)
    files = dict(files)
    if pat and lang in ("go", "java"):
        for t in tests: files[t] = prune(_s(files[t]) if isinstance(files[t], bytes) else files[t], lang, pat, neg)
    if lang == "python":
        sh = (f"python3 -m pytest -q -p no:cacheprovider {tq} --junitxml=/tmp/out/_r.xml"
              + (f" -k {q(k)}" if k else "") + " > /tmp/out/log 2>&1; echo $? > /tmp/out/rc\n")
    elif lang in ("typescript", "javascript"):
        flt = (f" {'--test-skip-pattern' if neg else '--test-name-pattern'} {q(re.escape(pat))}" if pat else "")
        sh = (f"node --disable-warning=ExperimentalWarning --test --test-reporter=junit "
              f"--test-reporter-destination=/tmp/out/_r.xml{flt} {tq} > /tmp/out/log 2>&1; echo $? > /tmp/out/rc\n")
    elif lang == "go":
        # One process per test: a panic in one test (e.g. a stub's panic("not implemented")) can't stop the others.
        # Compiled once; test2json keeps the `go test -json` event format the parser below reads.
        sel = f" | grep {'-viF' if neg else '-iF'} -- {q(pat)}" if pat else ""
        sh = ("[ -f go.mod ] || go mod init ilab >/dev/null 2>&1\n"
              "go test -list '.*' . > /tmp/out/list 2>&1; echo $? > /tmp/out/list.rc\n"
              "go test -c -o /tmp/t.test . 2>/tmp/out/err\n"
              f"for n in $(grep '^Test' /tmp/out/list{sel}); do go tool test2json -p ilab -t /tmp/t.test -test.v=test2json "
              "-test.run \"^$n\\$\" >> /tmp/out/log 2>>/tmp/out/err; done\necho 0 > /tmp/out/rc\n")
    elif lang == "java":
        files["Runner.java"] = JAVA_RUNNER; files["Expect.java"] = runner.JAVA_EXPECT
        arg = (f" {q(pat)}" + (" not" if neg else "")) if pat else ""
        sh = ("javac -d /tmp/_out $(find . -name '*.java') > /tmp/out/clog 2>&1; echo $? > /tmp/out/crc\n"
              "[ \"$(cat /tmp/out/crc)\" = 0 ] || exit 0\n: > /tmp/out/log\n")
        for t in tests:
            cls = runner.java_main(_s(files[t]) if isinstance(files[t], bytes) else files[t], t)
            sh += f"java -cp /tmp/_out Runner {q(cls)}{arg} >> /tmp/out/log 2>&1; echo $? >> /tmp/out/rc\n"
    else:
        return {"status": "could not be graded", "last_line": f"no runner for {lang}"}
    out, timed_out = runner.container(lang, files, sh, limit)
    if timed_out:
        return {"status": "did not finish", "limit_s": limit}
    log = _s(out.get("log")) + _s(out.get("err"))
    rcs = _s(out.get("rc")).split()
    rc = int(rcs[0]) if rcs and rcs[0].lstrip("-").isdigit() else None
    res = {}
    if lang == "python":
        if rc == 5: return {"status": "no tests selected", "k": k}
        if "_r.xml" not in out or rc in (2, 3, 4): return {"status": "could not be graded", "last_line": lastline(log or _s(out.get("_harness.log")))}
        res = _junit(out["_r.xml"])
    elif lang in ("typescript", "javascript"):
        if "_r.xml" not in out: return {"status": "could not be graded", "last_line": lastline(log or _s(out.get("_harness.log")))}
        res = _junit(out["_r.xml"], skip_skipped=True)
        if not res and rc != 0: return {"status": "could not be graded", "last_line": lastline(log)}
    elif lang == "go":
        lst = _s(out.get("list"))
        if _s(out.get("list.rc")).strip() != "0": return {"status": "could not be graded", "last_line": first_compile_error(lst, r"\.go:\d+:\d+: ") or lastline(lst or _s(out.get("_harness.log")))}
        tnames = [l for l in lst.split() if l.startswith("Test")]
        if pat: tnames = [n for n in tnames if (pat.lower() in n.lower()) != neg]
        outs = {}
        for l in _s(out.get("log")).splitlines():
            try: e = json.loads(l)
            except ValueError: continue
            n = e.get("Test")
            if not n or "/" in n: continue
            if e.get("Action") == "output" and n in tnames: outs.setdefault(n, []).append(e.get("Output", "").strip())
            if e.get("Action") in ("pass", "fail"):
                res[n] = None if e["Action"] == "pass" else next((o for o in outs.get(n, []) if o.startswith("panic:") or "_test.go:" in o), "failed")[:300]
        for n in tnames: res.setdefault(n, "did not run (earlier panic or crash)")
    elif lang == "java":
        if _s(out.get("crc")).strip() != "0": return {"status": "could not be graded", "last_line": first_compile_error(_s(out.get("clog")), r"\.java:\d+: error:") or lastline(_s(out.get("clog")) or _s(out.get("_harness.log")), ("error",))}
        for l in _s(out.get("log")).splitlines():
            m = re.match(r"(PASS|FAIL) (\S+)(?: \| (.*))?", l)
            if m: res[m.group(2)] = None if m.group(1) == "PASS" else (m.group(3) or "failed")[:300]
        if not res and any(r != "0" for r in rcs): return {"status": "could not be graded", "last_line": lastline(log)}
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
            files[os.path.relpath(p, d).replace(os.sep, "/")] = open(p, "rb").read()
    return files


if __name__ == "__main__":
    a = sys.argv[1:]; code, tests = a[0], a[1]
    k = a[a.index("-k") + 1] if "-k" in a else None
    lim = float(a[a.index("--timeout") + 1]) if "--timeout" in a else 90
    ext = os.path.splitext(tests)[1]; base = os.path.basename(tests)
    if ext not in LANG_BY_EXT:
        print(json.dumps({"status": "could not be graded", "last_line": f"no runner for {ext} files"})); sys.exit()
    files = read_tree(code); files[base] = open(tests, "rb").read()
    try:
        print(json.dumps(grade(files, [base], LANG_BY_EXT[ext], k, lim, "--names" in a)))
    except runner.DockerError as e:
        print(json.dumps({"status": "could not be graded", "last_line": str(e)}))
