"""Every case's "data" file (cases/data/*.json, the large hidden cases) is tracked in git, and a missing one fails the
render by name instead of reaching the harness as None. Run: python3 tests/unit/test_case_data.py"""

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import variants  # noqa: E402

refs = set()
for cf in glob.glob(f"{ROOT}/catalog/*/cases/*.json") + glob.glob(f"{ROOT}/tests/fixture/cases/*.json"):
    for c in json.load(open(cf)):
        if c.get("data"):
            refs.add(os.path.relpath(os.path.join(os.path.dirname(cf), c["data"]), ROOT))
tracked = set(
    subprocess.run(["git", "ls-files", *sorted(refs)], cwd=ROOT, capture_output=True, text=True).stdout.split()
)
assert refs and refs == tracked, f"case data not in git (check .gitignore): {sorted(refs - tracked)}"
print(f"PASS all {len(refs)} case data files are tracked")

d = tempfile.mkdtemp()
shutil.copytree(os.path.join(ROOT, "tests/fixture"), f"{d}/fx")
os.remove(f"{d}/fx/cases/data/large.json")
try:
    variants.render(f"{d}/fx", "python")
    raise SystemExit("FAIL: rendered without its data file")
except ValueError as e:
    assert "cases/data/large.json missing" in str(e), e
print("PASS a missing data file fails the render by name")
