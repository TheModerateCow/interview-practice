"""pack.py <set_dir> <out.zip> — pack an interview-set/1 zip for Interview Lab (spec: FORMAT.md).

Packs manifest.json, problem.md, starter/** and every `.hidden/X` the manifest names, taken from
<set_dir>/.hidden/X, <set_dir>/X or <set_dir>/levels/X. Never packs reference/, mutants.json or bugs.json.
"""
import json, os, re, sys, zipfile

LANGS = {"python": ".py", "go": ".go", "java": ".java", "typescript": ".ts", "javascript": ".js", "c": None, "cpp": None}
ROUNDS = {"codebase", "levelled", "ai-assisted", "tdd", "dsa"}
REFUSED = ("reference/", "mutants.json", "bugs.json")


def validate(m, exists, read=None):
    """m: parsed manifest; exists(path) -> bool for a path relative to the zip root; read(path) -> bytes (optional,
    enables the tags-vs-hidden-tests check). Returns a list of errors."""
    e = []
    if not isinstance(m, dict): return ["manifest.json must be a JSON object"]
    def s(k, req=True):
        v = m.get(k)
        if v is None and not req: return None
        if not isinstance(v, str) or not v.strip(): e.append(f"{k}: required string"); return None
        return v
    if m.get("format") != "interview-set/1": e.append('format: must be "interview-set/1"')
    n = s("name")
    if n and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", n): e.append("name: lowercase letters, digits and '-' only (max 64)")
    s("title"); s("company", False); s("role", False); s("rules", False)
    lang = s("language")
    if lang and lang not in LANGS: e.append(f"language: one of {sorted(LANGS)}")
    if m.get("round") not in ROUNDS: e.append(f"round: one of {sorted(ROUNDS)}")
    if m.get("difficulty") not in ("medium", "hard"): e.append('difficulty: "medium" or "hard"')
    mins = m.get("minutes")
    if not isinstance(mins, (int, float)) or isinstance(mins, bool) or not 1 <= mins <= 600: e.append("minutes: number 1-600")
    g = m.get("grade_timeout_s", 45)
    if not isinstance(g, (int, float)) or isinstance(g, bool) or not 5 <= g <= 600: e.append("grade_timeout_s: number 5-600")
    for k, v in m.items():
        if isinstance(v, str) and any(v.startswith(r) or v == r.rstrip("/") for r in REFUSED): e.append(f"{k}: must not point at {v}")
    if not exists("problem.md"): e.append("problem.md missing")
    if not exists("starter/"): e.append("starter/ missing or empty")
    tags = m.get("tags", ["test_"])
    if not isinstance(tags, list) or not tags or not all(isinstance(t, str) and t for t in tags): e.append("tags: non-empty list of test-name prefixes"); tags = []
    ht = s("hidden_tests", False); ht_ok = bool(ht)
    if ht:
        if not ht.startswith(".hidden/") or ".." in ht: e.append("hidden_tests: must be a path under .hidden/"); ht_ok = False
        elif not exists(ht): e.append(f"hidden_tests: {ht} missing"); ht_ok = False
        elif lang in LANGS and LANGS[lang] and not ht.endswith(LANGS[lang]): e.append(f"hidden_tests: must end in {LANGS[lang]} for {lang}")
        if lang in ("c", "cpp"): e.append("hidden_tests: C/C++ sets are Run-only")
    rv = m.get("reveal", [])
    if not isinstance(rv, list): e.append("reveal: list"); rv = []
    rd = [r for r in rv if isinstance(r, dict)]
    start = set(tags) - {r.get("unlocks") for r in rd if isinstance(r.get("unlocks"), str)}
    seen_file, seen_unlock = {}, {}
    for i, r in enumerate(rv):
        if not isinstance(r, dict): e.append(f"reveal[{i}]: object"); continue
        f = r.get("file")
        if not isinstance(f, str) or not f.startswith(".hidden/") or ".." in f: e.append(f"reveal[{i}].file: must be a path under .hidden/")
        elif not exists(f): e.append(f"reveal[{i}].file: {f} is missing (pack.py looks in .hidden/, the set folder and levels/)")
        elif f in seen_file: e.append(f"reveal[{i}].file: {f} is already revealed by reveal[{seen_file[f]}]")
        else: seen_file[f] = i
        u, a = r.get("unlocks"), r.get("after_tag")
        if isinstance(u, str) and u in seen_unlock: e.append(f"reveal[{i}].unlocks: {u} is already unlocked by reveal[{seen_unlock[u]}]")
        elif isinstance(u, str): seen_unlock[u] = i
        if isinstance(a, str) and a in tags and a not in start and not any(o.get("unlocks") == a for o in rd if o is not r):
            e.append(f"reveal[{i}].after_tag: {a} is never unlocked before this part, so passing it can't reveal it")
        if r.get("unlocks") is not None and r.get("unlocks") not in tags: e.append(f"reveal[{i}].unlocks: must be one of tags")
        if r.get("after_tag") is not None and r.get("after_tag") not in tags: e.append(f"reveal[{i}].after_tag: must be one of tags")
        o = r.get("or_minutes_left")
        if o is not None and (not isinstance(o, (int, float)) or isinstance(o, bool)): e.append(f"reveal[{i}].or_minutes_left: number or null")
    if ht and ht_ok and read and tags:
        text = read(ht).decode(errors="replace").lower()
        # ponytail: text match, the grader's case-insensitive substring rule; a tag only in a comment passes. The gate's run is the exact check.
        e += [f"tags: {t} matches no test in {ht}" for t in tags if t.lower() not in text]
    s("your_tests", False)
    ex = s("examples", False)
    if ex and (not ex.startswith(".hidden/") or ".." in ex or not exists(ex)): e.append(f"examples: {ex} missing or not under .hidden/")
    re_ = s("run_entry", False)
    if re_ and (".." in re_ or not exists("starter/" + re_)): e.append(f"run_entry: starter/{re_} missing")
    tc = m.get("testcases", [])
    if not isinstance(tc, list) or not all(isinstance(t, dict) and isinstance(t.get("stdin", ""), str) and isinstance(t.get("expected"), str) for t in tc):
        e.append('testcases: list of {"stdin": str, "expected": str}')
    elif tc and not re_: e.append("testcases need run_entry")
    return e


