"""A code-help container whose attach fails is force-removed, not just killed (it never started, so AutoRemove never
fires). Docker is stubbed. Run: python3 tests/unit/test_lsp_cleanup.py"""

import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
from sandbox import lsp, runner  # noqa: E402

d = os.path.join(os.environ["ILAB_DATA"], "sets", "s")
os.makedirs(f"{d}/work")
open(f"{d}/work/main.py", "w").close()
json.dump({"name": "s", "round": "codebase"}, open(f"{d}/manifest.json", "w"))

calls = []


def api(method, path, body=None, **k):
    calls.append((method, path))
    return {"Id": "c1"} if path == "/containers/create" else None


def attach(cid, timeout):
    raise runner.DockerError("attach: connection closed")


runner.api, runner._attach = api, attach
s = lsp.Session("s", "python")
for _ in range(50):
    if s.state == "unavailable":
        break
    time.sleep(0.1)
assert s.state == "unavailable", s.state
assert ("DELETE", "/containers/c1?force=1") in calls, calls
print("PASS a code-help container whose attach fails is force-removed")
