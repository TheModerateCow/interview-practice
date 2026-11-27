"""Every language the sandbox runs, one class each: file extensions, the Run build step and command, and the
hidden-test command with its report parser. runner.run and grade.grade hold no language knowledge; they call these.
Adding a language: one class here, added to TOOLCHAINS, plus its image in runner.IMAGES (with the other container
images). tools/pack.py and gate.py keep their own lists because SKILL.md embeds them; tests/unit/test_toolchains.py
fails if those drift from TOOLCHAINS."""
import json, os, re, shlex, xml.etree.ElementTree as ET

q = shlex.quote
REPORT = " > /tmp/out/log 2>&1; echo $? > /tmp/out/rc\n"   # every grade command logs here and leaves its exit code


def _s(b): return (b if isinstance(b, str) else (b or b"").decode(errors="replace"))


def lastline(text, marks=("E ", "FAIL", "panic:", "Error", "error")):
    ls = [l.strip() for l in text.splitlines() if l.strip()]
    hit = [l for l in ls if l.startswith(marks)]
    return (hit or ls or [""])[-1][:300]


def first_compile_error(text, rx):
    """The first compiler error line ("x.go:12:5: f.Foo undefined") says more than the trailing FAIL / "1 error"."""
    return next((l.strip()[:300] for l in text.splitlines() if re.search(rx, l)), None)


def junit(xml_bytes, skip_skipped=False):
    res = {}
    for c in ET.fromstring(xml_bytes).iter("testcase"):
        if skip_skipped and c.find("skipped") is not None: continue
        f = c.find("failure") if c.find("failure") is not None else c.find("error")
        res[c.get("name")] = None if f is None else (f.get("message") or "failed")[:300]
    return res


def log_of(out): return _s(out.get("log")) + _s(out.get("err"))
def rcs_of(out): return _s(out.get("rc")).split()
def rc_of(out):
    rcs = rcs_of(out)
    return int(rcs[0]) if rcs and rcs[0].lstrip("-").isdigit() else None
def ungradable(text): return {"status": "could not be graded", "last_line": text}


class Toolchain:
    name, exts = None, ()
    grades = True        # has a hidden-test runner (Submit / My tests); False: Run only
    test_start = None    # Go/Java: line -> (test name, the line that ends it), so grade.prune can drop unselected tests


    def build(self, entry, files):
        """Run's compile step: (script, files) for one build container, or None to run the sources directly."""
        return None

    def run_cmd(self, entry, files): raise NotImplementedError

    def grade_sh(self, files, tests, k, pat, neg):
        """-> (shell script, files) that runs the test files `tests` under the -k filter and leaves a report in /tmp/out."""
        raise NotImplementedError

    def parse(self, out, k, pat, neg):
        """-> ({test name: error or None}, None), or (None, a status dict) when there is nothing to count."""
        raise NotImplementedError


class Python(Toolchain):
    name, exts = "python", (".py",)

    def run_cmd(self, entry, files): return f"python3 {q(entry)}"

    def grade_sh(self, files, tests, k, pat, neg):
        tq = " ".join(q(t) for t in tests)
        return f"python3 -m pytest -q -p no:cacheprovider {tq} --junitxml=/tmp/out/_r.xml" + (f" -k {q(k)}" if k else "") + REPORT, files

    def parse(self, out, k, pat, neg):
        rc = rc_of(out)
        if rc == 5: return None, {"status": "no tests selected", "k": k}
        if "_r.xml" not in out or rc in (2, 3, 4): return None, ungradable(lastline(log_of(out) or _s(out.get("_harness.log"))))
        return junit(out["_r.xml"]), None


class Node(Toolchain):
    def grade_sh(self, files, tests, k, pat, neg):
        tq = " ".join(q(t) for t in tests)
        flt = f" {'--test-skip-pattern' if neg else '--test-name-pattern'} {q(re.escape(pat))}" if pat else ""
        return ("node --disable-warning=ExperimentalWarning --test --test-reporter=junit "
                f"--test-reporter-destination=/tmp/out/_r.xml{flt} {tq}" + REPORT), files

    def parse(self, out, k, pat, neg):
        if "_r.xml" not in out: return None, ungradable(lastline(log_of(out) or _s(out.get("_harness.log"))))
        res = junit(out["_r.xml"], skip_skipped=True)
        if not res and rc_of(out) != 0: return None, ungradable(lastline(log_of(out)))
        return res, None


