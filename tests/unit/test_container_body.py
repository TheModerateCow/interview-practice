"""The container a toolchain runs in: Go gets its env and the shared build-cache volume, the other languages neither.
runner.container() reads these from the toolchain; it names no language. Docker is stubbed.
Run: python3 tests/unit/test_container_body.py"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from sandbox import runner  # noqa: E402
from sandbox.toolchains import TOOLCHAINS  # noqa: E402

bodies = {}


def api(method, path, body=None, **k):
    if path == "/containers/create":
        bodies[current] = body
        return {"Id": "c1"}
    return None


def attach(cid, timeout):
    raise runner.DockerError("stop here: only the create body matters")


runner.api, runner._attach = api, attach
for current in TOOLCHAINS:
    try:
        runner.container(current, {"a": b""}, "true", 5, env=["X=1"])
    except runner.DockerError:
        pass

go = bodies["go"]
assert go["HostConfig"]["Mounts"] == [
    {"Type": "volume", "Source": runner.TOOLCHAINS["go"].cache[0], "Target": "/gocache"}
]
assert go["Env"][-6:] == [
    "X=1",
    "GOTOOLCHAIN=local",
    "GOFLAGS=-mod=mod",
    "GOCACHE=/gocache",
    "GOPATH=/tmp/gopath",
    "CGO_ENABLED=0",
]
for lang in set(TOOLCHAINS) - {"go"}:
    assert "Mounts" not in bodies[lang]["HostConfig"] and bodies[lang]["Env"][-1] == "X=1", (lang, bodies[lang])
print("PASS Go gets its env and build-cache volume from its toolchain; other languages get neither")
