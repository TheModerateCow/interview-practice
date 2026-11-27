#!/usr/bin/env python3
"""Acceptance tests against the isolated test stack (tests/stack.sh up: http://127.0.0.1:8766). stdlib only."""
import glob, http.client, io, json, os, random, re, shutil, socket, subprocess, sys, time, traceback, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("ILAB_TEST_DATA", os.path.join(ROOT, "tests/out/stack-data"))   # the test stack's /data
ZIPS = os.path.join(ROOT, "tests/sets/_zips")
HOST, PORT = "127.0.0.1", int(os.environ.get("ILAB_TEST_PORT", "8766"))
fails = 0


def check(name, ok, detail=""):
    global fails
    if not ok: fails += 1
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -- {str(detail)[:300]}"), flush=True)


def skip(name, why): print(f"SKIP {name}: {why}", flush=True)


def req(method, path, body=None, headers=None, host=None, hdr=True, timeout=400):
    h = {"X-ILab": "1"} if hdr else {}
    h.update(headers or {})
    if host: h["Host"] = host
    if isinstance(body, (dict, list)): body = json.dumps(body).encode()
    if isinstance(body, str): body = body.encode()
    c = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    try:
        c.request(method, path, body, h); r = c.getresponse(); return r.status, r.read()
    finally: c.close()


def jreq(*a, **k):
    s, b = req(*a, **k)
    try: return s, json.loads(b)
    except ValueError: return s, {"_raw": b[:200].decode(errors="replace")}


