"""A runner container whose attach fails is force-removed, not just killed (it never started, so AutoRemove never
fires). No Docker: the Docker API is stubbed. Run: python3 tests/unit/test_container_cleanup.py"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from sandbox import runner  # noqa: E402

calls = []


def api(method, path, body=None, **k):
    calls.append((method, path))
    return {"Id": "c1"} if path == "/containers/create" else None


def attach(cid, timeout):
    raise runner.DockerError("attach: connection closed")


runner.api, runner._attach = api, attach
try:
    runner.container("python", {"a.py": b""}, "true", 5)
    raise SystemExit("FAIL: expected DockerError")
except runner.DockerError:
    pass
assert ("DELETE", "/containers/c1?force=1") in calls, calls
print("PASS failed attach force-removes the created container")
