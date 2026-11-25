"""Python backend for shared-case problems. Contract: docs/rounds/3-language-variants/CONTRACT.md. Pure stdlib."""
import json, os, re

TESTS_FILE = "tests_hidden.py"


def _pascal(x): return "".join(w.capitalize() for w in x.split("_"))


def name(kind, neutral):
    return _pascal(neutral) + "Error" if kind == "error" else neutral


def _t(t):
    if t.startswith("list<"): return "list[%s]" % _t(t[5:-1])
    if t.startswith("optional<"): return "%s | None" % _t(t[9:-1])
    return {"int": "int", "long": "int", "bool": "bool", "string": "str"}.get(t, t)


def _sig(ps): return "".join(", %s: %s" % (n, _t(t)) for n, t in ps)


def _decls(api, stub):
    body = "raise NotImplementedError" if stub else "..."
    out = ["class %s(Exception):\n    pass\n" % name("error", e) for e in api.get("errors", [])]
    for r, fs in api.get("records", {}).items():
        out.append("@dataclass\nclass %s:\n%s\n" % (r, "\n".join("    %s: %s" % (f, _t(t)) for f, t in fs)))
    for f, d in api.get("functions", {}).items():
        out.append("def %s(%s) -> %s:\n    %s\n" % (f, _sig(d["params"])[2:], _t(d["returns"]) if d.get("returns") else "None", body))
    for c, d in api.get("classes", {}).items():
        ms = ["    def __init__(self%s):\n        %s\n" % (_sig(d.get("init", [])), body)]
        for m, md in d["methods"].items():
            lv = md.get("level", 1)
            if stub and lv > 1: continue
            note = "    # level %d\n" % lv if not stub and lv > 1 else ""
            ms.append("%s    def %s(self%s) -> %s:\n        %s\n" % (
                note, m, _sig(md["params"]), _t(md["returns"]) if md.get("returns") else "None", body))
        out.append("class %s:\n%s" % (c, "\n".join(ms)))
    return "\n\n".join(out)


def _head(api): return "from dataclasses import dataclass\n\n\n" if api.get("records") else ""


def signatures(api):
    return "```python\n%s%s\n```\n" % (_head(api), _decls(api, False).rstrip())


def tests_file(api, cases_by_tag, data):
    flat = {c["name"]: c for cs in cases_by_tag.values() for c in cs}
    doc = json.dumps({"api": api, "cases": flat, "data": data})
    with open(os.path.join(os.path.dirname(__file__), "python_harness.py.tmpl")) as f:
        src = f.read().replace("__HIDDEN_JSON__", json.dumps(doc))
    tests = "".join("\n\ndef %s%s(): _hidden_run(%s)" % (tag, c["name"], json.dumps(c["name"]))
                    for tag, cs in cases_by_tag.items() for c in cs)
    return src + tests + "\n"


def _lit(api, t, v):
    if t.startswith("list<"): return "[%s]" % ", ".join(_lit(api, t[5:-1], x) for x in v)
    if t.startswith("optional<"): return "None" if v is None else _lit(api, t[9:-1], v)
    if t in api.get("records", {}):
        return "%s(%s)" % (t, ", ".join("%s=%s" % (f, _lit(api, ft, v[f])) for f, ft in api["records"][t]))
    return repr(v)


def _example(api, case):
    used, lines, raises, cname = set(), [], False, None
    for st in case.get("steps") or [case]:
        if "new" in st:
            cname = st["new"]; used.add(cname)
            ps = api["classes"][cname]["init"]
            lines.append("    obj = %s(%s)" % (cname, ", ".join(_lit(api, t, a) for (_, t), a in zip(ps, st.get("args", [])))))
            continue
        n = st["call"]
        free = n in api["functions"]
        d = api["functions"][n] if free else api["classes"][cname]["methods"][n]
        if free: used.add(n)
        used |= {r for r in api.get("records", {}) for _, t in d["params"] + [("", d.get("returns") or "")] if re.search(r"\b%s\b" % r, t)}
        call = "%s%s(%s)" % ("" if free else "obj.", n, ", ".join(_lit(api, t, a) for (_, t), a in zip(d["params"], st.get("args", []))))
        if "error" in st:
            e = "Exception" if st["error"] is True else name("error", st["error"])
            if e != "Exception": used.add(e)
            raises = True
            lines += ["    with pytest.raises(%s):" % e, "        " + call]
        elif "expect" in st and d.get("returns"):
            lines.append("    assert %s %s" % (call, "is None" if st["expect"] is None else "== " + _lit(api, d["returns"], st["expect"])))
        else: lines.append("    " + call)
    imp = ("import pytest\n" if raises else "") + ("from %s import %s\n" % (api["module"], ", ".join(sorted(used))) if used else "")
    return "%s\n\ndef test_example():\n%s\n" % (imp, "\n".join(lines))


def scaffold(api, example=None):
    out = {api["module"] + ".py": _head(api) + _decls(api, True).rstrip() + "\n"}
    if example: out["test_example.py"] = _example(api, example)
    return out
