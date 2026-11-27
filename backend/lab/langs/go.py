"""Go backend for shared-case problems (contract: docs/rounds/3-language-variants/CONTRACT.md). Pure stdlib.
The generic reflection-based harness lives in go_harness.go.tmpl."""

import json
import os
from pathlib import Path

TESTS_FILE = "hidden_test.go"
INIT = ("id", "url", "ttl", "api", "http", "json", "ip", "uuid", "sku")
_TMPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "go_harness.go.tmpl")


def _pascal(s):
    return "".join(p.upper() if p in INIT else p[:1].upper() + p[1:] for p in s.split("_"))


def name(kind, x):
    if kind in ("func", "method", "field"):
        return _pascal(x)
    if kind == "class":
        return x
    if kind == "new":
        return "New" + x
    if kind == "error":
        return "Err" + _pascal(x)
    if kind == "param":
        return _pname(x)
    return x  # module


def gtype(t):
    if t in ("int", "long"):
        return "int"
    if t in ("bool", "string"):
        return t
    if t.startswith("list<"):
        return "[]" + gtype(t[5:-1])
    return t  # record


def _results(sig):
    r = sig.get("returns") or ""
    if r.startswith("optional<"):
        return f" ({gtype(r[9:-1])}, bool)"
    outs = ([gtype(r)] if r else []) + (["error"] if sig.get("errors") else [])
    return "" if not outs else " " + outs[0] if len(outs) == 1 else " (" + ", ".join(outs) + ")"


def _lower(n):
    p = n.split("_")
    return p[0] + "".join(_pascal(x) for x in p[1:])


GO_KEYWORDS = set(
    "break default func interface select case defer go map struct chan else goto package switch const fallthrough if range type continue for import return var".split()
)


def _pname(n):
    x = _lower(n)
    return x + "_" if x in GO_KEYWORDS else x


def _params(sig):
    return ", ".join(f"{_pname(n)} {gtype(t)}" for n, t in sig["params"])


def _ctor(c, d):
    return f"(*{c}, error)" if d.get("init_errors") else f"*{c}"


def _recv(c):
    return f"({c[0].lower()} *{c})"


def _records(api):
    out = []
    for r, fs in api.get("records", {}).items():
        w = max(len(name("field", f)) for f, _ in fs)
        out.append(
            f"type {r} struct {{\n" + "".join(f"\t{name('field', f).ljust(w)} {gtype(t)}\n" for f, t in fs) + "}"
        )
    return out


def _errors(api, stub=False):
    es = api.get("errors", [])
    if not es:
        return []
    w = max(len(name("error", e)) for e in es)
    if stub:
        return [
            "var (\n"
            + "".join(f'\t{name("error", e).ljust(w)} = errors.New("{e.replace("_", " ")}")\n' for e in es)
            + ")"
        ]
    return [f"var {name('error', e)} error" for e in es]


def _funcs(api):
    return [(f, s) for f, s in api.get("functions", {}).items()]


def _decl(fname, sig, recv=""):
    return f"func {recv}{fname}({_params(sig)}){_results(sig)}"


def signatures(api):
    parts = _records(api) + _errors(api)
    for f, s in _funcs(api):
        parts.append(_decl(name("func", f), s))
    for c, d in api.get("classes", {}).items():
        init = {"params": d.get("init", [])}
        parts.append(f"type {c} struct{{ /* your fields */ }}\n\nfunc New{c}({_params(init)}) {_ctor(c, d)}")
        ms = []
        for m, s in d["methods"].items():
            doc = f"// level {s['level']}\n" if s.get("level", 1) > 1 else ""
            ms.append(doc + _decl(name("method", m), s, _recv(c) + " "))
        parts.append("\n\n".join(ms))
    return "```go\n" + "\n\n".join(parts) + "\n```\n"


def _q(s):  # Go string literal
    return (
        '"'
        + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        + '"'
    )


def _lit(v, t):
    if v is None:
        return "nil"
    if t == "bool":
        return "true" if v else "false"
    if t == "string":
        return _q(v)
    if t in ("int", "long"):
        return str(v)
    if t.startswith("list<"):
        return gtype(t) + "{" + ", ".join(_lit(x, t[5:-1]) for x in v) + "}"
    raise ValueError(t)


def _rlit(api, v, t):
    if t in api.get("records", {}):
        return t + "{" + ", ".join(f"{name('field', f)}: {_rlit(api, v[f], ft)}" for f, ft in api["records"][t]) + "}"
    if t.startswith("list<"):
        return gtype(t) + "{" + ", ".join(_rlit(api, x, t[5:-1]) for x in v) + "}"
    return _lit(v, t)