def mkzip(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for k, v in files.items(): z.writestr(k, v)
    return b.getvalue()


def uniq(p): return f"{p}-{random.randrange(16**6):06x}"


def manifest(name, lang, **kw):
    m = {"format": "interview-set/1", "name": name, "title": "T " + name, "round": "tdd", "language": lang,
         "difficulty": "medium", "minutes": 30}
    m.update(kw); return m


def imp(zbytes):
    s, j = jreq("POST", "/api/import", zbytes)
    return s, j


def clock_set(label, minutes, slow=False):
    n = uniq(label); ht = ".hidden/test_hidden.py"
    t = "import time\n\ndef test_ok():\n    time.sleep(4)\n    assert True\n" if slow else "def test_ok():\n    assert True\n"
    z = {"manifest.json": json.dumps(manifest(n, "python", minutes=minutes, hidden_tests=ht)), "problem.md": "x",
         "starter/main.py": "print('hi')\n", ht: t}
    s, j = imp(mkzip(z)); check(f"{label}: import", s == 200, j)
    if s != 200: raise RuntimeError(f"{label}: import failed")
    jreq("POST", f"/api/sets/{n}/start")
    return n


def sess(n): return json.load(open(os.path.join(DATA, "sets", n, "session.json")))


def closes(n): return [e for e in sess(n)["events"] if e[1].startswith(("end", "time up"))]

# Two 1-minute rounds start now and pass their deadline while the other sections run; "honest clock" (the last
# section) checks them, so the run waits only for whatever is left of the minute instead of sleeping 70 s.
try:
    D, E = clock_set("t-clk-d", 1), clock_set("t-clk-e", 1)      # started together; expire together
    req("PUT", f"/api/sets/{E}/files/main.py", "print('late edit')\n")   # E: an edit while still in time ...
except Exception as e:
    D = E = None; check("deadline sets D/E start", False, e)
DE_START = time.time()


def runfile(n, f, stdin=""):
    s, j = jreq("POST", f"/api/sets/{n}/run", {"file": f, "stdin": stdin})
    return j if s == 200 else {"verdict": f"HTTP {s} {j}", "stdin_case": {}, "testcases": []}


def sec(name):
    def deco(fn):
        print(f"--- {name}", flush=True)
        try: fn()
        except Exception: check(name + " (exception)", False, traceback.format_exc()[-400:])
    return deco


# ------------------------------------------------------------------ languages
PROGS = {
 "python": ("main.py", {"main.py": "import sys\nl = sys.stdin.readline().strip()\nprint(l.upper() if l else 'hello')\n"},
            None),
 "go": ("main.go", {"go.mod": "module x\n\ngo 1.22\n", "main.go":
        'package main\nimport ("bufio";"fmt";"os";"strings")\nfunc main(){ l,_ := bufio.NewReader(os.Stdin).ReadString(\'\\n\'); l = strings.TrimSpace(l)\n'
        ' if l == "" { fmt.Println("hello"); return }\n fmt.Println(strings.ToUpper(l)) }\n'},
        "package main\nfunc main( {\n"),
 "java": ("Main.java", {"Main.java": "import java.util.*;\npublic class Main { public static void main(String[] a){ Scanner s=new Scanner(System.in);"
          " String l = s.hasNextLine()? s.nextLine().trim() : \"\"; System.out.println(l.isEmpty()? \"hello\" : l.toUpperCase()); } }\n"},
          "public class Main { void }\n"),
 "c": ("main.c", {"main.c": "#include <stdio.h>\n#include <ctype.h>\nint main(){ char b[256]; if(!fgets(b,256,stdin)||b[0]=='\\n'){puts(\"hello\");return 0;}"
      " for(char*p=b;*p;p++)*p=toupper((unsigned char)*p); fputs(b,stdout); return 0; }\n"}, "int main( {\n"),
 "cpp": ("main.cpp", {"main.cpp": "#include <iostream>\n#include <string>\n#include <cctype>\nint main(){ std::string l; std::getline(std::cin,l);"
        " if(l.empty()){std::cout<<\"hello\\n\";return 0;} for(auto&c:l)c=toupper((unsigned char)c); std::cout<<l<<\"\\n\"; }\n"},
        "int main( {\n"),
}


def lang_test(lang):
    entry, files, broken = PROGS[lang]
    n = uniq(f"t-{lang}")
    m = manifest(n, lang, run_entry=entry, testcases=[{"stdin": "abc\n", "expected": "ABC"}, {"stdin": "abc\n", "expected": "NOPE"}])
    z = {"manifest.json": json.dumps(m), "problem.md": "# p\nhello\n"}
    z.update({"starter/" + k: v for k, v in files.items()})
    s, j = imp(mkzip(z)); check(f"{lang}: import", s == 200 and j.get("name") == n, (s, j))
    if s != 200: return
    check(f"{lang}: start", jreq("POST", f"/api/sets/{n}/start")[0] == 200)
    r = runfile(n, entry, "\n")
    check(f"{lang}: hello world", r["stdin_case"].get("stdout", "").strip() == "hello", r)
    tc = r["testcases"]
    check(f"{lang}: testcases pass/fail", len(tc) == 2 and tc[0].get("pass") is True and tc[1].get("pass") is False, tc)
    check(f"{lang}: verdict Wrong Answer", r["verdict"] == "Wrong Answer", r["verdict"])
    r = runfile(n, entry, "")
    check(f"{lang}: empty stdin next to testcases still shows stdout", (r.get("stdin_case") or {}).get("stdout", "").strip() == "hello" and len(r["testcases"]) == 2, r)
    r = runfile(n, entry, "xyz\n")
    check(f"{lang}: stdin transform", r["stdin_case"].get("stdout", "").strip() == "XYZ", r)
    if broken:
        s, _ = req("PUT", f"/api/sets/{n}/files/{entry}", broken)
        r = runfile(n, entry, "\n")
        check(f"{lang}: Compile Error", r["verdict"] == "Compile Error" and (r.get("compile") or {}).get("log", "").strip() != "", r)


for L in PROGS:
    sec(f"language {L}")(lambda L=L: lang_test(L))

# ------------------------------------------------------------------ edge cases
EDGE = {}


@sec("edge cases")
def _():
    n = uniq("t-edge")
    z = {"manifest.json": json.dumps(manifest(n, "python")), "problem.md": "x", "starter/main.py": "print('hi')\n"}
    s, j = imp(mkzip(z)); check("edge: import", s == 200, j)
    jreq("POST", f"/api/sets/{n}/start")

    def code(c, stdin=""):
        req("PUT", f"/api/sets/{n}/files/main.py", c); return runfile(n, "main.py", stdin)

    r = code("print('hi')\n")
    check("runtime ms present", isinstance(r["stdin_case"].get("ms"), int), r)
    check("memory_kb present", isinstance(r.get("memory_kb"), int), r.get("memory_kb"))
    r = code("while True: pass\n"); check("TLE (python)", r["verdict"] == "Time Limit Exceeded", r["verdict"])
    r = code("b = b'a' * (1 << 30)\nprint(len(b))\n"); check("memory limit", r["verdict"] == "Memory Limit Exceeded", (r["verdict"], r["stdin_case"]))
    t = time.time()
    r = code("import os\nwhile True:\n    try: os.fork()\n    except OSError: pass\n")
    dt = time.time() - t
    check("fork bomb finishes in 30s, not Accepted", dt < 30 and r["verdict"] != "Accepted", (dt, r["verdict"]))
    gone = False
    for _ in range(15):
        if not subprocess.run(["docker", "ps", "-q", "--filter", "label=ilab.runner=test"], capture_output=True, text=True).stdout.strip():
            gone = True; break
        time.sleep(1)
    check("no runner containers left after fork bomb", gone)
    r = code("import socket\ns=socket.socket(); s.settimeout(3)\ntry:\n    s.connect(('1.1.1.1',53)); print('CONNECTED')\nexcept Exception as e:\n    print('NETFAIL')\n")
    check("no network", "NETFAIL" in r["stdin_case"].get("stdout", ""), r["stdin_case"])
    r = code("for p in ('/etc/x','/x'):\n    try: open(p,'w').write('a'); print('WROTE',p)\n    except OSError: print('ROFAIL',p)\n"
             "open('/tmp/y','w').write('a'); print('TMPOK')\n")
    o = r["stdin_case"].get("stdout", "")
    check("read-only root, /tmp writable", "WROTE" not in o and o.count("ROFAIL") == 2 and "TMPOK" in o, o + r["stdin_case"].get("stderr", ""))
    r = code("print('a' * 1000000)\n")
    sc = r["stdin_case"]
    check("output truncation", sc.get("truncated") is True and len(sc.get("stdout", "")) <= 65536, (sc.get("truncated"), len(sc.get("stdout", ""))))
    # compiled TLE
    n2 = uniq("t-edgec")
    z = {"manifest.json": json.dumps(manifest(n2, "c")), "problem.md": "x", "starter/main.c": "int main(){for(;;);}\n"}
    imp(mkzip(z)); jreq("POST", f"/api/sets/{n2}/start")
    r = runfile(n2, "main.c"); check("TLE (c)", r["verdict"] == "Time Limit Exceeded", r["verdict"])


# ------------------------------------------------------------------ ready-screen leak + next
SECRET = "ZZQ-SECRET-PROBLEM-TEXT"
LEAK = None


@sec("ready screen leak check")
def _():
    global LEAK
    n = uniq("t-leak"); LEAK = n
    m = manifest(n, "python", tags=["test_p1_", "test_p2_"], hidden_tests=".hidden/tests_hidden.py",
                 reveal=[{"file": ".hidden/p2.md", "after_tag": "test_p1_", "or_minutes_left": None, "unlocks": "test_p2_"}])
    z = {"manifest.json": json.dumps(m), "problem.md": f"# {SECRET}\nsolve it\n", "starter/main.py": "pass\n",
         ".hidden/tests_hidden.py": "def test_p1_a():\n    assert False\ndef test_p2_a():\n    assert True\n",
         ".hidden/p2.md": "# part two SECRETPART\n"}
    s, j = imp(mkzip(z)); check("leak: import", s == 200, j)
    s, b = req("GET", f"/api/sets/{n}")
    j = json.loads(b)
    bad = [k for k in ("problem", "parts", "tags", "reveal", "files") if k in j]
    check("ready info has no secret keys", s == 200 and not bad, bad)
    check("problem text absent from ready body", SECRET.encode() not in b and b"SECRETPART" not in b)
    check("state before start is 409", req("GET", f"/api/sets/{n}/state")[0] == 409)
    check("files before start is 409", req("GET", f"/api/sets/{n}/files/main.py")[0] == 409)
    s, st = jreq("POST", f"/api/sets/{n}/start")
    check("state after start has problem", s == 200 and SECRET in st.get("problem", ""), st)
    s, st = jreq("POST", f"/api/sets/{n}/next")
    ev = json.dumps(st.get("events", []))
    check("/next reveals next part, logs 'asked to move on'", s == 200 and "asked to move on" in ev and any(p["file"].endswith("p2.md") for p in st.get("parts", [])), (s, ev))


# ------------------------------------------------------------------ grading flows
def load_zip(path):
    """Return (bytes with a fresh manifest name, new name, manifest)."""
    zi = zipfile.ZipFile(path); b = io.BytesIO(); man = None
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as zo:
        for i in zi.infolist():
            d = zi.read(i)
            if i.filename.split("/")[-1] == "manifest.json" and i.filename.count("/") <= 1:
                man = json.loads(d); man["name"] = uniq(man["name"][:50]); d = json.dumps(man).encode()
            zo.writestr(i.filename, d)
    return b.getvalue(), man["name"], man


def put_dir(n, d):
    for p in glob.glob(os.path.join(d, "**"), recursive=True):
        if os.path.isfile(p):
            rel = os.path.relpath(p, d)
            s, _ = req("PUT", f"/api/sets/{n}/files/{rel}", open(p, "rb").read())
            if s != 200: check(f"PUT {rel}", False, s)


def grading(label, setdir):
    zp = os.path.join(ZIPS, os.path.basename(setdir.rstrip("/")) + ".zip")
    if not os.path.exists(zp): return skip(f"grading {label}", f"{zp} missing")
    z, n, man = load_zip(zp)
    s, j = imp(z); check(f"{label}: import", s == 200, j)
    if s != 200: return
    check(f"{label}: start", jreq("POST", f"/api/sets/{n}/start")[0] == 200)
    tags = man.get("tags") or ["test_"]
    rev = (man.get("reveal") or [None])[0]
    s, sub = jreq("POST", f"/api/sets/{n}/submit")
    res = sub.get("results", {})
    t0 = res.get(tags[0], {})
    check(f"{label}: starter passes 0 of N", s == 200 and t0.get("passed") == 0 and t0.get("total", 0) > 0, t0)
    check(f"{label}: submit names the failing tests", t0.get("failed") and all(f.lower().startswith(tags[0].lower()) for f in t0["failed"]), t0)
    if rev: check(f"{label}: {rev['unlocks']} locked", rev["unlocks"] not in sub["state"]["unlocked"], sub["state"]["unlocked"])
    put_dir(n, os.path.join(setdir, "reference"))
    s, sub = jreq("POST", f"/api/sets/{n}/submit")
    res = sub.get("results", {}); t0 = res.get(tags[0], {})
    check(f"{label}: reference passes N/N on {tags[0]}", t0.get("total", 0) > 0 and t0.get("passed") == t0.get("total"), t0)
    if rev:
        bn = os.path.basename(rev["file"])
        check(f"{label}: {bn} revealed", any(x.endswith(bn) for x in sub.get("revealed", [])) and any(p["file"].endswith(bn) for p in sub["state"]["parts"]), sub.get("revealed"))
        s, sub = jreq("POST", f"/api/sets/{n}/submit")
        check(f"{label}: next submit grades {rev['unlocks']}", rev["unlocks"] in sub.get("results", {}), list(sub.get("results", {})))
    mp = os.path.join(setdir, "mutants.json")
    if os.path.exists(mp) and label.startswith("mini"):
        mu = json.load(open(mp))[0]
        src = open(os.path.join(setdir, "reference", mu["file"])).read()
        check(f"{label}: mutant applies", mu["old"] in src)
        req("PUT", f"/api/sets/{n}/files/{mu['file']}", src.replace(mu["old"], mu["new"], 1))
        s, sub = jreq("POST", f"/api/sets/{n}/submit")
        check(f"{label}: mutant '{mu.get('label')}' fails something", any(g.get("passed") != g.get("total") or g.get("status") != "graded" for g in sub.get("results", {}).values()), sub.get("results"))
        put_dir(n, os.path.join(setdir, "reference"))
    s, fin = jreq("POST", f"/api/sets/{n}/end")
    final = fin.get("final") or {}
    check(f"{label}: end -> final with failed lists", s == 200 and final and all("failed" in g for g in final.values() if g.get("status") == "graded"), final)
    check(f"{label}: on-time End -> final not after time", all(not g["after_time"] for g in final.values()), final)
    s, b = req("GET", f"/api/sets/{n}/export")
    try:
        zf = zipfile.ZipFile(io.BytesIO(b)); names = zf.namelist()
        check(f"{label}: export contents", any(x.startswith("submission/") for x in names) and all(x in names for x in ("session.json", "results.json", "manifest.json")), names[:20])
        ev = json.dumps(json.loads(zf.read("session.json"))["events"]).lower()
        check(f"{label}: session events", all(w in ev for w in ("start", "submit", "end")) and (not rev or "reveal" in ev), ev[:300])
    except Exception as e:
        check(f"{label}: export zip", False, e)


@sec("grading rate-limiter-py")
def _(): grading("rate-limiter-py", os.path.join(ROOT, "tests/sets/rate-limiter-py"))


for d in sorted(glob.glob(os.path.join(ROOT, "tests/sets/mini-*"))):
    sec(f"grading {os.path.basename(d)}")(lambda d=d: grading(os.path.basename(d), d))


@sec("levelled go/java: code at L1 still grades L1")
def _():
    # Go/Java compile the whole hidden tests file; L2 tests call a method the candidate hasn't written yet.
    cases = {
        "go": ({"starter/go.mod": "module calc\n\ngo 1.22\n", "starter/calc.go": "package calc\n\nfunc Add(a, b int) int { return a + b }\n"},
               ".hidden/hidden_test.go",
               'package calc\n\nimport "testing"\n\nfunc Test_l1_add(t *testing.T) {\n\tif Add(1, 2) != 3 {\n\t\tt.Fatal("add")\n\t}\n}\n\n'
               'func Test_l2_mul(t *testing.T) {\n\tif Mul(2, 3) != 6 {\n\t\tt.Fatal("mul")\n\t}\n}\n'),
        "java": ({"starter/Calc.java": "public class Calc { public static int add(int a, int b) { return a + b; } }\n"},
                 ".hidden/HiddenTest.java",
                 "public class HiddenTest {\n    static void test_l1_add() {\n        Expect.eq(3, Calc.add(1, 2));\n    }\n\n"
                 "    static void test_l2_mul() {\n        Expect.eq(6, Calc.mul(2, 3));\n    }\n}\n"),
    }
    for lang, (starter, ht, tests) in cases.items():
        n = uniq(f"t-lvl-{lang}")
        z = dict(starter); z[ht] = tests; z["problem.md"] = "L1"; z[".hidden/l2.md"] = "L2"
        z["manifest.json"] = json.dumps(manifest(n, lang, round="levelled", tags=["test_l1_", "test_l2_"], hidden_tests=ht,
                                                  reveal=[{"file": ".hidden/l2.md", "after_tag": "test_l1_", "or_minutes_left": None, "unlocks": "test_l2_"}]))
        s, j = imp(mkzip(z)); check(f"{lang} levelled: import", s == 200, j)
        jreq("POST", f"/api/sets/{n}/start")
        s, sub = jreq("POST", f"/api/sets/{n}/submit")
        g = sub.get("results", {}).get("test_l1_", {}) if s == 200 else {}
        check(f"{lang} levelled: L1 graded 1/1 without L2 methods", g.get("status") == "graded" and g.get("passed") == 1, sub)
        s, sub = jreq("POST", f"/api/sets/{n}/submit")
        g2 = sub.get("results", {}).get("test_l2_", {}) if s == 200 else {}
        check(f"{lang} levelled: L2 says could not be graded with a compiler line", g2.get("status") == "could not be graded" and ("Mul" in g2.get("last_line", "") or "symbol" in g2.get("last_line", "")), g2)


# ------------------------------------------------------------------ honest clock
@sec("final snapshot")
def _():
    n = clock_set("t-snap", 30)
    req("PUT", f"/api/sets/{n}/files/main.py", "print('at end')\n")
    jreq("POST", f"/api/sets/{n}/end")
    req("PUT", f"/api/sets/{n}/files/main.py", "print('after end')\n")
    z = zipfile.ZipFile(io.BytesIO(req("GET", f"/api/sets/{n}/export")[1]))
    check("export: final/ has the code at End, submission/ the latest", z.read("final/main.py") == b"print('at end')\n" and z.read("submission/main.py") == b"print('after end')\n", z.namelist())
    check("export: top-level files kept", all(x in z.namelist() for x in ("session.json", "results.json", "manifest.json")), z.namelist())
    m = clock_set("t-snap-open", 30)
    check("export of a never-closed set has no final/", not any(x.startswith("final/") for x in zipfile.ZipFile(io.BytesIO(req("GET", f"/api/sets/{m}/export")[1])).namelist()))
    lv = uniq("t-snap-lvl"); ht = ".hidden/test_hidden.py"
    zz = {"manifest.json": json.dumps(manifest(lv, "python", round="levelled", tags=["test_l1_", "test_l2_"], hidden_tests=ht,
          reveal=[{"file": ".hidden/l2.md", "after_tag": "test_l1_", "or_minutes_left": None, "unlocks": "test_l2_"}])),
          "problem.md": "L1", ".hidden/l2.md": "L2", "starter/main.py": "x=1\n", ht: "def test_l1_a():\n    assert True\ndef test_l2_a():\n    assert True\n"}
    imp(mkzip(zz)); jreq("POST", f"/api/sets/{lv}/start"); jreq("POST", f"/api/sets/{lv}/end")
    check("levelled: has_next true after End", jreq("GET", f"/api/sets/{lv}/state")[1]["has_next"] is True)
    st = jreq("POST", f"/api/sets/{lv}/next")[1]
    check("levelled: Next after End reveals, marked after time", any("l2.md" in e[1] and "(after time)" in e[1] for e in st["events"]), st["events"][-2:])


# ------------------------------------------------------------------ manifest sanity
@sec("manifest sanity")
def _():
    ht = ".hidden/tests_hidden.py"; tests = "def test_p1_a():\n    pass\ndef test_p2_a():\n    pass\n"
    rv = lambda f, a, u: {"file": f, "after_tag": a, "or_minutes_left": None, "unlocks": u}
    def bad(label, want, tags=("test_p1_", "test_p2_"), reveal=(), **kw):
        n = uniq("t-san")
        z = {"manifest.json": json.dumps(manifest(n, "python", tags=list(tags), hidden_tests=ht, reveal=list(reveal), **kw)), "problem.md": "x",
             "starter/main.py": "x=1\n", ht: tests, ".hidden/p2.md": "P2", ".hidden/p3.md": "P3"}
        s, j = imp(mkzip(z)); err = j.get("error", "")
        check(f"sanity: {label} -> 400 naming the field", s == 400 and all(w in err for w in want), (s, err))
    bad("C1 tag with no test", ["tags: test_p3_ matches no test in .hidden/tests_hidden.py"], tags=("test_p1_", "test_p2_", "test_p3_"),
        reveal=[rv(".hidden/p2.md", "test_p1_", "test_p2_"), rv(".hidden/p3.md", "test_p2_", "test_p3_")])
    bad("C2 two files unlock one tag", ["reveal[1].unlocks: test_p2_ is already unlocked by reveal[0]"],
        reveal=[rv(".hidden/p2.md", "test_p1_", "test_p2_"), rv(".hidden/p3.md", "test_p1_", "test_p2_")])
    bad("C3 one file twice", ["reveal[1].file: .hidden/p2.md is already revealed by reveal[0]"],
        reveal=[rv(".hidden/p2.md", "test_p1_", "test_p2_"), rv(".hidden/p2.md", "test_p1_", "test_p2_")])
    bad("self after_tag", ["reveal[0].after_tag: test_p2_ is never unlocked before this part"], reveal=[rv(".hidden/p2.md", "test_p2_", "test_p2_")])
    bad("missing reveal file", ["reveal[0].file: .hidden/nope.md is missing"], reveal=[rv(".hidden/nope.md", "test_p1_", "test_p2_")])
    for d in sorted(os.path.dirname(x) for x in glob.glob(os.path.join(ROOT, "tests", "sets", "*", "manifest.json"))):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "pack.py"), d, "/tmp/_san.zip"], capture_output=True, text=True)
        check(f"sanity: pack.py packs {os.path.basename(d.rstrip('/'))}", r.returncode == 0 and "packed" in r.stdout, r.stdout + r.stderr)
    sk = open(os.path.join(ROOT, "skill", "interview-practice", "SKILL.md")).read()
    for f in ("tools/pack.py", "backend/sandbox/gate.py"):
        src = open(os.path.join(ROOT, f)).read()
        check(f"sanity: SKILL.md embeds {f} unchanged", src in sk)


