"""gate_problem.py <problem_dir> <answers_dir> [--lang go,java] [--keep DIR] [--build-starter]

Render the problem for each language, add that language's answers (reference/, mutants.json, bugs.json) and run the
unchanged gate.py on it in the app's runner images. Prints "<lang>: GATE PASS" per language; exits 1 if any fails.
--build-starter: Codebase only; write <problem>/<lang>/starter from reference + bugs.json (gate.py --build-starter).
--keep DIR: leave the rendered sets in DIR/<lang>/ (default: a temp dir, removed).
Contract: docs/rounds/3-language-variants/CONTRACT.md.
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import variants  # noqa: E402


def stage(problem_dir, answers_dir, lang, dest):
    files = variants.render(problem_dir, lang)
    variants.write(files, dest)
    hidden = [k for k in files if k.startswith(".hidden/") and not k.endswith(".md")]
    for k in hidden: shutil.copy(os.path.join(dest, k), os.path.join(dest, os.path.basename(k)))   # gate.py reads it at the set root
    a = os.path.join(answers_dir, lang)
    shutil.copytree(os.path.join(a, "reference"), os.path.join(dest, "reference"))
    for f in ("mutants.json", "bugs.json"):
        if os.path.isfile(os.path.join(a, f)): shutil.copy(os.path.join(a, f), os.path.join(dest, f))


def gate(dest, extra=()):
    cmd = ["docker", "compose", "run", "--rm", "-T", "-v", f"{dest}:/set", "backend", "python3", "gate.py", "/set", *extra]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.stdout + r.stderr


def main(a):
    if len(a) < 2: sys.exit(__doc__)
    pd, ad = os.path.abspath(a[0]), os.path.abspath(a[1])
    langs = a[a.index("--lang") + 1].split(",") if "--lang" in a else variants.languages(pd)
    keep = os.path.abspath(a[a.index("--keep") + 1]) if "--keep" in a else None
    base = keep or tempfile.mkdtemp(prefix="gate-")
    ok = True
    for lang in langs:
        dest = os.path.join(base, lang)
        shutil.rmtree(dest, ignore_errors=True)
        stage(pd, ad, lang, dest)
        if "--build-starter" in a:
            print(gate(dest, ["--build-starter"]).strip().splitlines()[-1])
            st = os.path.join(pd, lang, "starter")
            shutil.rmtree(st, ignore_errors=True); shutil.copytree(os.path.join(dest, "starter"), st)
            continue
        out = gate(dest)
        lines = [l for l in out.splitlines() if l.startswith(("PASS", "FAIL", "GATE"))]
        for l in lines:
            if not l.startswith("PASS"): print(f"{lang}: {l}")
        passed = bool(lines) and lines[-1] == "GATE PASS"
        if not lines: print(f"{lang}: no gate output:\n{out[-2000:]}")
        print(f"{lang}: {'GATE PASS' if passed else 'GATE FAIL'}")
        ok &= passed
    if not keep: shutil.rmtree(base, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
