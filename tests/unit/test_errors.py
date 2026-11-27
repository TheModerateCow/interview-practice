"""Lab refusals keep their HTTP statuses (403/404/409/400), and nothing under backend/lab/ knows HTTP.
Needs Flask (pip install -r backend/requirements.txt). Run: python3 tests/unit/test_errors.py"""
import glob, json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
import server  # noqa: E402

H = {"Host": "127.0.0.1:8765", "X-ILab": "1"}
c = server.app.test_client()
d = os.path.join(os.environ["ILAB_DATA"], "sets", "s")
os.makedirs(f"{d}/work")
json.dump({"name": "s", "title": "s", "minutes": 30}, open(f"{d}/manifest.json", "w"))

for method, path, headers, want in [
        ("GET", "/api/sets/s", {"Host": "evil.com", "X-ILab": "1"}, (403, "forbidden host")),
        ("GET", "/api/sets/nope", H, (404, "no set named")),
        ("GET", "/api/sets/s/state", H, (409, "not started")),
        ("POST", "/api/catalog/nope/attempt", H, (404, "no problem named")),
        ("POST", "/api/import", H, (400, "not a zip file"))]:
    r = c.open(path, method=method, headers=headers, data=b"x" if path.endswith("import") else None)
    got = (r.status_code, r.get_json()["error"])
    assert got[0] == want[0] and got[1].startswith(want[1]), (path, got)
print("PASS refusals keep their statuses and messages")

for f in glob.glob(os.path.join(ROOT, "backend/lab/**/*.py"), recursive=True):
    src = open(f).read()
    assert not any(w in src for w in ("HTTPError", "flask", "werkzeug")), f
print("PASS backend/lab/ does not know HTTP")
