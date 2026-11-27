"""A real flow leaves no file unclosed (no ResourceWarning): render a catalog problem in each language, start an
attempt, poll state, read a file through the API, export. Needs Flask. Run: python3 tests/unit/test_files_closed.py"""

import gc
import os
import sys
import tempfile
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
os.environ["ILAB_CATALOG"] = os.path.join(ROOT, "catalog")
sys.path.insert(0, os.path.join(ROOT, "backend"))
try:
    from lab import pack  # noqa: F401
except ImportError:  # in the image tools/pack.py is copied into lab/; in a checkout it isn't
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import pack

    sys.modules["lab.pack"] = pack
import server  # noqa: E402
from lab import catalog, rounds, store, variants  # noqa: E402

H = {"Host": "127.0.0.1:8765", "X-ILab": "1"}
with warnings.catch_warnings(record=True) as seen:
    warnings.simplefilter("always", ResourceWarning)
    for lang in ("go", "java", "python"):
        variants.render(os.path.join(ROOT, "catalog", "banking-levelled"), lang)
    n = catalog.start_attempt("banking-levelled", "python")["name"]
    rounds.start(n)
    store.state(n)
    f = store.state(n)["files"][0]
    assert server.app.test_client().get(f"/api/sets/{n}/files/{f}", headers=H).status_code == 200
    rounds.export(n)
    gc.collect()
leaks = [str(w.message) for w in seen if issubclass(w.category, ResourceWarning)]
assert not leaks, leaks[:3]
print("PASS render, start, state, file read and export close every file")
