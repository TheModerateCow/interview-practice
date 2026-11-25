#!/usr/bin/env python3
"""Acceptance tests against the isolated test stack (tests/stack.sh up: http://127.0.0.1:8766). stdlib only."""
import glob, http.client, io, json, os, random, socket, subprocess, sys, time, traceback, zipfile

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
    m = {"format": "interview-set/1", "name": name, "title": "T " + name, "round": "dsa", "language": lang,
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
 "javascript": ("main.js", {"main.js": "const l=require('fs').readFileSync(0,'utf8').split('\\n')[0].trim();\nconsole.log(l?l.toUpperCase():'hello');\n"}, None),
 "typescript": ("main.ts", {"main.ts": "import fs from 'node:fs';\nconst l: string = fs.readFileSync(0,'utf8').split('\\n')[0].trim();\nconsole.log(l ? l.toUpperCase() : 'hello');\n"},
                "const x: number = ;\n"),
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
    r = runfile(n, entry, "xyz\n")
    check(f"{lang}: stdin transform", r["stdin_case"].get("stdout", "").strip() == "XYZ", r)
    if broken:
        s, _ = req("PUT", f"/api/sets/{n}/files/{entry}", broken)
        r = runfile(n, entry, "\n")
        if lang == "typescript":
            check("typescript: syntax error is not Accepted", r["verdict"] != "Accepted", r["verdict"])
        else:
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
    check(f"{label}: submit never leaks failed names", '"failed"' not in json.dumps(sub), "")
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
    for f in ("tools/pack.py", "backend/gate.py"):
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
        check(f"compose port {svc} {port} publishes nothing", r.stdout.strip() in ("", ":0"), r.stdout + r.stderr)


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


print(f"\n{'ALL PASSED' if not fails else f'{fails} FAILED'}")
sys.exit(1 if fails else 0)
