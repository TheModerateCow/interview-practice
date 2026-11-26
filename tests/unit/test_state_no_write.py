"""GET /state (store.state) writes session.json only when something changed, not on every 5 s poll.
Run: python3 tests/unit/test_state_no_write.py"""
import json, os, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import store  # noqa: E402


def write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f: f.write(data if isinstance(data, str) else json.dumps(data))


d = os.path.join(os.environ["ILAB_DATA"], "sets", "s")
# part 2 reveals itself at 5 min left; the round has 30 min, 1 min used
write(f"{d}/manifest.json", {"name": "s", "minutes": 30, "reveal": [{"file": ".hidden/p2.md", "or_minutes_left": 5}]})
write(f"{d}/problem.md", "# s\n")
write(f"{d}/.hidden/p2.md", "part 2\n")
write(f"{d}/work/a.py", "")
write(f"{d}/session.json", {"start": time.time() - 60, "minutes": 30, "events": [], "ended": None, "unlocked": ["test_"], "revealed": []})

saves = []
real = store.jsave
store.jsave = lambda p, obj: saves.append(p) or real(p, obj)

for _ in range(3): store.state("s")
assert saves == [], saves
print("PASS polling a running round writes nothing")

# 26 min used -> 4 min left: the time reveal fires once, then polls are quiet again
s = json.load(open(f"{d}/session.json")); s["start"] = time.time() - 26 * 60; real(f"{d}/session.json", s)
for _ in range(3): store.state("s")
assert len(saves) == 1 and store.session("s")["revealed"] == [".hidden/p2.md"], (saves, store.session("s"))
print("PASS a time reveal is saved once")