class JavaScript(Node):
    name, exts = "javascript", (".js", ".mjs")
    def run_cmd(self, entry, files): return f"node {q(entry)}"


class TypeScript(Node):
    name, exts = "typescript", (".ts",)
    def run_cmd(self, entry, files): return f"node --disable-warning=ExperimentalWarning {q(entry)}"


class Go(Toolchain):
    name, exts = "go", (".go",)

    def test_start(self, line):
        m = re.match(r"func (Test\w*)\(", line)   # gofmt: a test ends at the next "}" in column 0
        return (m.group(1), "}") if m else None

    def build(self, entry, files):
        d = q(os.path.dirname(entry) or ".")
        script = f"[ -f go.mod ] || go mod init ilab >/dev/null 2>&1\ngo build -o /tmp/out/prog ./{d} > /tmp/out/compile.log 2>&1\nrc=$?\n"
        # a non-main package builds to an archive, not a program: say so instead of executing it
        script += (f"if [ $rc = 0 ]; then p=$(go list -f '{{{{.Name}}}}' ./{d}); [ \"$p\" = main ] || {{ rc=1; "
                   "echo \"Nothing to run: this code is a library (package $p), not a program with package main and func main(). "
                   "Test it with My tests (add a file ending in _test.go) or Submit.\" > /tmp/out/compile.log; }; fi\n"
                   "echo $rc > /tmp/out/compile.rc\n")
        return script, files

    def run_cmd(self, entry, files): return "/tmp/w/prog"

    def grade_sh(self, files, tests, k, pat, neg):
        # One process per test: a panic in one test (e.g. a stub's panic("not implemented")) can't stop the others.
        # Compiled once; test2json keeps the `go test -json` event format parse() reads.
        sel = f" | grep {'-viF' if neg else '-iF'} -- {q(pat)}" if pat else ""
        return ("[ -f go.mod ] || go mod init ilab >/dev/null 2>&1\n"
                "go test -list '.*' . > /tmp/out/list 2>&1; echo $? > /tmp/out/list.rc\n"
                "go test -c -o /tmp/t.test . 2>/tmp/out/err\n"
                f"for n in $(grep '^Test' /tmp/out/list{sel}); do go tool test2json -p ilab -t /tmp/t.test -test.v=test2json "
                "-test.run \"^$n\\$\" >> /tmp/out/log 2>>/tmp/out/err; done\necho 0 > /tmp/out/rc\n"), files

    def parse(self, out, k, pat, neg):
        lst = _s(out.get("list"))
        if _s(out.get("list.rc")).strip() != "0":
            return None, ungradable(first_compile_error(lst, r"\.go:\d+:\d+: ") or lastline(lst or _s(out.get("_harness.log"))))
        tnames = [l for l in lst.split() if l.startswith("Test")]
        if pat: tnames = [n for n in tnames if (pat.lower() in n.lower()) != neg]
        res, outs = {}, {}
        for l in _s(out.get("log")).splitlines():
            try: e = json.loads(l)
            except ValueError: continue
            n = e.get("Test")
            if not n or "/" in n: continue
            if e.get("Action") == "output" and n in tnames: outs.setdefault(n, []).append(e.get("Output", "").strip())
            if e.get("Action") in ("pass", "fail"):
                res[n] = None if e["Action"] == "pass" else next((o for o in outs.get(n, []) if o.startswith("panic:") or "_test.go:" in o), "failed")[:300]
        for n in tnames: res.setdefault(n, "did not run (earlier panic or crash)")
        return res, None


