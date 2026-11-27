"""POST /api/import: validate an interview-set/1 zip, unpack it as an attempt in data/sets/<name>/ and save the problem
to the user's catalog (data/catalog/<name>/) so it can be taken again (spec: FORMAT.md)."""

import importlib.util
import io
import json
import os
import re
import shutil
import uuid
import zipfile

from lab import catalog
from lab.errors import Conflict, Invalid
from lab.store import ROOT, SETS, jload, jsave, lock

# tools/pack.py stays one standalone script (SKILL.md embeds it byte for byte), so its validate() is loaded from there
_spec = importlib.util.spec_from_file_location("pack", os.path.join(ROOT, "tools", "pack.py"))
pack = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pack)

MAX_ZIP, MAX_FILES, MAX_UNPACKED = 50 << 20, 2000, 50 << 20
DROP = ("reference/", "mutants.json", "bugs.json")  # never unpacked: the answers stay with Claude


def do_import(body):
    if len(body) > MAX_ZIP:
        raise Invalid("zip is larger than 50 MB")
    try:
        z = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile:
        raise Invalid("not a zip file")
    infos = z.infolist()
    if len(infos) > MAX_FILES:
        raise Invalid(f"zip has more than {MAX_FILES} entries")
    if sum(i.file_size for i in infos) > MAX_UNPACKED:
        raise Invalid("zip unpacks to more than 50 MB")
    for i in infos:
        nm = i.filename
        parts = nm.split("/")
        if nm.startswith("/") or "\\" in nm or ".." in parts or re.match(r"^[A-Za-z]:", nm) or "\x00" in nm:
            raise Invalid(f"unsafe path in zip: {nm!r}")
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            raise Invalid(f"symlink in zip: {nm!r}")
    names = [i.filename for i in infos if not i.is_dir()]
    prefix = ""
    if "manifest.json" not in names:
        tops = {x.split("/")[0] for x in names}
        if len(tops) == 1 and f"{next(iter(tops))}/manifest.json" in names:
            prefix = next(iter(tops)) + "/"
        else:
            raise Invalid("manifest.json not found at the top of the zip")
    keep = {}
    for i in infos:
        if i.is_dir():
            continue
        rel = i.filename[len(prefix) :]
        if rel.startswith(DROP) or rel in DROP:
            continue  # reference/, mutants.json, bugs.json are deleted
        if rel in ("manifest.json", "problem.md") or rel.startswith(("starter/", ".hidden/")):
            keep[rel] = i
    try:
        m = json.loads(z.read(keep["manifest.json"]))
    except ValueError, KeyError:
        raise Invalid("manifest.json is not valid JSON")
    errs = pack.validate(
        m,
        lambda p: p in keep or (p.endswith("/") and any(k.startswith(p) for k in keep)),
        read=lambda p: z.read(keep[p]),
    )
    if errs:
        raise Invalid(
            "This zip is not a valid Interview Lab set. Ask Claude to pack it again. Details: " + "; ".join(errs)
        )
    n = m["name"]
    dest = os.path.join(SETS, n)
    with lock(n):
        s = jload(os.path.join(dest, "session.json"))
        if s and s.get("start"):
            raise Conflict(f"You already started {n}, so it can't be replaced. Ask Claude for a copy with a new name.")
        replaced = os.path.isdir(dest)  # an unstarted copy is about to be replaced
        tmp = os.path.join(SETS, f".import-{uuid.uuid4().hex}")
        try:
            total = 0
            for rel, i in keep.items():
                p = os.path.realpath(os.path.join(tmp, rel))
                if not p.startswith(os.path.realpath(tmp) + os.sep):
                    raise Invalid(f"unsafe path in zip: {rel!r}")
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with z.open(i) as src, open(p, "wb") as out:
                    while chunk := src.read(1 << 16):
                        total += len(chunk)
                        if total > MAX_UNPACKED:
                            raise Invalid("zip unpacks to more than 50 MB")
                        out.write(chunk)
            jsave(os.path.join(tmp, "manifest.json"), m | {"problem": n})
            shutil.copytree(os.path.join(tmp, "starter"), os.path.join(tmp, "work"))
            shutil.rmtree(dest, ignore_errors=True)
            os.replace(tmp, dest)
            catalog.save_custom(dest, n)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return {"name": n, "title": m["title"], "replaced": replaced}
