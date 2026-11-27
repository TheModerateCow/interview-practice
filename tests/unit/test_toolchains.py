"""sandbox/toolchains.py is the one list of languages the sandbox runs. The copies that must stay separate (tools/pack.py
and backend/sandbox/gate.py are embedded byte for byte in SKILL.md) and runner.IMAGES must agree with it.
Run: python3 tests/unit/test_toolchains.py"""

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pack  # noqa: E402
from sandbox import grade, runner  # noqa: E402
from sandbox.toolchains import TOOLCHAINS, for_file  # noqa: E402

grading = {n for n, t in TOOLCHAINS.items() if t.grades}
assert set(pack.LANGS) == set(TOOLCHAINS), set(pack.LANGS) ^ set(TOOLCHAINS)
for n, ext in pack.LANGS.items():  # pack: the hidden-tests extension, None for Run-only languages
    assert (ext is None) == (n not in grading) and (ext is None or ext in TOOLCHAINS[n].exts), (n, ext)
print("PASS tools/pack.py LANGS agrees with TOOLCHAINS")

src = open(os.path.join(ROOT, "backend/sandbox/gate.py")).read()
call = next(
    n
    for n in ast.walk(ast.parse(src))
    if isinstance(n, ast.Tuple)
    and all(isinstance(e, ast.Constant) for e in n.elts)
    and any(str(e.value).startswith("tests_hidden") for e in n.elts)
)
gate_names = [e.value for e in call.elts]
assert {grade.LANG_BY_EXT[os.path.splitext(f)[1]] for f in gate_names} == grading, gate_names
print("PASS gate.py's hidden-test names cover exactly the grading toolchains")

assert set(runner.IMAGES) == set(TOOLCHAINS), set(runner.IMAGES) ^ set(TOOLCHAINS)
for n, t in TOOLCHAINS.items():
    assert t.name == n and t.exts and all(for_file("x" + e) is t for e in t.exts)
    assert t.run_cmd("main" + t.exts[0], {"main" + t.exts[0]: b"class Main {}"})
    if t.grades:
        assert t.grade_sh({"t": b""}, ["t"], None, None, False)[0]
print(
    f"PASS {len(TOOLCHAINS)} toolchains: each has an image, extensions, a Run command and (if it grades) a test command"
)

from sandbox import lsp  # noqa: E402

for lang, cfg in lsp.SERVERS.items():
    for rnd in ("codebase", "dsa"):
        cfg["extra"](rnd)  # the code-help workspace files build (they reach into the toolchains)
assert b"class Expect" in lsp.SERVERS["java"]["extra"]("dsa")["Expect.java"]
print("PASS code help builds its workspace files for every language (Java gets the same Expect.java)")