# ------------------------------------------------------------------ import validation
@sec("import validation")
def _():
    def snap():
        out = set()
        for d in (ROOT, os.path.expanduser("~"), "/tmp"):
            try: out |= {os.path.join(d, x) for x in os.listdir(d)}
            except OSError: pass
        return out
    p = os.path.join(ZIPS, "invalid-bad-manifest.zip")
    if os.path.exists(p):
        s, j = imp(open(p, "rb").read()); check("bad manifest -> 400 with message", s == 400 and len(j.get("error", "")) > 5, (s, j))
    else: skip("bad manifest", "zip missing")
    p = os.path.join(ZIPS, "evil-zipslip.zip")
    if os.path.exists(p):
        before = snap(); data = open(p, "rb").read()
        s, j = imp(data); time.sleep(1)
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        landed = [x for x in names if ".." in x and any(os.path.exists(os.path.normpath(os.path.join(DATA, b, x))) for b in ("", "sets", "sets/x"))]
        check("zip-slip -> 400, nothing escapes", s == 400 and not landed and snap() <= before, (s, j, landed, snap() - before))
    else: skip("zipslip", "zip missing")
    n = uniq("t-strip")
    z = {"manifest.json": json.dumps(manifest(n, "python")), "problem.md": "x", "starter/main.py": "print(1)\n",
         "reference/x.py": "secret", "mutants.json": "[]", "bugs.json": "[]"}
    s, j = imp(mkzip(z)); check("hand-made zip with reference/mutants/bugs imports", s == 200, j)
    left = [os.path.join(r, f) for r, _, fs in os.walk(os.path.join(DATA, "sets", n)) for f in fs if f in ("x.py", "mutants.json", "bugs.json")]
    check("reference/mutants/bugs not stored", os.path.isdir(os.path.join(DATA, "sets", n)) and not left, left)


# ------------------------------------------------------------------ import answers
@sec("import answers")
def _():
    n = uniq("t-ans")
    z = mkzip({"manifest.json": json.dumps(manifest(n, "python")), "problem.md": "x", "starter/main.py": "print(1)\n"})
    s, j = imp(z); check("first import: replaced false, title set", s == 200 and j.get("replaced") is False and j.get("title") == "T " + n and j.get("name") == n, (s, j))
    s, j = imp(z); check("same zip again: replaced true", s == 200 and j.get("replaced") is True, (s, j))
    jreq("POST", f"/api/sets/{n}/start")
    s, j = imp(z); check("started set: 409 asking for a new name", s == 409 and "new name" in j.get("error", "") and n in j["error"], (s, j))
    p = os.path.join(ZIPS, "invalid-bad-manifest.zip")
    if os.path.exists(p):
        s, j = imp(open(p, "rb").read())
        check("bad manifest: plain words first, field detail kept", s == 400 and j.get("error", "").startswith("This zip is not a valid Interview Lab set") and "format:" in j["error"], (s, j))
    else: skip("bad manifest wording", "zip missing")


