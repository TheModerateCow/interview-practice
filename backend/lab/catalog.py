"""The problem catalog: built-in problems (catalog/<id>/, baked into the image) plus the user's own (data/catalog/<id>/,
saved by every zip import). Picking a problem in a language starts an attempt: a set in data/sets/ with its own clock.

A built-in problem is language-neutral (problem.json + <lang>/ variants, rendered by lab.variants); an imported problem
is one interview-set/1 set in one language (manifest.json)."""
import json, os, shutil

from lab import variants
from lab.errors import Invalid, NotFound
from lab.store import DATA, NAME_RE, ROOT, SETS, jload, jsave, left_s, lock, manifest, ready_info, session, set_names

BUILTIN = os.environ.get("ILAB_CATALOG", os.path.join(ROOT, "catalog"))
CUSTOM = os.path.join(DATA, "catalog")
FIELDS = ("title", "company", "round", "difficulty", "minutes")
SET_FILES = ("manifest.json", "problem.md", "starter", ".hidden")


class Problem:
    def __init__(self, pid, folder, source):
        self.id, self.dir, self.source = pid, folder, source
        self.neutral = os.path.isfile(os.path.join(folder, "problem.json"))
        self.meta = jload(os.path.join(folder, "problem.json" if self.neutral else "manifest.json"))
        self.languages = variants.languages(folder) if self.neutral else [self.meta.get("language")]

    def attempt_name(self, lang, k):
        return f"{self.id}-{lang}-{k}" if self.neutral else f"{self.id}-{k}"

    def files(self, lang, name):
        """The attempt's set: {relpath: bytes}, manifest included."""
        out = variants.render(self.dir, lang, name) if self.neutral else _read(self.dir, SET_FILES)
        m = json.loads(out["manifest.json"])
        out["manifest.json"] = json.dumps(m | {"name": name, "problem": self.id, "language": lang}, indent=1).encode()
        return out


def _read(d, names):
    """{relpath: bytes} for the files and folders `names` under d."""
    out = {}
    for f in names:
        p = os.path.join(d, f)
        if os.path.isfile(p): out[f] = open(p, "rb").read()
        for root, _, fs in os.walk(p) if os.path.isdir(p) else ():
            for x in fs:
                q = os.path.join(root, x)
                out[os.path.relpath(q, d).replace(os.sep, "/")] = open(q, "rb").read()
    return out


def _scan(root, source):
    out = {}
    for n in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        d = os.path.join(root, n)
        if NAME_RE.fullmatch(n) and (os.path.isfile(os.path.join(d, "problem.json")) or os.path.isfile(os.path.join(d, "manifest.json"))):
            p = Problem(n, d, source)
            if isinstance(p.meta, dict) and p.languages: out[n] = p
    return out


def problems():
    """id -> Problem; a built-in id hides a custom one of the same name."""
    return _scan(CUSTOM, "custom") | _scan(BUILTIN, "builtin")


def problem_of(m):
    return m.get("problem") or m.get("preset")   # "preset": attempts made by the earlier Library


def attempts():
    """problem id -> [(attempt name, language, status, start)], oldest name first."""
    out = {}
    for n in set_names():
        m = jload(os.path.join(SETS, n, "manifest.json"))
        if isinstance(m, dict) and problem_of(m):
            s = session(n) or {}
            out.setdefault(problem_of(m), []).append((n, m.get("language"), ready_info(n)["status"], s.get("start") or 0))
    return out


def sets():
    """GET /api/sets: every attempt with its status and, while running, the time left."""
    out = []
    for n in set_names():
        i = ready_info(n)
        out.append({k: i[k] for k in ("name", "title", "language", "round", "minutes", "status")}
                   | {"left_s": left_s(session(n)) if i["status"] == "running" else None, "problem": problem_of(manifest(n))})
    return {"sets": out}


def listing():
    att = attempts()
    rows = []
    for pid, p in problems().items():
        started = sorted((x for x in att.get(pid, []) if x[2] != "ready"), key=lambda x: x[3])
        by_lang = {l: sum(1 for x in started if x[1] == l) for l in p.languages}
        rows.append({"id": pid, "source": p.source, "languages": p.languages} | {k: p.meta.get(k) for k in FIELDS}
                    | {"attempts": len(started), "by_language": by_lang, "last": started[-1][2] if started else None,
                       "last_language": started[-1][1] if started else None})
    return {"problems": rows}


def start_attempt(pid, lang=None):
    """Open the problem's running attempt in that language, else an unstarted one, else a new attempt."""
    ps = problems()
    if pid not in ps: raise NotFound(f"no problem named {pid!r}")
    p = ps[pid]
    if lang is None and len(p.languages) == 1: lang = p.languages[0]
    if lang not in p.languages:
        raise Invalid(f"{p.meta['title']} has no {lang} version" if lang else "pick a language: " + ", ".join(p.languages))
    reused = lambda name: {"name": name, "title": p.meta["title"], "language": lang, "reused": True}  # noqa: E731
    with lock("catalog:" + pid):
        mine = [x for x in attempts().get(pid, []) if x[1] == lang]
        hit = next((x[0] for x in mine if x[2] == "running"), None)
        if hit: return reused(hit)
        hit = next((x[0] for x in mine if x[2] == "ready"), None)
        if hit:
            with lock(hit):   # Start takes this lock: an attempt is never rebuilt under a Start
                if not (session(hit) or {}).get("start"): _build(p, lang, hit)
            return reused(hit)
        k = 1
        while os.path.exists(os.path.join(SETS, p.attempt_name(lang, k))): k += 1
        name = p.attempt_name(lang, k)
        if not NAME_RE.fullmatch(name): raise Invalid(f"problem id {pid!r} is too long to copy")
        _build(p, lang, name)
    return {"name": name, "title": p.meta["title"], "language": lang, "reused": False}


def _build(p, lang, name):
    """Write the attempt's set from the problem as it is now. An unstarted attempt is rebuilt each time it's opened,
    so a catalog update reaches it (it holds no edits: files can't be saved before Start)."""
    tmp, dest, old = (os.path.join(SETS, x) for x in (f".attempt-{name}", name, f".old-{name}"))
    for d in (tmp, old): shutil.rmtree(d, ignore_errors=True)
    variants.write(p.files(lang, name), tmp)
    shutil.copytree(os.path.join(tmp, "starter"), os.path.join(tmp, "work"))
    if os.path.isdir(dest): os.replace(dest, old)
    os.replace(tmp, dest)
    shutil.rmtree(old, ignore_errors=True)


def save_custom(set_dir, pid):
    """An imported set becomes the user's own catalog problem (replacing an older import of the same id)."""
    if pid in _scan(BUILTIN, "builtin"): return   # a built-in of that name wins; the imported attempt still works
    dest, tmp = os.path.join(CUSTOM, pid), os.path.join(CUSTOM, f".import-{pid}")
    shutil.rmtree(tmp, ignore_errors=True)
    for f in SET_FILES:
        p = os.path.join(set_dir, f)
        if os.path.isdir(p): shutil.copytree(p, os.path.join(tmp, f))
        elif os.path.isfile(p): os.makedirs(tmp, exist_ok=True); shutil.copy(p, os.path.join(tmp, f))
    m = jload(os.path.join(tmp, "manifest.json")) or {}
    m.pop("problem", None)
    jsave(os.path.join(tmp, "manifest.json"), m)
    shutil.rmtree(dest, ignore_errors=True)
    os.replace(tmp, dest)
