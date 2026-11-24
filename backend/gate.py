import json,os,shutil,subprocess,sys,tempfile
# usage: python3 gate.py <set_dir>                      check the set
#        python3 gate.py <set_dir> --build-starter      write starter/ = reference/ + every bugs.json edit
#        python3 gate.py <set_dir> --tdd <their_tests>  score candidate tests against reference + mutants
d=os.path.abspath(sys.argv[1]); ref=os.path.join(d,"reference")
H=next((os.path.join(d,n) for n in ("tests_hidden.py","hidden_test.go","HiddenTest.java","hidden.test.ts","hidden.test.js") if os.path.exists(os.path.join(d,n))),None)
assert H, "no hidden tests file: tests_hidden.py / hidden_test.go / HiddenTest.java / hidden.test.ts / hidden.test.js"
G=os.path.join(os.path.dirname(os.path.abspath(__file__)),"grade.py")
def load(n):
    p=os.path.join(d,n); return json.load(open(p)) if os.path.exists(p) else []
def grade(src,tests=H,k=None):
    r=subprocess.run([sys.executable,G,src,tests,"--names"]+(["-k",k] if k else []),capture_output=True,text=True)
    return json.loads(r.stdout.strip().splitlines()[-1])
def ok(g): return g.get("status")=="graded" and g["passed"]==g["total"] and g["total"]>0
def killed(g): return g.get("status") in ("did not finish","could not be graded") or (g.get("status")=="graded" and g["passed"]<g["total"])
def apply(edits):
    t=tempfile.mkdtemp(); shutil.copytree(ref,t,dirs_exist_ok=True)
    for e in edits:
        p=os.path.join(t,e["file"]); s=open(p).read()
        assert s.count(e["old"])==1, f"OLD not unique/absent in {e['file']}: {e['old'][:60]!r}"
        open(p,"w").write(s.replace(e["old"],e["new"]))
    return t
a=sys.argv[2:]
if "--build-starter" in a:
    t=apply(load("bugs.json")); s=os.path.join(d,"starter"); shutil.rmtree(s,ignore_errors=True); shutil.copytree(t,s)
    print("starter written:",s); sys.exit()
if "--tdd" in a:
    their=os.path.abspath(a[a.index("--tdd")+1]); g=grade(ref,their)
    print("their tests pass on reference:",ok(g),{k:g.get(k) for k in ("status","passed","total","failed","last_error","last_line")})
    if not ok(g): print("A test that fails on correct code is a wrong test; mutation score not counted."); sys.exit()
    hit=[m["label"] for m in load("mutants.json") if killed(grade(apply([m]),their))]
    miss=[m["label"] for m in load("mutants.json") if m["label"] not in hit]
    print(f"mutants killed: {len(hit)}/{len(load('mutants.json'))}"); print("killed:",hit); print("survived:",miss); sys.exit()
fails=0
def check(name,cond):
    global fails; fails+=not cond; print(("PASS " if cond else "FAIL ")+name)
for i in range(3): check(f"reference passes every hidden test (run {i+1}/3)",ok(grade(ref)))
st=os.path.join(d,"starter"); bugs=load("bugs.json")
if os.path.isdir(st):
    g=grade(st)
    if bugs: check("starter fails at least one hidden test",killed(g))
    else: check("hand-written starter passes no hidden test (no free points for stubs)",g.get("status")!="graded" or g["passed"]==0)
for m in load("mutants.json"): check(f"mutant killed [{m.get('k') or 'all'}]: {m['label']}",killed(grade(apply([m]),k=m.get("k"))))
for b in bugs:
    check(f"bug caught alone [{b.get('k') or 'all'}]: {b['label']}",killed(grade(apply([b]),k=b.get("k"))))
    iso={"test_p1_":"not test_p1_","test_p2_":"test_p1_","test_p3_":"not test_p3_"}.get(b.get("k"))
    if iso: check(f"bug isolated [{iso}] still passes: {b['label']}",ok(grade(apply([b]),k=iso)))
print("GATE PASS" if fails==0 else f"GATE FAIL ({fails})")
