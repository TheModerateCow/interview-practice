"""Java backend for shared-case problems. Contract: docs/rounds/3-language-variants/CONTRACT.md. Pure stdlib."""
import json, os

TESTS_FILE = "HiddenTest.java"
CHUNK = 30000
STUB = 'throw new UnsupportedOperationException("not implemented");'


def camel(n):
    h, *t = n.split("_")
    return h + "".join(w[:1].upper() + w[1:] for w in t)


def pascal(n):
    c = camel(n)
    return c[:1].upper() + c[1:]


def name(kind, neutral):
    if kind in ("func", "method", "field"): return camel(neutral)
    if kind == "class": return pascal(neutral)
    if kind == "new": return "new " + pascal(neutral)
    if kind == "error": return pascal(neutral) + "Exception"
    if kind == "module": return pascal(neutral)
    raise ValueError(kind)


def jclass(api): return api.get("java_class") or pascal(api["module"])


def jtype(t):
    if t in ("int", "long"): return t
    if t == "bool": return "boolean"
    if t == "string": return "String"
    if t.startswith("optional<"): return {"int": "Integer", "long": "Long", "bool": "Boolean"}.get(t[9:-1], jtype(t[9:-1]))
    if t.startswith("list<"):
        e = t[5:-1]
        return jtype(e) + "[]" if primarr(t) else f"List<{jtype(e)}>"
    return t


def primarr(t):
    if not t.startswith("list<"): return False
    e = t[5:-1]
    return e in ("int", "long", "bool") or primarr(e)


def params(ps): return ", ".join(f"{jtype(t)} {camel(n)}" for n, t in ps)


def _methods(api, cls, upto=None):
    return [(m, d) for m, d in api["classes"][cls]["methods"].items() if upto is None or d.get("level", 1) <= upto]


def signatures(api):
    o = []
    for r, fs in api.get("records", {}).items():
        o.append(f"public record {r}({params(fs)}) {{}}")
    if api.get("errors"):
        o.append("// unchecked exceptions (each extends RuntimeException): " + ", ".join(name("error", e) for e in api["errors"]))
    if api.get("functions"):
        o.append(f"public class {jclass(api)} {{")
        for f, d in api["functions"].items():
            o.append(f"    public static {jtype(d['returns']) if d['returns'] else 'void'} {camel(f)}({params(d['params'])});")
        o.append("}")
    for c, cd in api.get("classes", {}).items():
        o.append(f"public class {c} {{")
        o.append(f"    public {c}({params(cd['init'])});")
        for m, d in cd["methods"].items():
            lv = f"   // level {d['level']}" if d.get("level", 1) > 1 else ""
            o.append(f"    public {jtype(d['returns']) if d['returns'] else 'void'} {camel(m)}({params(d['params'])});{lv}")
        o.append("}")
    return "```java\n" + "\n".join(o) + "\n```"


def _file(body):
    return ("import java.util.List;\n\n" if "List<" in body else "") + body


def _lit(v, t):
    if v is None: return "null"
    if t == "int": return str(v)
    if t == "long": return f"{v}L"
    if t == "bool": return "true" if v else "false"
    if t == "string": return json.dumps(v)
    if t.startswith("optional<"): return _lit(v, t[9:-1])
    if t.startswith("list<"):
        e = t[5:-1]
        if primarr(t):
            return "new " + jtype(t) + "{" + ", ".join(_inner(x, e) for x in v) + "}"
        return "List.of(" + ", ".join(_lit(x, e) for x in v) + ")"
    return f"new {t}(" + ", ".join(_lit(v[f], ft) for f, ft in _RECS[t]) + ")"


def _inner(v, t):
    """Element of a primitive array: nested arrays use bare braces."""
    if t.startswith("list<"): return "{" + ", ".join(_inner(x, t[5:-1]) for x in v) + "}"
    return _lit(v, t)


_RECS = {}


