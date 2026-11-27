"""The backend imports from a plain checkout: pack.validate comes from tools/pack.py and the built-in catalog is the
repo's catalog/, with no Dockerfile copy step. Needs Flask. Run: python3 tests/unit/test_checkout_imports.py"""

import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
code = f"""
import sys; sys.path.insert(0, {os.path.join(ROOT, "backend")!r})
import server
from lab import catalog, importer
print(importer.pack.__file__, catalog.BUILTIN, len(catalog.problems()))
"""
env = {k: v for k, v in os.environ.items() if k != "ILAB_CATALOG"} | {"ILAB_DATA": tempfile.mkdtemp()}
r = subprocess.run([sys.executable, "-I", "-c", code], cwd=tempfile.mkdtemp(), env=env, capture_output=True, text=True)
assert r.returncode == 0, r.stderr[-500:]
pack_file, builtin, n = r.stdout.split()
assert (
    pack_file == os.path.join(ROOT, "tools", "pack.py") and builtin == os.path.join(ROOT, "catalog") and int(n) > 0
), r.stdout
print(f"PASS a checkout imports the backend: pack from tools/, {n} built-in problems from catalog/")
