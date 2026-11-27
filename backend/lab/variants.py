"""Language variants: render a language-neutral problem (catalog/<problem>/) into an interview-set/1 set for one language.
Contract: docs/rounds/3-language-variants/CONTRACT.md. Pure stdlib; used by the backend and by tools/."""
import importlib, json, os, re
from pathlib import Path

LANGS = ("go", "java", "python")
YOUR_TESTS = {"go": "*_test.go", "java": "*Test.java", "python": "test_*.py"}
CODEBASE_TESTS = {"go": "hidden_test.go", "java": "HiddenTest.java", "python": "tests_hidden.py"}


def backend(lang):
    if lang not in LANGS: raise ValueError(f"unknown language {lang!r}")
    return importlib.import_module(f"lab.langs.{lang}")


def jload(p, default=None):
    try:
        with open(p) as f: return json.load(f)
    except FileNotFoundError: return default


def languages(d):
    return [l for l in LANGS if os.path.isdir(os.path.join(d, l, "starter"))]


def problem(d):
    """(problem.json, api.json or None, {tag: [case]}, {data path: parsed json})."""
    meta, api = jload(os.path.join(d, "problem.json")), jload(os.path.join(d, "api.json"))
    cases, data = {}, {}
    if api is not None:
        for tag in meta.get("tags", ["test_p1_"]):
            stem = tag[len("test_"):].rstrip("_")
            cs = jload(os.path.join(d, "cases", stem + ".json"))
            if cs is None: raise ValueError(f"cases/{stem}.json missing for tag {tag}")
            cases[tag] = cs
            for c in cs:
                if c.get("data"):
                    data[c["data"]] = jload(os.path.join(d, "cases", c["data"]))
                    if data[c["data"]] is None: raise ValueError(f"cases/{c['data']} missing (case {c.get('name')})")
    return meta, api, cases, data


def _pick(d, lang, rel):
    """A shared file, unless <lang>/<rel> overrides it."""
    for p in (os.path.join(d, lang, rel), os.path.join(d, rel)):
        if os.path.isfile(p): return p
    return None


def _kind(api, x):
    if x in api.get("classes", {}) or x in api.get("records", {}): return "class"
    if x in api.get("functions", {}): return "func"
    if any(x in c.get("methods", {}) for c in api.get("classes", {}).values()): return "method"
    if any(x == f for fs in api.get("records", {}).values() for f, _ in fs): return "field"
    if x in api.get("errors", []): return "error"
    if x == api.get("module"): return "module"
    sigs = list(api.get("functions", {}).values()) + [{"params": c.get("init", [])} for c in api.get("classes", {}).values()] \
        + [m for c in api.get("classes", {}).values() for m in c.get("methods", {}).values()]
    if any(x == n for sg in sigs for n, _ in sg.get("params", [])): return "param"
    return None


PLACEHOLDER = re.compile(r"\{\{(new )?([A-Za-z_][A-Za-z0-9_]*)\}\}")


def render_md(text, api, be, manifest=None):
    """Replace {{name}} placeholders; {{run_entry}} and {{your_tests}} come from the language's manifest."""
    specials = {k: str((manifest or {}).get(k, "")) for k in ("run_entry", "your_tests")}
    if not api and not manifest: return text
    def sub(m):
        new, x = m.group(1), m.group(2)
        if not new and x in specials and specials[x]: return specials[x]
        if not api: return m.group(0)
        k = "new" if new else _kind(api, x)
        if k is None: raise ValueError(f"unknown placeholder {{{{{m.group(0)[2:-2]}}}}}")
        return be.name(k, x)
    return PLACEHOLDER.sub(sub, text)


def render(d, lang, name=None):
    """-> {relpath: bytes}: manifest.json, problem.md, .hidden/*, starter/**."""
    meta, api, cases, data = problem(d)
    if lang not in languages(d): raise ValueError(f"{os.path.basename(d)} has no {lang} version")
    be = backend(lang) if api else None
    m = dict(meta)
    m.update(jload(os.path.join(d, lang, "manifest.json"), {}))
    tests_file = be.TESTS_FILE if api else CODEBASE_TESTS[lang]
    m.update(format="interview-set/1", name=name or os.path.basename(d.rstrip("/")), language=lang,
             hidden_tests=".hidden/" + tests_file)
    levelled = bool(api) and m.get("round") == "levelled"
    if levelled: m["examples"] = ".hidden/examples/" + tests_file   # Run grades these: the first case of each level
    else: m.setdefault("your_tests", YOUR_TESTS[lang])
    out = {}
    md = Path(_pick(d, lang, "problem.md")).read_text()
    md = render_md(md, api, be, m)
    if api: md = md.rstrip() + "\n\n## Your code\n\n" + be.signatures(api).rstrip() + "\n"
    out["problem.md"] = md.encode()
    for r in m.get("reveal", []):
        f = r["file"][len(".hidden/"):]
        src = _pick(d, lang, os.path.join("levels", f)) or _pick(d, lang, f)
        if not src: raise ValueError(f"reveal file {f} missing")
        out[".hidden/" + f] = render_md(Path(src).read_text(), api, be, m).encode()
    if api:
        out[".hidden/" + tests_file] = be.tests_file(api, cases, data).encode()
        if levelled: out[m["examples"]] = be.tests_file(api, {t: cs[:1] for t, cs in cases.items()}, data).encode()
    else:
        src = os.path.join(d, lang, "hidden", tests_file)
        if not os.path.isfile(src): raise ValueError(f"{lang}/hidden/{tests_file} missing")
        out[".hidden/" + tests_file] = Path(src).read_bytes()
    st = os.path.join(d, lang, "starter")
    for root, _, fs in os.walk(st):
        for f in fs:
            p = os.path.join(root, f)
            out["starter/" + os.path.relpath(p, st).replace(os.sep, "/")] = Path(p).read_bytes()
    out["manifest.json"] = json.dumps(m, indent=1).encode()
    return out


def write(files, dest):
    for rel, b in files.items():
        p = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f: f.write(b)