# ------------------------------------------------------------------ security
@sec("security")
def _():
    check("no X-ILab -> 403", req("GET", "/api/health", hdr=False)[0] == 403)
    check("Host evil.com -> 403", req("GET", "/api/health", host="evil.com")[0] == 403)
    check("Origin evil -> 403", req("GET", "/api/health", headers={"Origin": "http://evil.com"})[0] == 403)
    check("good Origin ok", req("GET", "/api/health", headers={"Origin": f"http://127.0.0.1:{PORT}"})[0] == 200)
    n = LEAK
    if n:
        mpath = os.path.join(DATA, "sets", n, "manifest.json")
        mb = open(mpath, "rb").read() if os.path.exists(mpath) else None
        for p in ("..%2F..%2Fmanifest.json", "../.hidden/x", "..%2F.hidden%2Ftests_hidden.py", ".hidden/tests_hidden.py", "%2e%2e/manifest.json"):
            for meth in ("GET", "PUT"):
                s, b = req(meth, f"/api/sets/{n}/files/{p}", b"pwned" if meth == "PUT" else None)
                if meth == "PUT" and p == ".hidden/tests_hidden.py": continue  # lands in work/.hidden; real one checked below
                check(f"{meth} files/{p} -> 4xx", 400 <= s < 500, s)
                check(f"{meth} files/{p} leaks nothing", b"def test_p1_a" not in b and b"pwned" not in b and b"interview-set" not in b)
        hp = os.path.join(DATA, "sets", n, ".hidden", "tests_hidden.py")
        check("real .hidden tests untouched", not os.path.exists(hp) or b"def test_p1_a" in open(hp, "rb").read())
        if mb is not None: check("manifest.json untouched", open(mpath, "rb").read() == mb)
    out = subprocess.run(["ss", "-ltnH"], capture_output=True, text=True).stdout.splitlines()
    ls = [l.split()[3] for l in out if len(l.split()) > 3]
    mine = [a for a in ls if a.endswith(f":{PORT}")]
    check(f"{PORT} listens on 127.0.0.1 only", mine and all(a.startswith("127.0.0.1:") for a in mine), mine)
    check("nothing listens on 2375/8000", not [a for a in ls if a.endswith((":2375", ":8000"))], ls)
    for port in (2375, 8000):
        try: socket.create_connection(("127.0.0.1", port), timeout=2).close(); ok = False
        except OSError: ok = True
        check(f"connect 127.0.0.1:{port} fails", ok)
    for svc, port in (("backend", 8000), ("docker-proxy", 2375)):
        r = subprocess.run([os.path.join(ROOT, "tests/stack.sh"), "compose", "port", svc, str(port)], cwd=ROOT, capture_output=True, text=True)
        out = r.stdout + r.stderr   # unpublished reads "", ":0" or "invalid IP:0" depending on the Compose version
        check(f"compose port {svc} {port} publishes nothing", not re.search(r":[1-9][0-9]*\s*$", out, re.M), out)


@sec("sets say which is which")
def _():
    n = uniq("t-names"); ht = ".hidden/test_hidden.py"
    z = {"manifest.json": json.dumps(manifest(n, "python", minutes=5, hidden_tests=ht)), "problem.md": "x",
         "starter/main.py": "print('hi')\n", ht: "def test_ok():\n    assert True\n"}
    check("import", imp(mkzip(z))[0] == 200)
    row = lambda: next(r for r in jreq("GET", "/api/sets")[1]["sets"] if r["name"] == n)
    r = row()
    check("ready: minutes, left_s null", r["minutes"] == 5 and r["left_s"] is None and r["status"] == "ready", r)
    jreq("POST", f"/api/sets/{n}/start"); r = row()
    check("running: 0 < left_s <= minutes*60", r["status"] == "running" and 0 < r["left_s"] <= 300, r)
    jreq("POST", f"/api/sets/{n}/end"); r = row()
    check("ended: status ended, left_s null", r["status"] == "ended" and r["left_s"] is None, r)


@sec("honest clock")
def _():
    import threading
    A, B, C = clock_set("t-clk-a", 1), clock_set("t-clk-b", 1), clock_set("t-clk-c", 1, slow=True)
    s, sub = jreq("POST", f"/api/sets/{A}/submit")
    check("A: early Submit is in time", s == 200 and not sub["results"]["test_"]["after_time"], sub)
    time.sleep(5)
    s, fin = jreq("POST", f"/api/sets/{A}/end"); final = fin.get("final") or {}
    ev = [e[1] for e in sess(A)["events"]]
    check("A: End logs 'end' without suffix", "end" in ev and "end (after time)" not in ev, ev)
    check("A: final on time, at ~ close minute", final and all(not g["after_time"] and g["at"] <= 0.2 for g in final.values()), final)
    l1 = jreq("GET", f"/api/sets/{A}/state")[1]["left_s"]; time.sleep(3)
    check("A: left_s frozen after End", jreq("GET", f"/api/sets/{A}/state")[1]["left_s"] == l1, l1)
    s, sub = jreq("POST", f"/api/sets/{A}/submit")
    check("A: Submit after End is after time", sub["results"]["test_"]["after_time"] and "(after time)" in sess(A)["events"][-1][1], sess(A)["events"][-1])
    out = []
    ts = [threading.Thread(target=lambda: out.append(req("POST", f"/api/sets/{B}/end")[0])) for _ in range(2)]
    [t.start() for t in ts]; [t.join() for t in ts]
    check("B: two parallel Ends both 200, one close event", out == [200, 200] and len(closes(B)) == 1, (out, closes(B)))
    th = threading.Thread(target=lambda: out.append(("sub", jreq("POST", f"/api/sets/{C}/submit")[0]))); th.start(); time.sleep(1)
    s, fin = jreq("POST", f"/api/sets/{C}/end"); th.join()
    res = json.load(open(os.path.join(DATA, "sets", C, "results.json")))
    check("C: End during Submit waits and writes final", s == 200 and fin.get("final") and not res["test_"]["after_time"], (s, res))
    if not (D and E): raise RuntimeError("deadline sets D/E were not started")
    time.sleep(max(0, DE_START + 70 - time.time()))   # 10 s past their deadline; the earlier sections used most of it
    req("PUT", f"/api/sets/{E}/files/main.py", "print('later edit')\n")  # ... and after the deadline
    s, fin = jreq("POST", f"/api/sets/{D}/end")
    d = sess(D)
    check("D: close after deadline = 'time up' at 1.0, ended = deadline", any(e == [1.0, "time up"] for e in d["events"]) and abs(d["ended"] - (d["start"] + 60)) < 0.01, d["events"])
    check("D: no edits -> final on time", all(not g["after_time"] for g in (fin.get("final") or {"x": {"after_time": True}}).values()), fin.get("final"))
    s, fin = jreq("POST", f"/api/sets/{E}/end")
    check("E: edit after deadline -> final after_time", fin.get("final") and all(g["after_time"] for g in fin["final"].values()), fin.get("final"))


@sec("delete a set")
def _():
    n = uniq("t-del"); ht = ".hidden/test_hidden.py"
    zb = mkzip({"manifest.json": json.dumps(manifest(n, "python", minutes=5, hidden_tests=ht)), "problem.md": "x",
                "starter/main.py": "print('hi')\n", ht: "def test_ok():\n    assert True\n"})
    names = lambda: [r["name"] for r in jreq("GET", "/api/sets")[1]["sets"]]
    deleted = lambda: [d for d in os.listdir(os.path.join(DATA, "deleted")) if d.startswith(n + "-")] if os.path.isdir(os.path.join(DATA, "deleted")) else []
    check("import", imp(zb)[0] == 200)
    check("DELETE without X-ILab is refused", req("DELETE", f"/api/sets/{n}", hdr=False)[0] == 403 and n in names())
    s, j = jreq("DELETE", f"/api/sets/{n}")
    check("DELETE: 200 with name, title, moved_to", s == 200 and j.get("name") == n and j.get("title") == "T " + n and "/deleted/" in j.get("moved_to", ""), j)
    check("gone from the list, folder under deleted/", n not in names() and len(deleted()) == 1 and not os.path.exists(os.path.join(DATA, "sets", n)) and os.path.isfile(os.path.join(DATA, "deleted", deleted()[0], "manifest.json")), deleted())
    check("re-import the same zip", imp(zb)[0] == 200 and n in names())
    jreq("POST", f"/api/sets/{n}/start")
    s, j = jreq("DELETE", f"/api/sets/{n}")
    check("running set: 409 with the message", s == 409 and j.get("error") == "This round is in progress. End it first, then delete it." and n in names(), (s, j))
    jreq("POST", f"/api/sets/{n}/end")
    check("ended set can be deleted; second copy kept too", jreq("DELETE", f"/api/sets/{n}")[0] == 200 and n not in names() and len(deleted()) == 2, deleted())
    check("unknown name: 404", jreq("DELETE", "/api/sets/no-such-set")[0] == 404)


@sec("run a library (no program)")
def _():
    def lib(label, **kw):
        n = uniq("t-lib")
        z = {"manifest.json": json.dumps(manifest(n, "go", **kw)), "problem.md": "x",
             "starter/go.mod": "module flagstore\n\ngo 1.22\n", "starter/store.go": "package flagstore\n\nfunc Get() int { return 1 }\n"}
        s, j = imp(mkzip(z)); check(f"{label}: import", s == 200, j)
        jreq("POST", f"/api/sets/{n}/start")
        r = runfile(n, "store.go"); return r, (r.get("compile") or {})

    r, c = lib("lib with My tests", your_tests="*_test.go"); log = c.get("log", "")
    check("lib with My tests: Nothing to run, package named, mentions My tests, no shell error",
          c.get("ok") is False and "Nothing to run" in log and "flagstore" in log and "My tests" in log and "Syntax error" not in json.dumps(r), r)
    r, c = lib("lib without My tests"); log = c.get("log", "")
    check("lib without My tests: Nothing to run, package named, says Check it with Submit., no My tests",
          c.get("ok") is False and "Nothing to run" in log and "flagstore" in log and "Check it with Submit." in log and "My tests" not in log, r)