class Java(Toolchain):
    name, exts = "java", (".java",)
    EXPECT = r'''
public class Expect {
  public static void eq(Object exp, Object act){ if(exp==null?act!=null:!exp.equals(act)) throw new AssertionError("expected "+exp+" but got "+act); }
  public static void isTrue(boolean b, String msg){ if(!b) throw new AssertionError(msg); }
  public static void isTrue(boolean b){ isTrue(b,"expected true"); }
  public static void raises(Class<? extends Throwable> k, Runnable r){ try{ r.run(); }catch(Throwable x){ if(k.isInstance(x)) return; throw new AssertionError("expected "+k.getSimpleName()+" but got "+x); } throw new AssertionError("expected "+k.getSimpleName()+" but nothing was thrown"); }
}
'''
    RUNNER = r'''
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

    @staticmethod
    def main_class(src, path):
        m = re.search(r"^\s*package\s+([\w.]+)\s*;", _s(src), re.M)
        cls = os.path.splitext(os.path.basename(path))[0]
        return f"{m.group(1)}.{cls}" if m else cls

    def test_start(self, line):
        m = re.match(r"(\s*)(?:(?:public|private|protected)\s+)?static\s+void\s+(test\w*)\s*\(\s*\)", line)
        return (m.group(2), m.group(1) + "}") if m else None   # a test ends at the "}" with its own indent

    def build(self, entry, files):
        files = dict(files); files.setdefault("Expect.java", self.EXPECT)
        return "javac -d /tmp/out/classes $(find . -name '*.java') > /tmp/out/compile.log 2>&1\necho $? > /tmp/out/compile.rc\n", files

    def run_cmd(self, entry, files): return f"java -cp /tmp/w/classes {q(self.main_class(files[entry], entry))}"

    def grade_sh(self, files, tests, k, pat, neg):
        files = dict(files); files["Runner.java"] = self.RUNNER; files["Expect.java"] = self.EXPECT
        arg = (f" {q(pat)}" + (" not" if neg else "")) if pat else ""
        sh = ("javac -d /tmp/_out $(find . -name '*.java') > /tmp/out/clog 2>&1; echo $? > /tmp/out/crc\n"
              "[ \"$(cat /tmp/out/crc)\" = 0 ] || exit 0\n: > /tmp/out/log\n")
        for t in tests:
            sh += f"java -cp /tmp/_out Runner {q(self.main_class(files[t], t))}{arg} >> /tmp/out/log 2>&1; echo $? >> /tmp/out/rc\n"
        return sh, files

    def parse(self, out, k, pat, neg):
        clog = _s(out.get("clog"))
        if _s(out.get("crc")).strip() != "0":
            return None, ungradable(first_compile_error(clog, r"\.java:\d+: error:") or lastline(clog or _s(out.get("_harness.log")), ("error",)))
        res = {}
        for l in _s(out.get("log")).splitlines():
            m = re.match(r"(PASS|FAIL) (\S+)(?: \| (.*))?", l)
            if m: res[m.group(2)] = None if m.group(1) == "PASS" else (m.group(3) or "failed")[:300]
        if not res and any(r != "0" for r in rcs_of(out)): return None, ungradable(lastline(log_of(out)))
        return res, None


class Gcc(Toolchain):
    grades = False
    CC = None

    def build(self, entry, files):
        return f"{self.CC} -o /tmp/out/prog {q(entry)} -lm > /tmp/out/compile.log 2>&1\necho $? > /tmp/out/compile.rc\n", files

    def run_cmd(self, entry, files): return "/tmp/w/prog"


class C(Gcc): name, exts, CC = "c", (".c",), "gcc -O2 -std=c17"
class Cpp(Gcc): name, exts, CC = "cpp", (".cpp", ".cc"), "g++ -O2 -std=c++17"


TOOLCHAINS = {t.name: t for t in (Python(), Go(), Java(), C(), Cpp(), JavaScript(), TypeScript())}
BY_EXT = {e: t for t in TOOLCHAINS.values() for e in t.exts}


def for_file(path):
    """The toolchain that runs this file (by extension), or None."""
    return BY_EXT.get(os.path.splitext(path)[1])
