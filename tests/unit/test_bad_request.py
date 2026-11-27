"""Bad request bodies are 400s; a bug in our own code (a KeyError/ValueError) is a 500, not a "bad request".
Needs Flask (pip install -r backend/requirements.txt). Run: python3 tests/unit/test_bad_request.py"""
import json, os, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ILAB_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(ROOT, "backend"))
import server  # noqa: E402

H = {"Host": "127.0.0.1:8765", "X-ILab": "1"}
c = server.app.test_client()


def post(path, data):
    r = c.post(path, data=data, headers=H)
    return r.status_code, r.get_json()


def write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f: f.write(json.dumps(data))


d = os.path.join(os.environ["ILAB_DATA"], "sets")
write(f"{d}/ok/manifest.json", {"name": "ok", "minutes": 30})
write(f"{d}/ok/session.json", {"start": time.time(), "minutes": 30, "events": [], "ended": None, "unlocked": [], "revealed": []})
write(f"{d}/broken/manifest.json", {"name": "broken"})   # no "minutes": Start hits a KeyError in our code

for path, data, want in [("/api/catalog/x/attempt", b"not json", "not valid JSON"),
                         ("/api/catalog/x/attempt", b"[1]", "JSON object"),
                         ("/api/sets/ok/run", b"{\"file\": 5}", "must be strings")]:
    s, j = post(path, data)
    assert s == 400 and want in j["error"], (path, data, s, j)
print("PASS bad bodies -> 400 naming the problem")

s, j = post("/api/sets/broken/start", b"")
assert s == 500 and j["error"].startswith("internal error"), (s, j)
print("PASS a KeyError in our code -> 500, not 'bad request'")