@sec("go: one panicking test doesn't stop the others")
def _():
    n = uniq("t-goiso"); ht = ".hidden/hidden_test.go"
    z = {"manifest.json": json.dumps(manifest(n, "go", tags=["test_p1_"], hidden_tests=ht)), "problem.md": "x",
         "starter/go.mod": "module flagstore\n\ngo 1.22\n",
         "starter/store.go": ("package flagstore\n\ntype Store struct{ m map[string]bool }\n\n"
                              "func NewStore() *Store { return &Store{m: map[string]bool{}} }\n\n"
                              "func (s *Store) Create(k string) bool { if _, ok := s.m[k]; ok { return false }; s.m[k] = true; return true }\n\n"
                              "func (s *Store) Get(k string) bool { panic(\"not implemented\") }\n"),
         # the Get test runs first and panics; Create is finished and its test must still count
         ht: ("package flagstore\n\nimport \"testing\"\n\n"
              "func Test_p1_get(t *testing.T) { s := NewStore(); s.Create(\"a\"); if !s.Get(\"a\") { t.Fatal(\"get\") } }\n\n"
              "func Test_p1_create_twice(t *testing.T) { s := NewStore(); if !s.Create(\"a\") || s.Create(\"a\") { t.Fatal(\"create\") } }\n")}
    s, j = imp(mkzip(z)); check("goiso: import", s == 200, j)
    jreq("POST", f"/api/sets/{n}/start")
    s, sub = jreq("POST", f"/api/sets/{n}/submit")
    r = sub.get("results", {}).get("test_p1_", {})
    check("goiso: the finished function's test passes although another test panics", s == 200 and r.get("passed") == 1 and r.get("total") == 2, r)
    check("goiso: the failure is the panic, not 'did not run'", "did not run" not in json.dumps(r) and "panic" in r.get("last_error", ""), r)


@sec("problem catalog")
def _():
    s, j = jreq("GET", "/api/catalog"); ps = j.get("problems", [])
    built = [p for p in ps if p.get("source") == "builtin"]
    check("catalog lists the built-in problems with ready-screen fields", s == 200 and len(built) >= 10 and all(p.get("id") and p.get("title") and p.get("round") and p.get("languages") and "attempts" in p for p in ps), j)
    sys.path.insert(0, os.path.join(ROOT, "backend")); from lab import variants
    for d in sorted(glob.glob(os.path.join(ROOT, "catalog", "*", "problem.json"))):
        d = os.path.dirname(d); pid = os.path.basename(d)
        for lang in variants.languages(d):
            t = f"/tmp/_cat/{pid}/{lang}"; shutil.rmtree(t, ignore_errors=True); variants.write(variants.render(d, lang), t)
            for f in os.listdir(os.path.join(t, ".hidden")):
                if os.path.isfile(os.path.join(t, ".hidden", f)): shutil.copy(os.path.join(t, ".hidden", f), os.path.join(t, f))
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "pack.py"), t, "/tmp/_cat.zip"], capture_output=True, text=True)
            check(f"sanity: catalog/{pid} renders a valid {lang} set", r.returncode == 0 and "packed" in r.stdout, r.stdout + r.stderr)
            check(f"sanity: answers/{pid}/{lang} has the reference", os.path.isdir(os.path.join(ROOT, "answers", pid, lang, "reference")))
    for d in sorted(glob.glob(os.path.join(ROOT, "catalog", "*", "manifest.json"))):
        d = os.path.dirname(d); r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "pack.py"), d, "/tmp/_cat.zip"], capture_output=True, text=True)
        check(f"sanity: catalog/{os.path.basename(d)} is a valid set", r.returncode == 0 and "packed" in r.stdout, r.stdout + r.stderr)
    for d in sorted(glob.glob(os.path.join(ROOT, "catalog", "*", "manifest.json"))):   # old-layout problems
        pid = os.path.basename(os.path.dirname(d)); ans = os.path.join(ROOT, "answers", pid)
        check(f"sanity: answers/{pid} has the reference and the same hidden tests", os.path.isdir(os.path.join(ans, "reference"))
              and all(open(os.path.join(ROOT, "catalog", pid, ".hidden", f), "rb").read() == open(next(p for p in (os.path.join(ans, f), os.path.join(ans, "levels", f)) if os.path.exists(p)), "rb").read()
                      for f in os.listdir(os.path.join(ROOT, "catalog", pid, ".hidden"))))
    multi = next((x for x in built if len(x.get("languages", [])) > 1), None)
    if multi:
        q = multi["id"]; l1, l2 = multi["languages"][:2]
        s1, x1 = jreq("POST", f"/api/catalog/{q}/attempt", {"language": l1}); s2, x2 = jreq("POST", f"/api/catalog/{q}/attempt", {"language": l2})
        check("a problem in two languages: one attempt per language, named <id>-<lang>-<k>", s1 == s2 == 200 and x1["name"] == f"{q}-{l1}-1"
              and x2["name"] == f"{q}-{l2}-1" and x1["language"] == l1 and x2["language"] == l2, (x1, x2))
        m2 = json.load(open(os.path.join(DATA, "sets", x2["name"], "manifest.json")))
        check("the attempt is a set in that language", m2.get("language") == l2 and m2.get("problem") == q, m2)
        check("several languages need a language", jreq("POST", f"/api/catalog/{q}/attempt")[0] == 400)
        check("an unknown language is refused", jreq("POST", f"/api/catalog/{q}/attempt", {"language": "cobol"})[0] == 400)
    else: skip("problem in two languages", "no catalog problem has two languages yet")
    fresh = next((x for x in built if x is not multi), None)   # one the two-language check above hasn't picked yet
    p = fresh["id"] if fresh else "none"
    row = lambda: next((x for x in jreq("GET", "/api/catalog")[1]["problems"] if x["id"] == p), {})
    s, a = jreq("POST", f"/api/catalog/{p}/attempt", {"language": fresh["languages"][0]} if fresh else {})
    check("attempt: a copy named <id>-<k>, not reused", s == 200 and a.get("name", "").startswith(p + "-") and a.get("reused") is False, a)
    m = json.load(open(os.path.join(DATA, "sets", a["name"], "manifest.json"))) if s == 200 else {}
    check("the attempt's manifest has its own name and the problem it came from", m.get("name") == a.get("name") and m.get("problem") == p, m)
    check("the attempt opens on the ready screen and lists its problem", jreq("GET", f"/api/sets/{a.get('name')}")[1].get("status") == "ready"
          and any(x["name"] == a.get("name") and x.get("problem") == p for x in jreq("GET", "/api/sets")[1]["sets"]))
    check("picking again while unstarted: the same attempt", jreq("POST", f"/api/catalog/{p}/attempt", {"language": a.get("language")})[1] == a | {"reused": True})
    jreq("POST", f"/api/sets/{a['name']}/start")
    check("picking while it runs: back to the running attempt", jreq("POST", f"/api/catalog/{p}/attempt", {"language": a.get("language")})[1].get("name") == a["name"])
    jreq("POST", f"/api/sets/{a['name']}/end")
    s, c = jreq("POST", f"/api/catalog/{p}/attempt", {"language": a.get("language")})
    check("after it finished: a new attempt", s == 200 and c.get("name") not in (None, a["name"]) and c.get("reused") is False, c)
    check("the catalog counts the finished attempt", row().get("attempts", 0) >= 1 and row().get("last") == "ended", row())
    n = uniq("t-cat"); ht = ".hidden/test_hidden.py"
    zb = mkzip({"manifest.json": json.dumps(manifest(n, "python", hidden_tests=ht)), "problem.md": "x",
                "starter/main.py": "print('hi')\n", ht: "def test_ok():\n    assert True\n"})
    check("a dropped set imports as before", imp(zb)[0] == 200)
    mine = next((x for x in jreq("GET", "/api/catalog")[1]["problems"] if x["id"] == n), {})
    check("and joins the catalog as your own problem", mine.get("source") == "custom" and mine.get("title") == "T " + n, mine)
    check("picking it opens the imported attempt", jreq("POST", f"/api/catalog/{n}/attempt")[1].get("name") == n)
    jreq("POST", f"/api/sets/{n}/start"); jreq("POST", f"/api/sets/{n}/end")
    s, d = jreq("POST", f"/api/catalog/{n}/attempt")
    check("retaking your own problem: a fresh <id>-1", s == 200 and d.get("name") == n + "-1", d)
    check("unknown problem: 404", jreq("POST", "/api/catalog/no-such-problem/attempt")[0] == 404)
    check("catalog needs X-ILab", req("GET", "/api/catalog", hdr=False)[0] == 403)

@sec("levelled: Run grades one example per unlocked level")
def _():
    for lang in ("python", "go", "java"):
        s, a = jreq("POST", "/api/catalog/cart-levelled/attempt", {"language": lang}); n = a.get("name")
        check(f"{lang}: attempt", s == 200, a)
        if s != 200: continue
        st = jreq("POST", f"/api/sets/{n}/start")[1]
        check(f"{lang}: Run checks examples; no My tests, no stdin program", st.get("has_examples") and not st.get("has_mytests") and not st.get("run_entry"), st)
        s, r = jreq("POST", f"/api/sets/{n}/run", {})
        ex = r.get("examples", {})
        check(f"{lang}: starter fails the L1 example, by name", s == 200 and list(ex) == ["test_l1_"] and ex["test_l1_"].get("passed") == 0
              and ex["test_l1_"].get("total") == 1 and ex["test_l1_"].get("failed"), r)
        put_dir(n, os.path.join(ROOT, "answers", "cart-levelled", lang, "reference"))
        ex = jreq("POST", f"/api/sets/{n}/run", {})[1].get("examples", {})
        check(f"{lang}: the reference passes the L1 example", ex.get("test_l1_", {}).get("passed") == 1, ex)
        st = jreq("GET", f"/api/sets/{n}/state")[1]
        check(f"{lang}: Run unlocks nothing and isn't a Submit", st["unlocked"] == ["test_l1_"] and not st["results"] and any(e[1].startswith("run examples: test_l1_ 1/1") for e in st["events"]), st["unlocked"])
        sub = jreq("POST", f"/api/sets/{n}/submit")[1].get("results", {}).get("test_l1_", {})
        check(f"{lang}: Submit still runs the full L1 tests", sub.get("total", 0) > 1 and sub.get("passed") == sub.get("total"), sub)
        ex = jreq("POST", f"/api/sets/{n}/run", {})[1].get("examples", {})
        check(f"{lang}: after L2 opens, Run checks L1 and L2", list(ex) == ["test_l1_", "test_l2_"] and all(g.get("passed") == 1 for g in ex.values()), ex)
        jreq("POST", f"/api/sets/{n}/end")


