"""The problem catalog: built-in problems (catalog/<id>/, baked into the image) plus the user's own (data/catalog/<id>/,
saved by every zip import). Picking a problem starts an attempt: a copy in data/sets/<id>-<k>/ with its own clock."""
import os, shutil

from lab.store import DATA, NAME_RE, SETS, HTTPError, jload, jsave, lock, ready_info

BUILTIN = os.environ.get("ILAB_CATALOG", "/app/catalog")
CUSTOM = os.path.join(DATA, "catalog")
FIELDS = ("title", "company", "round", "language", "difficulty", "minutes")
PROBLEM_FILES = ("manifest.json", "problem.md", "starter", ".hidden")


def _scan(root, source):
    out = {}
    for n in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        m = jload(os.path.join(root, n, "manifest.json"))
        if NAME_RE.fullmatch(n) and isinstance(m, dict): out[n] = (os.path.join(root, n), m, source)
    return out


def problems():
    """id -> (folder, manifest, "builtin" | "custom"); a built-in id hides a custom one of the same name."""
    return _scan(CUSTOM, "custom") | _scan(BUILTIN, "builtin")


def problem_of(m):
    return m.get("problem") or m.get("preset")   # "preset": attempts made by the earlier Library


def attempts():
    """problem id -> [(attempt name, status)], oldest name first."""
    out = {}
    for n in sorted(os.listdir(SETS)) if os.path.isdir(SETS) else []:
        m = jload(os.path.join(SETS, n, "manifest.json"))
        if NAME_RE.fullmatch(n) and isinstance(m, dict) and problem_of(m):
            out.setdefault(problem_of(m), []).append((n, ready_info(n)["status"]))
    return out


def listing():
    att = attempts()
    rows = []
    for pid, (_, m, source) in problems().items():
        a = att.get(pid, [])
        started = [x for x in a if x[1] != "ready"]
        rows.append({"id": pid, "source": source} | {k: m.get(k) for k in FIELDS}
                    | {"attempts": len(started), "last": started[-1][1] if started else None})
    return {"problems": rows}


def start_attempt(pid):
    """Open the problem's running attempt, else an unstarted one, else copy the problem into a new <id>-<k>."""
    ps = problems()
    if pid not in ps: raise HTTPError(404, f"no problem named {pid!r}")
    src, m, _ = ps[pid]
    with lock("catalog:" + pid):
        mine = attempts().get(pid, [])
        for want in ("running", "ready"):
            hit = next((n for n, st in mine if st == want), None)
            if hit: return {"name": hit, "title": m["title"], "reused": True}
        k = 1
        while os.path.exists(os.path.join(SETS, f"{pid}-{k}")): k += 1
        name = f"{pid}-{k}"
        if not NAME_RE.fullmatch(name): raise HTTPError(400, f"problem id {pid!r} is too long to copy")
        tmp = os.path.join(SETS, f".attempt-{name}")
        shutil.rmtree(tmp, ignore_errors=True)
        for f in PROBLEM_FILES:
            p = os.path.join(src, f)
            if os.path.isdir(p): shutil.copytree(p, os.path.join(tmp, f))
            elif os.path.isfile(p): os.makedirs(tmp, exist_ok=True); shutil.copy(p, os.path.join(tmp, f))
        jsave(os.path.join(tmp, "manifest.json"), m | {"name": name, "problem": pid})
        shutil.copytree(os.path.join(tmp, "starter"), os.path.join(tmp, "work"))
        os.replace(tmp, os.path.join(SETS, name))
    return {"name": name, "title": m["title"], "reused": False}


def save_custom(set_dir, pid):
    """An imported set becomes the user's own catalog problem (replacing an older import of the same id)."""
    if pid in _scan(BUILTIN, "builtin"): return   # a built-in of that name wins; the imported attempt still works
    dest, tmp = os.path.join(CUSTOM, pid), os.path.join(CUSTOM, f".import-{pid}")
    shutil.rmtree(tmp, ignore_errors=True)
    for f in PROBLEM_FILES:
        p = os.path.join(set_dir, f)
        if os.path.isdir(p): shutil.copytree(p, os.path.join(tmp, f))
        elif os.path.isfile(p): os.makedirs(tmp, exist_ok=True); shutil.copy(p, os.path.join(tmp, f))
    shutil.rmtree(dest, ignore_errors=True)
    os.replace(tmp, dest)