def pack(d, out):
    m = json.load(open(os.path.join(d, "manifest.json")))
    hidden = [m.get("hidden_tests"), m.get("examples")] + [r.get("file") for r in m.get("reveal", []) if isinstance(r, dict)]
    src = {}
    for h in filter(None, hidden):
        x = h[len(".hidden/"):] if isinstance(h, str) and h.startswith(".hidden/") else None
        if not x: continue
        p = next((os.path.join(d, b, x) for b in (".hidden", "", "levels") if os.path.isfile(os.path.join(d, b, x))), None)
        if p: src[h] = p
    st = os.path.join(d, "starter")
    for root, _, fs in os.walk(st):
        for f in fs:
            p = os.path.join(root, f)
            if not os.path.islink(p): src["starter/" + os.path.relpath(p, st).replace(os.sep, "/")] = p
    src["manifest.json"] = os.path.join(d, "manifest.json")
    if os.path.isfile(os.path.join(d, "problem.md")): src["problem.md"] = os.path.join(d, "problem.md")
    errs = validate(m, lambda p: p in src or (p.endswith("/") and any(k.startswith(p) for k in src)), read=lambda p: open(src[p], "rb").read())
    bad = [k for k in src if k.startswith(REFUSED) or "/reference/" in k or k.endswith(("mutants.json", "bugs.json"))]
    if bad: errs.append(f"refusing to pack: {bad}")
    if errs: sys.exit("NOT PACKED:\n  " + "\n  ".join(errs))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for k in sorted(src): z.write(src[k], k)
    print(f"packed {len(src)} files -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    pack(sys.argv[1], sys.argv[2])