@sec("run: stdout with an empty stdin box")
def _():
    n = uniq("t-stdout")
    m = manifest(n, "python", run_entry="main.py", testcases=[{"stdin": "abc\n", "expected": "ABC"}])
    s, j = imp(mkzip({"manifest.json": json.dumps(m), "problem.md": "x", "starter/main.py": "print(input().upper())\n"}))
    check("import", s == 200, j); jreq("POST", f"/api/sets/{n}/start")
    r = runfile(n, "main.py", "")
    sc = r.get("stdin_case") or {}
    check("the empty-stdin run is shown (its crash included)", sc.get("verdict") == "Runtime Error" and "EOFError" in sc.get("stderr", ""), sc)
    check("the testcases decide the verdict when stdin is empty", r["verdict"] == "Accepted" and r["testcases"][0]["pass"], r)
    r = runfile(n, "main.py", "")
    r2 = runfile(n, "main.py", "xy\n")
    check("typed stdin: shown and counted", (r2.get("stdin_case") or {}).get("stdout", "").strip() == "XY" and r2["verdict"] == "Accepted", r2)


# ------------------------------------------------------------------ code help (language server)
@sec("code help: Python (pyright)")
def _():
    def attempt():
        a = jreq("POST", "/api/catalog/ledger-codebase/attempt", {"language": "python"})[1]["name"]; jreq("POST", f"/api/sets/{a}/start"); return a
    def assist(n, op, file="main.py", text=None, line=0, col=0, **k):
        return jreq("POST", f"/api/sets/{n}/assist", {"op": op, "file": file, "text": text, "line": line, "col": col, **k})
    def ready(n, secs=20):
        for _ in range(int(secs * 2)):
            if assist(n, "complete", text="")[1].get("state") == "ready": return True
            time.sleep(0.5)
        return False
    def containers(): return subprocess.run(["docker", "ps", "-q", "--filter", "label=ilab.lsp=test"], capture_output=True, text=True).stdout.split()
    def gone(secs=5):
        for _ in range(secs * 2):
            if not containers(): return True
            time.sleep(0.5)
        return False
    seen = []   # every response body, for the leak scan
    def at(n, op, text, line, col, **k):
        for _ in range(20):   # a check with no fresh answer yet carries no "diagnostics": ask again (up to ~10 s), so [] always means a real "no errors"
            s, j = assist(n, op, text=text, line=line, col=col, **k); seen.append(j)
            if op != "check" or "diagnostics" in j or j.get("state") != "ready": return j
            time.sleep(0.5)
        return j
    def labels(j): r = j.get("result") or {}; return [i["label"] for i in (r.get("items") if isinstance(r, dict) else r) or []]
    A = attempt()
    main = req("GET", f"/api/sets/{A}/files/main.py")[1].decode()
    s, _ = jreq("POST", f"/api/sets/{A}/assist", {"op": "complete", "file": "main.py", "text": "", "line": 0, "col": 0}); check("assist is accepted after Start", s == 200, s)
    n0 = uniq("t-ca")
    z = {"manifest.json": json.dumps(manifest(n0, "python")), "problem.md": "x", "starter/main.py": "print(1)\n"}
    imp(mkzip(z))
    check("assist before Start: 409", assist(n0, "complete", text="")[0] == 409)
    check("code help reaches ready within 20 s", ready(A))
    ln = main.split("\n").index('    return ["ok"]')   # inside handle()
    def with_line(extra): L = main.split("\n"); L.insert(ln, extra); return "\n".join(L)
    j = at(A, "complete", with_line("    l.bal"), ln, 9)
    check("own type: l.bal lists balance_at (ledger.py never opened)", "balance_at" in labels(j), labels(j)[:10])
    t = "import heapq\n" + with_line("    heapq.heap"); j = at(A, "complete", t, ln + 1, 14)
    check("stdlib: heapq.heap lists heappush", "heappush" in labels(j), labels(j)[:10])
    t = "import heapq\n" + with_line("    heapq.heappush("); j = at(A, "signature", t, ln + 1, 19)
    sigs = ((j.get("result") or {}).get("signatures") or [])
    check("signature help for heapq.heappush(", any("heap" in x.get("label", "") for x in sigs), j)
    L = main.split("\n"); hl = next(i for i, x in enumerate(L) if x.startswith("def handle(l: Ledger"))
    j = at(A, "hover", main, hl, 17)
    hv = json.dumps(j.get("result"))
    check("hover on Ledger names the class", "Ledger" in hv and "class" in hv, hv[:200])
    t = with_line("    undefined_name()"); t0 = time.time(); j = at(A, "check", t, 0, 0)
    d = [x for x in j.get("diagnostics", []) if x["range"]["start"]["line"] == ln]
    check("codebase round: an undefined name is underlined within 2 s", len(d) == 1 and "undefined_name" in d[0]["message"] and time.time() - t0 < 2.5, (j, time.time() - t0))
    j = at(A, "check", with_line("    l.balance('a')"), 0, 0)
    check("codebase round: type errors are not underlined (they would give away the planted bugs)", j.get("diagnostics") == [], j)
    j = at(A, "check", main + "\ndef broken(:\n", 0, 0)
    check("codebase round: a syntax error is underlined", any(x.get("severity") == 1 for x in j.get("diagnostics", [])), j)
    ex = req("GET", f"/api/sets/{A}/files/test_example.py")[1].decode()
    check("the untouched starter test file has no diagnostics", at(A, "check", ex, 0, 0, file="test_example.py").get("diagnostics") == [], None)
    check("main.py as shipped has no diagnostics", at(A, "check", main, 0, 0).get("diagnostics") == [], None)
    req("PUT", f"/api/sets/{A}/files/ledger/ledger.py", req("GET", f"/api/sets/{A}/files/ledger/ledger.py")[1].decode() + "\n    def zz_probe(self):\n        return 1\n")
    j = at(A, "complete", with_line("    l.zz_"), ln, 9)
    check("a method saved in ledger.py shows in main.py's suggestions (main.py not resent)", "zz_probe" in labels(j), labels(j)[:10])
    # leak: the hidden tests define test_p1_... in .hidden/tests_hidden.py
    j1 = at(A, "complete", "import tests_h", 0, 14, file="probe.py"); j2 = at(A, "complete", "test_p1_", 0, 8, file="probe.py")
    bad = [x for x in labels(j1) + labels(j2) if x.startswith(("test_p1_", "tests_hidden"))]
    check("hidden test names are never offered", not bad, bad)
    blob = json.dumps(seen)
    check("no container path, .hidden or link in any result", "/tmp/w" not in blob and ".hidden" not in blob and "](" not in blob, [m for m in ("/tmp/w", ".hidden", "](") if m in blob])
    ids = containers()
    check("exactly one language-server container", len(ids) == 1, ids)
    if len(ids) == 1:
        o = json.loads(subprocess.run(["docker", "inspect", ids[0]], capture_output=True, text=True).stdout)[0]
        hc = o["HostConfig"]
        check("container is locked down", hc["NetworkMode"] == "none" and hc["ReadonlyRootfs"] is True and hc["Memory"] == 536870912
              and hc["MemorySwap"] == 536870912 and hc["NanoCpus"] == 2000000000 and hc["PidsLimit"] == 256 and hc["CapDrop"] == ["ALL"]
              and "no-new-privileges" in " ".join(hc["SecurityOpt"]) and not hc["PortBindings"] and not o["Mounts"] and not o["NetworkSettings"]["Ports"], hc)
    check("bad op: 400", assist(A, "nope")[0] == 400)
    check("file ../x: 400", assist(A, "complete", file="../x")[0] == 400)
    check("file .hidden/x: 400", assist(A, "complete", file=".hidden/x")[0] == 400)
    check("stop: the container is gone within 5 s", assist(A, "stop")[0] == 200 and gone())
    check("a request after stop starts a new session", ready(A))
    jreq("POST", f"/api/sets/{A}/end")
    check("delete a set with a live session: the container is gone within 5 s", jreq("DELETE", f"/api/sets/{A}")[0] == 200 and gone())
    def errors(n, rels):
        out = {}
        for f in rels:
            d = at(n, "check", req("GET", f"/api/sets/{n}/files/{f}")[1].decode(), 0, 0, file=f).get("diagnostics")
            e = [x["message"] for x in d or [] if x.get("severity") == 1]
            if e or d is None: out[f] = e or "no answer"
        return out
    for prob in ("ledger-codebase", "jobqueue-codebase", "quota-codebase"):
        a = jreq("POST", f"/api/catalog/{prob}/attempt", {"language": "python"})[1]["name"]; jreq("POST", f"/api/sets/{a}/start")
        ready(a)
        py = [f for f in jreq("GET", f"/api/sets/{a}/state")[1]["files"] if f.endswith(".py")]
        check(f"{prob}: untouched starter files have 0 errors", errors(a, py) == {}, errors(a, py))
        jreq("POST", f"/api/sets/{a}/end")
    a = jreq("POST", "/api/catalog/invoice-tdd/attempt", {"language": "python"})[1]["name"]; jreq("POST", f"/api/sets/{a}/start"); ready(a)
    check("invoice-tdd: untouched test_example.py has 0 errors (import pytest resolves)", errors(a, ["test_example.py"]) == {}, errors(a, ["test_example.py"]))
    j = at(a, "check", "def f(a, b): return a\nf(1)\n", 0, 0, file="probe.py")
    check("other rounds keep type checking: a missing argument is underlined", any("b" in x["message"] for x in j.get("diagnostics", [])), j)
    jreq("POST", f"/api/sets/{a}/end")
    # stdin handover: a 100 KB file saved before the server starts
    B = attempt()
    big = "".join(f"def big_fn_{i:04d}(x):\n    return x + {i}\n\n" for i in range(3500)) + "def big_last_fn(x):\n    return x\n"
    req("PUT", f"/api/sets/{B}/files/big.py", big)
    check("big.py is over 100 KB", len(big) > 100_000, len(big))
    check("a 100 KB file before start: the server still reaches ready", ready(B))
    j = at(B, "complete", "from big import big_last", 0, 24)
    check("and offers big.py's last function", "big_last_fn" in labels(j), labels(j)[:5])
    jreq("POST", f"/api/sets/{B}/end"); assist(B, "stop"); gone()