def _example(api, ex):
    _RECS.clear(); _RECS.update(api.get("records", {}))
    L, funcs = [], api.get("functions", {})
    steps = ex["steps"] if "steps" in ex else [ex]
    cur = None

    def sig(call):
        return funcs[call] if call in funcs else api["classes"][cur]["methods"][call]
    for s in steps:
        if "new" in s:
            cur = s["new"]; ps = api["classes"][cur]["init"]
            L.append(f"var o = new {cur}(" + ", ".join(_lit(a, t) for a, (_, t) in zip(s["args"], ps)) + ");")
            continue
        d = sig(s["call"])
        c = (f"{jclass(api)}." if s["call"] in funcs else "o.") + camel(s["call"]) + "(" + ", ".join(_lit(a, t) for a, (_, t) in zip(s["args"], d["params"])) + ")"
        if "error" in s:
            k = "Exception" if s["error"] is True else name("error", s["error"])
            L.append(f"Expect.raises({k}.class, () -> {c});")
        elif "expect" in s and d["returns"]:
            e = _lit(s["expect"], d["returns"])
            if primarr(d["returns"]): L.append(f"Expect.isTrue(java.util.Arrays.deepEquals(new Object[]{{{e}}}, new Object[]{{{c}}}));")
            else: L.append(f"Expect.eq({e}, {c});")
        else: L.append(c + ";")
    body = "\n".join("        " + l for l in L)
    return _file(f"public class ExampleTest {{\n    static void test_{ex['name']}() {{\n{body}\n    }}\n}}\n")


def scaffold(api, example=None):
    out = {}
    for r, fs in api.get("records", {}).items():
        out[f"{r}.java"] = _file(f"public record {r}({params(fs)}) {{}}\n")
    for e in api.get("errors", []):
        n = name("error", e)
        out[f"{n}.java"] = (f"public class {n} extends RuntimeException {{\n    public {n}() {{ super(); }}\n"
                            f"    public {n}(String message) {{ super(message); }}\n}}\n")
    if api.get("functions"):
        b = "".join(f"    public static {jtype(d['returns']) if d['returns'] else 'void'} {camel(f)}({params(d['params'])}) {{\n        {STUB}\n    }}\n\n"
                    for f, d in api["functions"].items())
        out[f"{jclass(api)}.java"] = _file(f"public class {jclass(api)} {{\n{b.rstrip()}\n}}\n")
    for c, cd in api.get("classes", {}).items():
        b = f"    public {c}({params(cd['init'])}) {{\n        {STUB}\n    }}\n\n"
        b += "".join(f"    public {jtype(d['returns']) if d['returns'] else 'void'} {camel(m)}({params(d['params'])}) {{\n        {STUB}\n    }}\n\n"
                     for m, d in _methods(api, c, 1))
        out[f"{c}.java"] = _file(f"public class {c} {{\n{b.rstrip()}\n}}\n")
    if example: out["ExampleTest.java"] = _example(api, example)
    return out


def _esc(s): return s.replace("\\", "\\\\").replace('"', '\\"')


def tests_file(api, cases_by_tag, data):
    allc = {c["name"]: c for cs in cases_by_tag.values() for c in cs}
    doc = json.dumps({"api": api, "cases": allc, "data": data}, separators=(",", ":"))   # ASCII only
    chunks = [doc[i:i + CHUNK] for i in range(0, len(doc), CHUNK)] or [""]
    tests = "".join(f'    static void {tag}{c["name"]}() {{ hiddenRun("{c["name"]}"); }}\n'
                    for tag, cs in cases_by_tag.items() for c in cs)
    tmpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "java_harness.java.tmpl")).read()
    return (tmpl.replace("/*@@TESTS@@*/\n", tests)
                .replace("/*@@CHUNKS@@*/\n", ",\n".join(f'        "{_esc(c)}"' for c in chunks) + "\n"))
