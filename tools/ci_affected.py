"""ci_affected.py [<base-ref> | --all]  — which problem gates a change needs, as the CI matrix (JSON on stdout).

Reads the changed files (git diff <base-ref>...HEAD) and maps them to (problem, language) gates:
  grader core (variants.py, sandbox/, the backend image, compose files, gate_problem.py)  → the canaries, every language
  a language backend (backend/lab/langs/<lang>*) or its runner image (deploy/runner-python/)  → the canaries in that language
  catalog/<p>/<lang>/… or answers/<p>/<lang>/…                                               → p in that language
  any other file of catalog/<p>/ (problem.json, api.json, cases/, statement)                  → p in all its languages
  tests/fixture/… likewise, as the problem "fixture"
The canaries are tests/fixture (every shared-case harness feature, in all three languages) and one Codebase problem
(per-language hidden tests, planted bugs, a timing phase): if they pass, the harness and grader are sound for every
problem, so a harness change never re-gates the whole catalog. A full re-gate is a manual run (--all).
Output: {"include": [{"lang": "go", "problems": "catalog/a catalog/b"}, …]} — one CI job per language with work;
{"include": []} when nothing needs gating.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab.variants import LANGS  # noqa: E402  (the catalog languages: one list)

CORE = (
    "backend/lab/variants.py",
    "backend/lab/langs/__init__.py",
    "backend/sandbox/",
    "deploy/backend/",
    "deploy/docker-compose.yml",
    "tests/compose.test.yml",
    "tools/gate_problem.py",
)
FIXTURE = "tests/fixture"
CANARIES = (FIXTURE, "catalog/quota-codebase")


def problems(root=ROOT):
    """problem dir (relative) -> its languages."""
    out = {}
    for d in [FIXTURE] + sorted("catalog/" + n for n in os.listdir(os.path.join(root, "catalog"))):
        langs = [l for l in LANGS if os.path.isdir(os.path.join(root, d, l, "starter"))]
        if langs:
            out[d] = langs
    return out


def affected(changed, probs):
    """changed: relative paths; probs: problem dir -> languages. Returns {lang: set(problem dirs)}."""
    want = {l: set() for l in LANGS}

    def add(p, langs):
        for l in langs:
            if l in probs.get(p, []):
                want[l].add(p)

    for f in changed:
        if f.startswith(CORE):
            for p in CANARIES:
                add(p, LANGS)
            continue
        for l in LANGS:
            if f.startswith(f"backend/lab/langs/{l}") or (l == "python" and f.startswith("deploy/runner-python/")):
                for p in CANARIES:
                    add(p, [l])
        parts = f.split("/")
        if f.startswith(FIXTURE + "/"):
            p, rest = FIXTURE, parts[2:]
            if rest[:1] == ["answers"]:
                rest = rest[1:]
        elif parts[0] in ("catalog", "answers") and len(parts) > 2:
            p, rest = "catalog/" + parts[1], parts[2:]
        else:
            continue
        add(p, [rest[0]] if rest and rest[0] in LANGS else probs.get(p, []))
    return {l: ps for l, ps in want.items() if ps}


def main(a):
    probs = problems()
    if a[:1] == ["--all"] or not a:
        want = {l: {p for p, ls in probs.items() if l in ls} for l in LANGS}
    else:
        changed = subprocess.run(
            ["git", "diff", "--name-only", f"{a[0]}...HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
        want = affected(changed, probs)
    print(json.dumps({"include": [{"lang": l, "problems": " ".join(sorted(ps))} for l, ps in want.items() if ps]}))


def _check():
    probs = {
        "tests/fixture": list(LANGS),
        "catalog/a": list(LANGS),
        "catalog/b": ["go"],
        "catalog/quota-codebase": list(LANGS),
    }
    assert affected(["README.md", "ui/src/App.svelte"], probs) == {}
    assert affected(["catalog/a/go/starter/x.go"], probs) == {"go": {"catalog/a"}}
    assert affected(["answers/a/java/reference/X.java"], probs) == {"java": {"catalog/a"}}
    assert affected(["catalog/a/cases/p1.json"], probs) == {l: {"catalog/a"} for l in LANGS}
    canary = {"tests/fixture", "catalog/quota-codebase"}
    assert affected(["backend/lab/langs/go_harness.go.tmpl"], probs) == {"go": canary}
    assert affected(["deploy/runner-python/Dockerfile"], probs) == {"python": canary}
    assert affected(["backend/sandbox/grade.py"], probs) == {l: canary for l in LANGS}
    assert affected(["backend/sandbox/grade.py", "catalog/b/go/starter/x.go"], probs) == {
        "go": canary | {"catalog/b"},
        "java": canary,
        "python": canary,
    }
    assert affected(["tests/fixture/answers/java/mutants.json"], probs) == {"java": {"tests/fixture"}}
    assert affected(["catalog/gone/problem.md"], probs) == {}  # a deleted problem gates nothing


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-check"]:
        _check()
        print("ok")
    else:
        main(sys.argv[1:])