def _example(api, case):
    steps = case.get("steps") or [case]
    body, n, uses = [], 0, set()
    funcs, cls = api.get("functions", {}), None

    def errcheck(n, err, ok):
        if err is True:
            return [f"\tif err{n} == nil {{", '\t\tt.Fatal("expected an error")', "\t}"]
        if err:
            uses.add("errors")
            return [
                f"\tif !errors.Is(err{n}, {name('error', err)}) {{",
                f'\t\tt.Fatalf("expected {name("error", err)}, got %v", err{n})',
                "\t}",
            ]
        return [f"\tif err{n} != nil {{", f"\t\tt.Fatal(err{n})", "\t}"]

    for s in steps:
        n += 1
        if "new" in s:
            cls = s["new"]
            cd = api["classes"][cls]
            args = ", ".join(_rlit(api, a, t) for a, (_, t) in zip(s["args"], cd.get("init", [])))
            if cd.get("init_errors"):
                v = "_" if s.get("error") else cls[0].lower()
                body.append(f"\t{v}, err{n} := New{cls}({args})")
                body += errcheck(n, s.get("error"), True)
            else:
                body.append(f"\t{cls[0].lower()} := New{cls}({args})")
            continue
        c = s["call"]
        sig = funcs[c] if c in funcs else api["classes"][cls]["methods"][c]
        args = ", ".join(_rlit(api, a, t) for a, (_, t) in zip(s["args"], sig["params"]))
        call = f"{'' if c in funcs else cls[0].lower() + '.'}{name('func', c)}({args})"
        ret, want = sig.get("returns"), s.get("expect")
        opt = (ret or "").startswith("optional<")
        err = s.get("error")
        lhs = []
        if ret:
            lhs.append(f"got{n}" if ("expect" in s and not err) else "_")
        if opt:
            lhs.append(f"ok{n}")
        if sig.get("errors"):
            lhs.append(f"err{n}")
        if not lhs:
            body.append("\t" + call)
            continue
        body.append(f"\t{', '.join(lhs)} := {call}" if lhs != ["_"] else f"\t{call}")
        if sig.get("errors"):
            body += errcheck(n, err, True)
        if "expect" in s and not err:
            rt = ret[9:-1] if opt else ret
            if opt and want is None:
                body += [f"\tif ok{n} {{", f'\t\tt.Fatalf("expected nothing, got %v", got{n})', "\t}"]
                continue
            w = _rlit(api, want, rt)
            if rt in ("int", "long", "bool", "string"):
                cond = f"got{n} != {w}"
            elif want == []:
                cond = f"len(got{n}) != 0"
            else:
                uses.add("reflect")
                cond = f"!reflect.DeepEqual(got{n}, {w})"
            if opt:
                cond = f"!ok{n} || " + cond
            body += [f"\tif {cond} {{", f'\t\tt.Fatalf("expected %v, got %v", {w}, got{n})', "\t}"]
    imps = sorted(uses | {"testing"})
    return imps, body


def scaffold(api, example=None):
    mod = api["module"]
    stub = ['\tpanic("not implemented")']
    parts = _records(api) + _errors(api, stub=True)
    for f, s in _funcs(api):
        parts.append(_decl(name("func", f), s) + " {\n" + stub[0] + "\n}")
    for c, d in api.get("classes", {}).items():
        init = {"params": d.get("init", [])}
        parts.append(f"type {c} struct{{}}\n\nfunc New{c}({_params(init)}) {_ctor(c, d)} {{\n{stub[0]}\n}}")
        for m, s in d["methods"].items():
            if s.get("level", 1) == 1:
                parts.append(_decl(name("method", m), s, _recv(c) + " ") + " {\n" + stub[0] + "\n}")
    head = f"package {mod}\n\n" + ('import "errors"\n\n' if api.get("errors") else "")
    out = {f"{mod}.go": head + "\n\n".join(parts) + "\n", "go.mod": f"module {mod}\n\ngo 1.22\n"}
    if example:
        imps, body = _example(api, example)
        imp = f'import "{imps[0]}"' if len(imps) == 1 else "import (\n" + "".join(f'\t"{i}"\n' for i in imps) + ")"
        out["example_test.go"] = (
            f"package {mod}\n\n{imp}\n\nfunc TestExample(t *testing.T) {{\n" + "\n".join(body) + "\n}\n"
        )
    return out


def tests_file(api, cases_by_tag, data):
    allc = [c for cs in cases_by_tag.values() for c in cs]
    fns = ", ".join(f'{_q(f)}: {name("func", f)}' for f in api.get("functions", {}))
    news = ", ".join(f'{_q(c)}: {name("new", c)}' for c in api.get("classes", {}))
    errs = ", ".join(f'{_q(e)}: {name("error", e)}' for e in api.get("errors", []))
    reg = (
        f"var hiddenFuncs = map[string]any{{{fns}}}\n\nvar hiddenNew = map[string]any{{{news}}}\n\n"
        f"var hiddenErrs = map[string]error{{{errs}}}"
    )

    def dj(o):
        return json.dumps(o, ensure_ascii=False, separators=(",", ":"))

    emb = (
        f"const hiddenAPIJSON = {_q(dj(api))}\n\nconst hiddenCasesJSON = {_q(dj(allc))}\n\n"
        f"var hiddenDataJSON = map[string]string{{{', '.join(f'{_q(k)}: {_q(dj(v))}' for k, v in data.items())}}}"
    )
    tests = []
    for tag, cs in cases_by_tag.items():
        pre = "Test_" + tag[len("test_") :]
        tests += [f'func {pre}{c["name"]}(t *testing.T) {{ hiddenRun(t, {_q(c["name"])}) }}' for c in cs]
    src = Path(_TMPL).read_text()
    for k, v in (
        ("PKG", api["module"]),
        ("INIT", ", ".join(f'"{i}": true' for i in INIT)),
        ("REGISTRIES", reg),
        ("EMBED", emb),
        ("TESTS", "\n\n".join(tests)),
    ):
        src = src.replace(f"@@{k}@@", v)
    return src
