"""End grades the final/ snapshot, not work/ (an edit can land in work/ after the close). No Docker: grading is stubbed.
Run: python3 tests/unit/test_final_grade.py"""

import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import rounds  # noqa: E402


def write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(data if isinstance(data, str) else json.dumps(data))


d = os.path.join(os.environ["ILAB_DATA"], "sets", "s")
write(
    f"{d}/manifest.json", {"name": "s", "language": "python", "minutes": 30, "hidden_tests": ".hidden/tests_hidden.py"}
)
write(f"{d}/.hidden/tests_hidden.py", "def test_x(): pass\n")
write(f"{d}/problem.md", "# s\n")
now = time.time()
write(
    f"{d}/session.json",
    {"start": now - 60, "minutes": 30, "events": [], "ended": now - 10, "unlocked": ["test_"], "revealed": []},
)
write(f"{d}/final/sol.py", "A = 1\n")  # the code at the close
write(f"{d}/work/sol.py", "B = 2\n")  # an autosave that landed after the close

seen = []
rounds.grade.grade = lambda files, *a, **k: (
    seen.append(files["sol.py"]) or {"status": "graded", "passed": 1, "total": 1}
)
rounds.end("s")
assert seen == [b"A = 1\n"], seen
print("PASS end grades final/, not work/")
