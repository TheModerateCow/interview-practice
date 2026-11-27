"""GET /api/sets and GET /state give the same left_s (one rule, store.left_s). Run: python3 tests/unit/test_sets_listing.py"""
import json, os, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import catalog, store  # noqa: E402


def write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f: f.write(data if isinstance(data, str) else json.dumps(data))


sets = os.path.join(os.environ["ILAB_DATA"], "sets")
for n, start in (("a-running", time.time() - 60.5), ("b-ready", None)):   # 60.5 s used: 1739.5 s left
    write(f"{sets}/{n}/manifest.json", {"name": n, "title": n, "minutes": 30, "problem": "p"})
    write(f"{sets}/{n}/problem.md", "#\n"); write(f"{sets}/{n}/work/a.py", "")
    if start: write(f"{sets}/{n}/session.json", {"start": start, "minutes": 30, "events": [], "ended": None, "unlocked": [], "revealed": []})
write(f"{sets}/Not-A-Set/manifest.json", {})   # invalid name: skipped

rows = {r["name"]: r for r in catalog.sets()["sets"]}
assert list(rows) == ["a-running", "b-ready"], rows
assert rows["b-ready"]["left_s"] is None and rows["b-ready"]["problem"] == "p"
listed, polled = rows["a-running"]["left_s"], store.state("a-running")["left_s"]
assert abs(listed - polled) < 0.05, (listed, polled)
print("PASS /api/sets and /state agree on left_s")
