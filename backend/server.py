"""Interview Lab API on Flask, served by Waitress: routes and request guards only. Contract: API.md. Data layout: FORMAT.md."""
import json, os, sys, threading, traceback
from flask import Flask, Response, jsonify, request
from waitress import serve
from werkzeug.exceptions import HTTPException

from lab import catalog, importer, rounds
from sandbox import images, lsp, runner
from lab.store import EXPORTS, NAME_RE, SETS, HTTPError, clock, manifest, ready_info, require_started, sdir, session, state, work_path

PORT = os.environ.get("ILAB_PORT", "8765")   # the port nginx publishes; the Host/Origin allowlist follows it
HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
ORIGINS = {"http://" + h for h in HOSTS}
MAX_FILE = 1 << 20

app = Flask(__name__)
app.json.sort_keys = False


def body(limit):
    request.max_content_length = limit   # 413 for oversized bodies, chunked ones included
    return request.get_data(cache=False)


@app.before_request
def guard():
    if request.headers.get("Host") not in HOSTS: raise HTTPError(403, "forbidden host")
    if request.headers.get("X-ILab") != "1": raise HTTPError(403, "missing X-ILab header")
    o = request.headers.get("Origin")
    if o is not None and o not in ORIGINS: raise HTTPError(403, "forbidden origin")


@app.after_request
def no_store(r):
    r.headers["Cache-Control"] = "no-store"
    print(request.method, request.full_path.rstrip("?"), file=sys.stderr)
    return r


def err(code, msg): return jsonify(error=msg), code


@app.errorhandler(HTTPError)
def _app_error(e): return err(e.code, str(e))


@app.errorhandler(HTTPException)
def _http_errors(e):   # unknown route or wrong method: 404 as before; 413 etc. keep their code
    return err(404, "not found") if e.code in (404, 405) else err(e.code, e.description)


@app.errorhandler(runner.DockerError)
def _docker(e): return err(503, str(e))


@app.errorhandler(ValueError)
@app.errorhandler(KeyError)
def _bad(e): traceback.print_exc(); return err(400, f"bad request: {e}")


@app.errorhandler(Exception)
def _internal(e): traceback.print_exc(); return err(500, f"internal error: {e}")


@app.get("/api/health")
def r_health(): return images.health()


@app.post("/api/import")
def r_import(): return importer.do_import(body(importer.MAX_ZIP))


@app.get("/api/catalog")
def r_catalog(): return catalog.listing()


@app.post("/api/catalog/<n>/attempt")
def r_attempt(n): return catalog.start_attempt(n, json.loads(body(MAX_FILE) or b"{}").get("language"))


@app.get("/api/sets")
def r_sets():
    os.makedirs(SETS, exist_ok=True)
    out = []
    for n in sorted(os.listdir(SETS)):
        if NAME_RE.fullmatch(n) and os.path.isfile(os.path.join(SETS, n, "manifest.json")):
            i = ready_info(n)
            left = round(clock(session(n))[1] * 60) if i["status"] == "running" else None   # same rule as state.left_s
            out.append({k: i[k] for k in ("name", "title", "language", "round", "minutes", "status")} | {"left_s": left, "problem": catalog.problem_of(manifest(n))})
    return {"sets": out}


@app.get("/api/sets/<n>")
def r_set(n): sdir(n); return ready_info(n)


@app.route("/api/sets/<n>/files/<path:rel>", methods=["GET", "PUT"])
def r_files(n, rel):
    sdir(n); require_started(n)
    p = work_path(n, rel)
    if request.method == "GET":
        if not os.path.isfile(p): raise HTTPError(404, "no such file")
        return Response(open(p, "rb").read(), mimetype="text/plain; charset=utf-8")
    data = body(MAX_FILE)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f: f.write(data)
    lsp.file_saved(n, os.path.relpath(p, os.path.realpath(os.path.join(sdir(n), "work"))), data)
    return {"ok": True}


@app.post("/api/sets/<n>/assist")
def r_assist(n):
    sdir(n)
    b = json.loads(body(MAX_FILE + 4096) or b"{}")
    op = b.get("op")
    if op not in lsp.OPS and op not in ("check", "stop"): raise HTTPError(400, "bad op")
    if op == "stop": lsp.stop(n); return {"state": "stopped"}
    require_started(n)
    if not isinstance(b.get("file"), str): raise HTTPError(400, "bad path")
    rel = os.path.relpath(work_path(n, b.get("file")), os.path.realpath(os.path.join(sdir(n), "work")))
    text = b.get("text")
    if text is not None and (not isinstance(text, str) or len(text) > MAX_FILE): raise HTTPError(400, "bad text")
    line, col = b.get("line", 0), b.get("col", 0)
    if not all(isinstance(x, int) and 0 <= x < 10**7 for x in (line, col)): raise HTTPError(400, "bad position")
    return lsp.call(n, manifest(n)["language"], op, rel, text, line, col, b.get("item"))


@app.get("/api/sets/<n>/state")
def r_state(n): sdir(n); require_started(n); return state(n)


@app.post("/api/sets/<n>/run")
def r_run(n): sdir(n); return rounds.run(n, json.loads(body(MAX_FILE) or b"{}"))


ACTIONS = {"start": rounds.start, "mytests": rounds.mytests, "submit": rounds.submit, "next": rounds.next_part, "end": rounds.end}


@app.post("/api/sets/<n>/<act>")
def r_action(n, act):
    sdir(n)
    if act not in ACTIONS: raise HTTPError(404, "not found")
    return ACTIONS[act](n)


@app.delete("/api/sets/<n>")
def r_delete(n): sdir(n); return rounds.delete(n)


@app.get("/api/sets/<n>/export")
def r_export(n):
    sdir(n)
    return Response(rounds.export(n), mimetype="application/zip", headers={"Content-Disposition": 'attachment; filename="export.zip"'})


if __name__ == "__main__":
    os.makedirs(SETS, exist_ok=True); os.makedirs(EXPORTS, exist_ok=True)
    threading.Thread(target=images.image_keeper, daemon=True).start()
    print("Interview Lab backend on :8000", flush=True)
    # ponytail: one process, 32 threads; the per-set locks and IMG_STATE live in memory, so never add workers.
    serve(app, host="0.0.0.0", port=8000, threads=32, channel_timeout=900)
