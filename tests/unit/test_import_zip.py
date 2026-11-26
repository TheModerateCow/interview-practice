"""importer.do_import: a good zip becomes an attempt and a custom catalog problem without its answers; unsafe zips are
refused before anything is written. Run: python3 tests/unit/test_import_zip.py"""
import io, os, sys, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = DATA = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
try: from lab import pack  # noqa: F401
except ImportError:  # in the image tools/pack.py is copied into lab/; in a checkout it isn't
    sys.path.insert(0, os.path.join(ROOT, "tools")); import pack; sys.modules["lab.pack"] = pack
from lab import importer  # noqa: E402

ZIPS = os.path.join(ROOT, "tests/sets/_zips")


def refused(data, want):
    try: importer.do_import(data)
    except Exception as e:
        assert getattr(e, "code", None) == 400 or type(e).__name__ == "Invalid", e
        assert want in str(e), (want, str(e)); return
    raise AssertionError(f"accepted a zip that should fail: {want}")


def mkzip(entries, mode=None):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for name, data in entries.items():
            zi = zipfile.ZipInfo(name)
            if mode: zi.external_attr = mode << 16
            z.writestr(zi, data)
    return b.getvalue()


refused(b"not a zip", "not a zip file")
refused(open(os.path.join(ZIPS, "evil-zipslip.zip"), "rb").read(), "unsafe path in zip")
refused(mkzip({"/etc/x": "a"}), "unsafe path in zip")
refused(mkzip({"C:/x": "a"}), "unsafe path in zip")
refused(mkzip({"manifest.json": "{}", "starter/l": "/etc/passwd"}, 0o120777), "symlink in zip")
refused(mkzip({"starter/a.py": ""}), "manifest.json not found")
refused(open(os.path.join(ZIPS, "invalid-bad-manifest.zip"), "rb").read(), "not a valid Interview Lab set")
assert not os.path.exists(os.path.join(DATA, "sets")) or os.listdir(os.path.join(DATA, "sets")) == []
print("PASS unsafe and invalid zips are refused and leave nothing behind")

z = open(os.path.join(ZIPS, "mini-go.zip"), "rb").read()
extra = io.BytesIO(z)
with zipfile.ZipFile(extra, "a") as zz: zz.writestr("reference/merge.go", "answer"); zz.writestr("mutants.json", "[]")
r = importer.do_import(extra.getvalue())
assert r == {"name": "mini-go", "title": "Merge intervals (Go)", "replaced": False}, r
s = os.path.join(DATA, "sets", "mini-go")
assert os.path.isfile(f"{s}/work/merge.go") and os.path.isfile(f"{s}/.hidden/hidden_test.go")
assert not os.path.exists(f"{s}/reference") and not os.path.exists(f"{s}/mutants.json")
assert os.path.isfile(os.path.join(DATA, "catalog", "mini-go", "manifest.json"))
assert importer.do_import(z)["replaced"] is True   # an unstarted attempt is replaced
print("PASS a good zip becomes an attempt + catalog problem, answers dropped")
