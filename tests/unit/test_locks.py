"""While a Run/Submit holds run_lock: a second one and a delete are refused (409); after it, delete works.
Run: python3 tests/unit/test_locks.py"""
import json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
from lab import rounds, store  # noqa: E402

d = os.path.join(os.environ["ILAB_DATA"], "sets", "s")
os.makedirs(d)
json.dump({"name": "s", "title": "s", "minutes": 30}, open(f"{d}/manifest.json", "w"))


def code(fn):
    try: fn(); return 200
    except store.HTTPError as e: return e.code


assert store.run_lock("s") is store.run_lock("s") and store.run_lock("s") is not store.lock("s")
with store.run_lock("s"):
    assert code(lambda: rounds.busy("s")) == 409
    assert code(lambda: rounds.delete("s")) == 409
assert code(lambda: rounds.delete("s")) == 200 and not os.path.exists(d)
print("PASS run_lock refuses a second Run/Submit and a delete while held")
