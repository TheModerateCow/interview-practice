"""pack.validate (tools/pack.py, also the importer's check): a good manifest passes; each broken field is named.
Run: python3 tests/unit/test_pack_validate.py"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pack import validate  # noqa: E402

SET = os.path.join(ROOT, "tests/sets/mini-go")
good = json.load(open(os.path.join(SET, "manifest.json")))
files = {"problem.md", "starter/", "starter/cmd/run/main.go", ".hidden/hidden_test.go", ".hidden/p2.md"}
exists = lambda p: p in files  # noqa: E731
assert validate(good, exists) == [], validate(good, exists)
assert validate([1], exists) == ["manifest.json must be a JSON object"]
print("PASS a good manifest has no errors")

BAD = [
    ({"name": "Bad_Name"}, "name:"),
    ({"format": "interview-set/2"}, "format:"),
    ({"language": "cobol"}, "language:"),
    ({"language": "typescript"}, "language:"),
    ({"language": "javascript"}, "language:"),
    ({"minutes": 0}, "minutes:"),
    ({"minutes": True}, "minutes:"),
    ({"hidden_tests": "tests/hidden_test.go"}, "hidden_tests: must be a path under .hidden/"),
    ({"hidden_tests": ".hidden/x.py"}, "hidden_tests: .hidden/x.py missing"),
    ({"notes": "reference/x.go"}, "notes: must not point at reference/x.go"),
    ({"run_entry": "nope.go"}, "run_entry: starter/nope.go missing"),
    ({"reveal": [{"file": ".hidden/p2.md", "unlocks": "test_p9_"}]}, "reveal[0].unlocks: must be one of tags"),
]
for patch, want in BAD:
    errs = validate(good | patch, exists)
    assert any(e.startswith(want) for e in errs), (patch, errs)
print(f"PASS {len(BAD)} broken fields are each named")