@sec("code help: Go (gopls)")
def _():
    def assist(n, op, file="cmd/run/main.go", text=None, line=0, col=0, **k):
        return jreq("POST", f"/api/sets/{n}/assist", {"op": op, "file": file, "text": text, "line": line, "col": col, **k})
    def ready(n, secs=30):
        for _ in range(int(secs * 2)):
            if assist(n, "complete", text="")[1].get("state") == "ready": return True
            time.sleep(0.5)
        return False
    def containers(): return subprocess.run(["docker", "ps", "-q", "--filter", "label=ilab.lsp=test"], capture_output=True, text=True).stdout.split()
    def gone(secs=5):
        for _ in range(secs * 2):
            if not containers(): return True
            time.sleep(0.5)
        return False
    seen = []   # every response body, for the leak scan
    def at(n, op, text, line, col, **k):
        for _ in range(20):   # a check with no fresh answer yet carries no "diagnostics": ask again (up to ~10 s), so [] always means a real "no errors"
            s, j = assist(n, op, text=text, line=line, col=col, **k); seen.append(j)
            if op != "check" or "diagnostics" in j or j.get("state") != "ready": return j
            time.sleep(0.5)
        return j
    def labels(j): r = j.get("result") or {}; return [i["label"] for i in (r.get("items") if isinstance(r, dict) else r) or []]
    def start(prob):
        a = jreq("POST", f"/api/catalog/{prob}/attempt", {"language": "go"})[1]["name"]; jreq("POST", f"/api/sets/{a}/start"); return a
    A = start("ledger-codebase")
    main = req("GET", f"/api/sets/{A}/files/cmd/run/main.go")[1].decode()
    check("Go code help reaches ready within 30 s", ready(A))
    L = main.split("\n"); ln = next(i for i, x in enumerate(L) if x.strip().startswith("switch {"))   # inside the command loop
    def with_line(extra): M = list(L); M.insert(ln, extra); return "\n".join(M)
    j = at(A, "complete", with_line("\t\tl.Bal"), ln, 7)
    check("own type: l.Bal lists Balance and BalanceAt (ledger.go never opened)", {"Balance", "BalanceAt"} <= set(labels(j)), labels(j)[:10])
    j = at(A, "complete", with_line("\t\tstrings.Has"), ln, 13)
    check("stdlib: strings.Has lists HasPrefix and HasSuffix", {"HasPrefix", "HasSuffix"} <= set(labels(j)), labels(j)[:10])
    t = with_line("\t\tvar b strings.Builder\n\t\tb.Wri"); j = at(A, "complete", t, ln + 1, 7)
    check("b.Wri lists Write, WriteByte, WriteRune, WriteString", {"Write", "WriteByte", "WriteRune", "WriteString"} <= set(labels(j)), labels(j)[:10])
    j = at(A, "signature", with_line("\t\t_ = l.Balance("), ln, 16)
    check("signature help for l.Balance(", any("account" in x.get("label", "") for x in (j.get("result") or {}).get("signatures", [])), j)
    k = next(i for i, x in enumerate(L) if "ledger.New()" in x); j = at(A, "hover", main, k, L[k].index("New") + 1)
    hv = json.dumps(j.get("result"))
    check("hover on New: signature and doc, no link", "New() *ledger.Ledger" in hv and "returns an empty ledger" in hv and "pkg.go.dev" not in hv, hv[:300])
    t0 = time.time(); j = at(A, "check", with_line("\t\t_ = l.Balance(\"a\")"), 0, 0)
    d = [x for x in j.get("diagnostics", []) if x["range"]["start"]["line"] == ln]
    check("a call with too few arguments is underlined within 2 s, saying what is wanted",
          len(d) == 1 and "not enough arguments" in d[0]["message"] and "want (string, string)" in d[0]["message"] and time.time() - t0 < 2.5, (j, time.time() - t0))
    check("main.go as shipped has no diagnostics", at(A, "check", main, 0, 0).get("diagnostics") == [], None)
    check("ledger_example_test.go as shipped has no diagnostics",
          at(A, "check", req("GET", f"/api/sets/{A}/files/ledger_example_test.go")[1].decode(), 0, 0, file="ledger_example_test.go").get("diagnostics") == [], None)
    req("PUT", f"/api/sets/{A}/files/extra.go", "package ledger\n\nfunc ZzProbe() int { return 1 }\n")
    j = at(A, "complete", with_line("\t\tledger.Zz"), ln, 11)
    check("a new file in package ledger: ledger.ZzProbe is offered from main.go (main.go not resent)", "ZzProbe" in labels(j), labels(j)[:10])
    # leak: the hidden tests define Test_p1_... in .hidden/hidden_test.go
    j1 = at(A, "complete", "package ledger\nfunc Test_p1", 1, 12, file="probe.go"); j2 = at(A, "complete", "package ledger\nfunc TestP1", 1, 11, file="probe.go")
    bad = [x for x in labels(j1) + labels(j2) if "p1" in x.lower()]
    check("hidden test names are never offered", not bad, bad)
    blob = json.dumps(seen)
    check("no container path, .hidden, link or pkg.go.dev in any result", "/tmp/w" not in blob and ".hidden" not in blob and "](" not in blob and "pkg.go.dev" not in blob,
          [m for m in ("/tmp/w", ".hidden", "](", "pkg.go.dev") if m in blob])
    ids = containers()
    check("exactly one language-server container", len(ids) == 1, ids)
    if len(ids) == 1:
        o = json.loads(subprocess.run(["docker", "inspect", ids[0]], capture_output=True, text=True).stdout)[0]
        hc = o["HostConfig"]
        print("  docker inspect:", {k: hc[k] for k in ("NetworkMode", "ReadonlyRootfs", "Memory", "MemorySwap", "NanoCpus", "PidsLimit", "CapDrop", "SecurityOpt", "PortBindings")}, "mounts", o["Mounts"], flush=True)
        check("container is locked down", hc["NetworkMode"] == "none" and hc["ReadonlyRootfs"] is True and hc["Memory"] == 536870912
              and hc["MemorySwap"] == 536870912 and hc["NanoCpus"] == 2000000000 and hc["PidsLimit"] == 256 and hc["CapDrop"] == ["ALL"]
              and "no-new-privileges" in " ".join(hc["SecurityOpt"]) and not hc["PortBindings"] and not o["Mounts"] and not o["NetworkSettings"]["Ports"], hc)
    check("stop: the container is gone within 5 s", assist(A, "stop")[0] == 200 and gone())
    check("a request after stop starts a new session", ready(A))
    jreq("POST", f"/api/sets/{A}/end")
    check("delete a set with a live session: the container is gone within 5 s", jreq("DELETE", f"/api/sets/{A}")[0] == 200 and gone())
    # every untouched Go starter: 0 diagnostics at all (errors, warnings, hints) in the editor, in every round type
    total = {}
    for prob in sorted(os.path.basename(d) for d in glob.glob(os.path.join(ROOT, "catalog/*-*"))):
        a = start(prob); ready(a)
        gos = [f for f in jreq("GET", f"/api/sets/{a}/state")[1]["files"] if f.endswith(".go")]
        bad = {}
        for f in gos:
            d = at(a, "check", req("GET", f"/api/sets/{a}/files/{f}")[1].decode(), 0, 0, file=f).get("diagnostics")
            if d is None or d: bad[f] = "no answer" if d is None else [(x.get("severity"), x["message"]) for x in d]
        total[prob] = (len(gos), len(bad))
        check(f"{prob}: {len(gos)} untouched Go files, 0 diagnostics", bad == {}, bad)
        jreq("POST", f"/api/sets/{a}/end")
    print("  Go starters checked:", sum(v[0] for v in total.values()), "files in", len(total), "problems;", sum(v[1] for v in total.values()), "files with diagnostics", flush=True)
    # stdin handover: a 100 KB file saved before the server starts
    B = start("ledger-codebase")
    big = "package ledger\n\n" + "".join(f"func BigFn{i:04d}(x int) int {{ return x + {i} }}\n\n" for i in range(3000)) + "func BigLastFn(x int) int { return x }\n"
    req("PUT", f"/api/sets/{B}/files/big.go", big)
    check("big.go is over 100 KB", len(big) > 100_000, len(big))
    check("a 100 KB file before start: the server still reaches ready", ready(B))
    j = at(B, "complete", with_line("\t\tledger.BigLast"), ln, 16)
    check("and offers big.go's last function", "BigLastFn" in labels(j), labels(j)[:5])
    jreq("POST", f"/api/sets/{B}/end"); assist(B, "stop"); gone()


