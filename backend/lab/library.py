"""The preset Library: packed sets shipped in the image (presets/*.zip). Taking one imports a fresh copy."""
import json, os, zipfile

from lab import importer
from lab.store import NAME_RE, SETS, HTTPError, jload

PRESETS = os.environ.get("ILAB_PRESETS", "/app/presets")
FIELDS = ("name", "title", "company", "round", "language", "difficulty", "minutes")


def _manifest(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        top = "manifest.json" if "manifest.json" in names else next(n for n in names if n.count("/") == 1 and n.endswith("/manifest.json"))
        return json.loads(z.read(top))


def presets():
    """name -> (zip path, manifest), read fresh on every call (ponytail: ~10 small zips; cache if the library grows)."""
    out = {}
    for f in sorted(os.listdir(PRESETS)) if os.path.isdir(PRESETS) else []:
        if not f.endswith(".zip"): continue
        p = os.path.join(PRESETS, f)
        try: m = _manifest(p)
        except (zipfile.BadZipFile, StopIteration, ValueError, KeyError): continue
        if isinstance(m, dict) and NAME_RE.fullmatch(str(m.get("name", ""))): out[m["name"]] = (p, m)
    return out


def listing():
    return {"presets": [{k: m.get(k) for k in FIELDS} for _, m in presets().values()]}


def take(name):
    """Open a copy of preset `name`: an unstarted copy if one is waiting, else a new <name>-<k>."""
    ps = presets()
    if name not in ps: raise HTTPError(404, f"no preset named {name!r}")
    path, m = ps[name]
    os.makedirs(SETS, exist_ok=True)
    for n in sorted(os.listdir(SETS)):
        d = os.path.join(SETS, n)
        if (jload(os.path.join(d, "manifest.json")) or {}).get("preset") == name and not (jload(os.path.join(d, "session.json")) or {}).get("start"):
            return {"name": n, "title": m["title"], "reused": True}
    k = 1
    while os.path.exists(os.path.join(SETS, f"{name}-{k}")): k += 1
    copy = f"{name}-{k}"
    if not NAME_RE.fullmatch(copy): raise HTTPError(400, f"preset name {name!r} is too long to copy")
    with open(path, "rb") as f: r = importer.do_import(f.read(), name=copy, preset=name)
    return r | {"reused": False}
