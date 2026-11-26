"""Older on-disk shapes are upgraded on load, in one place (store.upgrade_session / upgrade_manifest).
Run: python3 tests/unit/test_session_upgrade.py"""
import json, os, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import catalog, rounds, store  # noqa: E402

sets = os.path.join(os.environ["ILAB_DATA"], "sets")


def put(n, manifest, session=None):
    os.makedirs(f"{sets}/{n}/work", exist_ok=True)
    open(f"{sets}/{n}/problem.md", "w").write("#\n")
    json.dump(manifest, open(f"{sets}/{n}/manifest.json", "w"))
    if session: json.dump(session, open(f"{sets}/{n}/session.json", "w"))


# v0: End pressed 1 min after the deadline stored the press time; "hints" was always written and never read
start = time.time() - 40 * 60
put("old", {"name": "old", "minutes": 30, "preset": "two-sum"},
    {"start": start, "minutes": 30, "hints": [], "events": [], "ended": start + 31 * 60, "unlocked": [], "revealed": []})
s = store.session("old")
deadline = start + 30 * 60
assert s["v"] == 1 and "hints" not in s and s["ended"] == deadline, s
assert store.late(s, deadline + 30)   # a Submit 30 s after the deadline is "after time" (v0 said it wasn't)
assert store.state("old")["status"] == "ended"
print("PASS v0 session: hints dropped, a late End clamped to the deadline")

assert store.manifest("old")["problem"] == "two-sum" and "preset" not in store.manifest("old")
assert [a[0] for a in catalog.attempts()["two-sum"]] == ["old"]
print('PASS a "preset" attempt is read as "problem"')

put("new", {"name": "new", "title": "new", "minutes": 30})
rounds.start("new")
s = json.load(open(f"{sets}/new/session.json"))
assert s["v"] == store.SESSION_V and "hints" not in s, s
assert store.upgrade_session(dict(s)) == s   # the current shape is left alone
print("PASS a new session is written at the current version")
