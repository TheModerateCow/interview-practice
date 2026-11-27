"""runner: Docker stream demux, and how each Run case's exit code / OOM / timeout becomes a verdict. Docker is stubbed.
Run: python3 tests/unit/test_runner_verdicts.py"""

import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from sandbox import runner  # noqa: E402


def frame(kind, data):
    return bytes([kind, 0, 0, 0]) + struct.pack(">I", len(data)) + data


assert runner._demux(frame(1, b"out") + frame(2, b"err") + frame(1, b"!")) == (b"out!", b"err")
assert runner._demux(frame(1, b"ab")[:-1]) == (b"a", b"")  # a cut-off last frame keeps what arrived
print("PASS demux splits stdout/stderr frames")

# one case per row: (files in /tmp/out for that case, container timed out) -> verdict
CASES = [
    ({"rc": b"0"}, False, "Accepted"),
    ({"rc": b"1"}, False, "Runtime Error"),
    ({"rc": b"124"}, False, "Time Limit Exceeded"),
    ({"rc": b"0", "oom": b""}, False, "Memory Limit Exceeded"),
    ({}, True, "Time Limit Exceeded"),  # no exit code: the whole container ran out of time
    ({}, False, "Runtime Error"),  # no exit code otherwise: killed
    ({"rc": b"141", "out": b"x" * (runner.OUT_CAP + 1)}, False, "Accepted"),
]  # SIGPIPE after the output cap
for i, (files, to, want) in enumerate(CASES):
    out = {f"0.{k}": v for k, v in files.items()} | {"peak": b"2048"}
    runner.container = lambda *a, **k: (out, to)
    r = runner.run("python", {"main.py": b""}, "main.py", [""])
    c = r["cases"][0]
    assert c["verdict"] == want, (i, files, to, c)
    assert r["compile"] is None and r["memory_kb"] == 2
print("PASS run: exit code / OOM / timeout -> verdict")

runner.container = lambda *a, **k: ({"compile.rc": b"1", "compile.log": b"x.go:1:1: oops"}, False)
r = runner.run("go", {"main.go": b""}, "main.go", [""])
assert r == {"compile": {"ok": False, "log": "x.go:1:1: oops"}, "cases": [], "memory_kb": None}, r
print("PASS run: a failed compile stops before any case")
