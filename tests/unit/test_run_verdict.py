"""rounds.run: the Run verdict from the stdin box and the testcases (runner stubbed, no Docker).
Run: python3 tests/unit/test_run_verdict.py"""
import json, os, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import rounds  # noqa: E402

d = os.path.join(os.environ["ILAB_DATA"], "sets", "s")
os.makedirs(f"{d}/work")
open(f"{d}/work/main.py", "w").close()
json.dump({"name": "s", "minutes": 30, "run_entry": "main.py",
           "testcases": [{"stdin": "1", "expected": "2\n"}, {"stdin": "5", "expected": "6"}]}, open(f"{d}/manifest.json", "w"))
json.dump({"start": time.time(), "minutes": 30, "events": [], "ended": None, "unlocked": [], "revealed": []}, open(f"{d}/session.json", "w"))


def case(stdout, verdict="Accepted"): return {"stdout": stdout, "stderr": "", "exit": 0, "ms": 1, "truncated": False, "verdict": verdict}


def run(stdin, *cases):
    rounds.runner.run = lambda lang, files, entry, stdins: {"compile": None, "cases": list(cases), "memory_kb": 1}
    return rounds.run("s", {"file": "main.py", "stdin": stdin})


assert run("", case(""), case("2  \n\n"), case("6"))["verdict"] == "Accepted"        # trailing spaces/lines ignored
assert run("", case(""), case("2"), case("7"))["verdict"] == "Wrong Answer"
assert run("", case("", "Runtime Error"), case("2"), case("6"))["verdict"] == "Accepted"   # empty box: testcases decide
assert run("x", case("", "Runtime Error"), case("2"), case("6"))["verdict"] == "Runtime Error"   # typed stdin counts
assert run("", case(""), case("2", "Time Limit Exceeded"), case("6"))["verdict"] == "Time Limit Exceeded"
r = run("", case(""), case("2"), case("7"))
assert [t["pass"] for t in r["testcases"]] == [True, False] and r["testcases"][1]["expected"] == "6"
assert json.load(open(f"{d}/session.json"))["events"][-1][1] == "run main.py: Wrong Answer, 1/2 cases"
print("PASS run verdict: testcases, whitespace, the stdin box, and the event log")

rounds.runner.run = lambda *a: {"compile": {"ok": False, "log": "boom"}, "cases": [], "memory_kb": None}
assert rounds.run("s", {"file": "main.py"})["verdict"] == "Compile Error"
print("PASS compile error -> Compile Error")