@sec("code help: Java (jdtls)")
def _():
    def attempt(prob="ledger-codebase"):
        a = jreq("POST", f"/api/catalog/{prob}/attempt", {"language": "java"})[1]["name"]; jreq("POST", f"/api/sets/{a}/start"); return a
    def assist(n, op, file="Main.java", text=None, line=0, col=0, **k):
        return jreq("POST", f"/api/sets/{n}/assist", {"op": op, "file": file, "text": text, "line": line, "col": col, **k})
    def ready(n, secs=30):
        for _ in range(int(secs * 2)):
            if assist(n, "complete", text="")[1].get("state") == "ready": return True
            time.sleep(0.5)
        return False
    def containers(): return subprocess.run(["docker", "ps", "-q", "--filter", "label=ilab.lsp=test"], capture_output=True, text=True).stdout.split()
    def gone(secs=5):
        for _ in range(secs * 2):
            if not containers(): return True
            time.sleep(0.5)
        return False
    seen = []
    def at(n, op, text, line, col, **k):
        s, j = assist(n, op, text=text, line=line, col=col, **k); seen.append(j); return j
    def labels(j): r = j.get("result") or {}; return [i["label"] for i in (r.get("items") if isinstance(r, dict) else r) or []]
    A = attempt()
    check("Java: code help reaches ready within 30 s", ready(A))
    main = req("GET", f"/api/sets/{A}/files/Main.java")[1].decode()
    ln = main.split("\n").index("        int n = f.length - 1;") + 1   # the line after it, inside handle()
    def with_line(extra): L = main.split("\n"); L.insert(ln, extra); return "\n".join(L)
    def prime(): at(A, "check", main, 0, 0)   # open Main.java in the server, then let the project finish importing
    def diags(text, file="Main.java", wait=20):   # a real answer for this text (jdtls publishes without a version), or None
        end = time.time() + wait
        while time.time() < end:
            d = at(A, "check", text, 0, 0, file=file).get("diagnostics")
            if d is not None: return d
            time.sleep(0.5)
    prime(); time.sleep(1)
    j = at(A, "complete", with_line("        l.bal"), ln, 8 + len("l.bal"))
    check("Java own type: l.bal lists balanceAt (Ledger.java never opened)", any(x.startswith("balanceAt(") for x in labels(j)), labels(j)[:6])
    j = at(A, "complete", "import java.util.*; " + with_line("        Collections.unmod"), ln, 8 + len("Collections.unmod"))
    check("Java stdlib: Collections.unmod lists unmodifiableList", any(x.startswith("unmodifiableList(") for x in labels(j)), labels(j)[:6])
    t = with_line("        Map<String, Long> m = new HashMap<>();\n        m.computeIf"); j = at(A, "complete", t, ln + 1, 8 + len("m.computeIf"))
    check("Java stdlib member: m.computeIf lists computeIfAbsent", any(x.startswith("computeIfAbsent(") for x in labels(j)), labels(j)[:6])
    j = at(A, "signature", with_line("        Math.max("), ln, 8 + len("Math.max("))
    check("Java signature help for Math.max(", any("max" in x.get("label", "") for x in (j.get("result") or {}).get("signatures", [])), j)
    t0 = time.time(); j = diags(with_line('        l.balance("a");'))
    d = [x for x in j or [] if x["range"]["start"]["line"] == ln]
    print(f"       Java: first underline after {time.time() - t0:.1f} s")
    check("Java: l.balance(\"a\") is underlined within 20 s, naming the method", len(d) == 1 and "balance" in d[0]["message"], (j, time.time() - t0))
    j = diags(main)
    check("Java: Main.java as shipped has no diagnostics (a real answer, not a timeout)", j == [], j)
    ex = req("GET", f"/api/sets/{A}/files/ExampleTest.java")[1].decode()
    check("Java: the untouched ExampleTest.java has no diagnostics (Expect resolves)", diags(ex, "ExampleTest.java") == [], None)
    L = main.split("\n"); hl = next(i for i, x in enumerate(L) if "Ledger l = new Ledger();" in x)
    for _ in range(20):
        hv = json.dumps(at(A, "hover", main, hl, L[hl].index("new Ledger") + 6).get("result"))
        if "Ledger" in hv: break
        time.sleep(0.5)
    check("Java hover names Ledger", "Ledger" in hv, hv[:200])
    led = req("GET", f"/api/sets/{A}/files/Ledger.java")[1].decode()
    req("PUT", f"/api/sets/{A}/files/Ledger.java", led.rstrip()[:-1] + "\n    public int zzProbe() { return 1; }\n}\n")
    time.sleep(1)
    j = at(A, "complete", with_line("        l.zzPr"), ln, 8 + len("l.zzPr"))
    check("Java: a method saved in Ledger.java shows in Main.java's suggestions (Main.java not resent)", any(x.startswith("zzProbe(") for x in labels(j)), labels(j)[:6])
    pr = "public class Probe {\n    HiddenT\n    void f() { test_p1_ }\n}\n"
    j1 = at(A, "complete", pr, 1, 11, file="Probe.java"); j2 = at(A, "complete", pr, 2, 21, file="Probe.java")
    bad = [x for x in labels(j1) + labels(j2) if x.startswith(("HiddenTest", "test_p1_"))]
    check("Java: hidden test names are never offered", not bad, bad)
    blob = json.dumps(seen)
    check("Java: no container path, .hidden, file:// or link in any result", not any(m in blob for m in ("/tmp/w", ".hidden", "file://", "](")), [m for m in ("/tmp/w", ".hidden", "file://", "](") if m in blob])
    req("PUT", f"/api/sets/{A}/files/build.gradle", "plugins { id 'java' }\nthis is not gradle {{{\n")
    j = at(A, "check", main, 0, 0)
    check("Java: a build.gradle the candidate creates is ignored (no new underline, no Gradle start)", j.get("diagnostics") == [] and "gradle" not in subprocess.run(["docker", "ps", "--format", "{{.Image}}"], capture_output=True, text=True).stdout, j)
    ids = containers()
    check("Java: exactly one language-server container", len(ids) == 1, ids)
    if len(ids) == 1:
        o = json.loads(subprocess.run(["docker", "inspect", ids[0]], capture_output=True, text=True).stdout)[0]
        hc = o["HostConfig"]
        check("Java: container is locked down", hc["NetworkMode"] == "none" and hc["ReadonlyRootfs"] is True and hc["Memory"] == 536870912
              and hc["MemorySwap"] == 536870912 and hc["NanoCpus"] == 2000000000 and hc["PidsLimit"] == 256 and hc["CapDrop"] == ["ALL"]
              and "no-new-privileges" in " ".join(hc["SecurityOpt"]) and not hc["PortBindings"] and not o["Mounts"] and not o["NetworkSettings"]["Ports"], hc)
        peak = subprocess.run(["docker", "exec", ids[0], "cat", "/sys/fs/cgroup/memory.peak"], capture_output=True, text=True).stdout.strip()
        mb = int(peak) / 2**20 if peak.isdigit() else None
        print(f"       jdtls peak memory in {A}: {mb and round(mb)} MB (limit 512)")
        check("Java: peak memory under 512 MB and no OOM kill", mb is not None and mb < 500 and json.loads(subprocess.run(["docker", "inspect", ids[0]], capture_output=True, text=True).stdout)[0]["State"]["OOMKilled"] is False, mb)
    check("Java: stop: the container is gone within 5 s", assist(A, "stop")[0] == 200 and gone())
    jreq("POST", f"/api/sets/{A}/end"); jreq("DELETE", f"/api/sets/{A}"); gone()
    # every Java starter in the catalog: 0 errors on untouched files (a planted bug must never get an underline; no false positives)
    probs = [p for p in jreq("GET", "/api/catalog")[1]["problems"] if "java" in p["languages"] and p.get("source") != "custom"]
    total = {}
    for pr_ in probs:
        a = attempt(pr_["id"])
        if not ready(a, 40): check(f"Java {pr_['id']}: code help ready", False); continue
        files = [f for f in jreq("GET", f"/api/sets/{a}/state")[1]["files"] if f.endswith(".java")]
        bad = {}
        for f in files:
            txt = req("GET", f"/api/sets/{a}/files/{f}")[1].decode(); d = None
            for _ in range(8):
                d = at(a, "check", txt, 0, 0, file=f).get("diagnostics")
                if d is not None: break
                time.sleep(1)
            if d is None or d: bad[f] = [x["message"] for x in d] if d else "no answer"
        total[pr_["id"]] = (len(files), len(bad))
        check(f"Java {pr_['id']} ({pr_['round']}): {len(files)} untouched starter files, 0 diagnostics", not bad, bad)
        jreq("POST", f"/api/sets/{a}/end"); assist(a, "stop")
    print(f"       Java starters checked: {len(total)} problems, {sum(v[0] for v in total.values())} files, {sum(v[1] for v in total.values())} with diagnostics")
    gone()

print(f"\n{'ALL PASSED' if not fails else f'{fails} FAILED'}")
sys.exit(1 if fails else 0)
