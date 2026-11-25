"""cases.py fill|check <problem_dir> <answers_dir> --lang python

fill:  run the language's reference through the harness; write `expect` for every case/step whose "expect" is "?".
check: run every case against the reference and report mismatches (exit 1 if any).
Python is the canonical language for filling. Contract: docs/rounds/3-language-variants/CONTRACT.md."""
import copy, glob, importlib, json, os, sys, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import variants  # noqa: E402


def load(pd, ad, cases):
    """-> (harness module with the reference importable, api). `cases` {tag: [case]} is embedded in the harness."""
    meta, api, _, data = variants.problem(pd)
    ref = os.path.join(ad, "python", "reference")
    for m in [m for m in sys.modules if m == api["module"]]: del sys.modules[m]
    sys.path.insert(0, ref)
    h = types.ModuleType("tests_hidden")
    exec(compile(variants.backend("python").tests_file(api, cases, data), "tests_hidden.py", "exec"), h.__dict__)
    return h


def steps_of(c): return c.get("steps") or [c]


def main(a):
    if len(a) < 3 or a[0] not in ("fill", "check"): sys.exit(__doc__)
    mode, pd, ad = a[0], os.path.abspath(a[1]), os.path.abspath(a[2])
    if "--lang" in a and a[a.index("--lang") + 1] != "python": sys.exit("only --lang python is supported")
    meta, api, cases, data = variants.problem(pd)
    # "?" expects are unchecked while running; fill writes them afterwards
    work = copy.deepcopy(cases)
    todo = []
    for tag, cs in work.items():
        for c in cs:
            for i, st in enumerate(steps_of(c)):
                if st.get("expect") == "?": del st["expect"]; todo.append((tag, c["name"], i))
    h = load(pd, ad, work)
    bad = 0
    if mode == "check":
        for tag, cs in work.items():
            for c in cs:
                try: h._hidden_run(c["name"])
                except AssertionError as e: bad += 1; print("MISMATCH %s%s: %s" % (tag, c["name"], e))
        print("%d mismatches, %d unset ('?')" % (bad, len(todo)))
        sys.exit(1 if bad else 0)
    got = {}
    for tag, name, i in todo:
        for j, kind, v, _ in h._hidden_play(h._hidden_case(name)):
            if j == i: got[(name, i)] = (kind, v)
    for tag, cs in cases.items():
        stem = tag[len("test_"):].rstrip("_"); n = 0
        for c in cs:
            for i, st in enumerate(steps_of(c)):
                if st.get("expect") != "?": continue
                kind, v = got.get((c["name"], i), ("missing", "not reached"))
                if kind != "ok": bad += 1; print("cannot fill %s%s step %d: %s %s" % (tag, c["name"], i + 1, kind, v)); continue
                st["expect"] = v; n += 1
        if n:
            with open(os.path.join(pd, "cases", stem + ".json"), "w") as f: json.dump(cs, f, indent=1); f.write("\n")
        print("%s: filled %d" % (stem, n))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
