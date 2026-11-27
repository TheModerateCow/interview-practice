"""Opening a problem again rebuilds its unstarted attempt from the catalog as it is now (a catalog update reaches it);
a started attempt is never touched. Run: python3 tests/unit/test_ready_attempt_refresh.py"""

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = DATA = tempfile.mkdtemp()
os.environ["ILAB_CATALOG"] = CAT = tempfile.mkdtemp()
shutil.copytree(os.path.join(ROOT, "catalog", "banking-levelled"), os.path.join(CAT, "bank"))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import catalog, rounds  # noqa: E402


def statement(n):
    return open(os.path.join(DATA, "sets", n, "problem.md")).read()


def update_catalog(text):
    with open(os.path.join(CAT, "bank", "problem.md"), "a") as f:
        f.write(text)


a = catalog.start_attempt("bank", "python")
assert a["reused"] is False and "v2 of the statement" not in statement(a["name"])
update_catalog("\nv2 of the statement\n")  # e.g. the image was rebuilt with a fixed problem
b = catalog.start_attempt("bank", "python")
assert b["name"] == a["name"] and b["reused"] is True and "v2 of the statement" in statement(b["name"]), b
assert not [x for x in os.listdir(os.path.join(DATA, "sets")) if x.startswith(".")]  # no temp folders left
print("PASS an unstarted attempt picks up a catalog update")

rounds.start(b["name"])
update_catalog("\nv3 of the statement\n")
c = catalog.start_attempt("bank", "python")
assert c["name"] == b["name"] and "v3 of the statement" not in statement(c["name"]), c
print("PASS a started attempt keeps the problem it started with")
