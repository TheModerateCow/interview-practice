"""Code help: one language server per open round, in a runner-shaped container, spoken to over the attach stream.

The container is the runner's (LOCKED: no network, read-only root, 512 MB, ...), started through the same socket proxy.
It only ever sees the files the Files pane lists (store.work_files), never .hidden/. Design: docs/rounds/5-editor-intellisense/HLD.md
"""
import json, re, struct, sys, threading, time

from lab import store
from sandbox import runner

SERVERS = {   # language -> command, source extension, files for the server's workspace only, answers to workspace/configuration
    # Debug (Codebase) rounds plant bugs the type checker would underline, so type checking is off there: completion, hover and
    # signatures stay, syntax errors and undefined names still show. /opt/site holds pytest, as in the runner image.
    "python": dict(cmd="pyright-langserver --stdio", ext=".py", settings={},
                   extra=lambda rnd: {"pyrightconfig.json": json.dumps({"pythonVersion": "3.15", "extraPaths": ["/opt/site"],
                                                                        "typeCheckingMode": "off" if rnd == "codebase" else "basic"}).encode()}),
}
OPS = {"complete": "textDocument/completion", "resolve": "completionItem/resolve",
       "hover": "textDocument/hover", "signature": "textDocument/signatureHelp"}
W = "/tmp/w"
BOOT = 'mkdir -p /tmp/w && cd /tmp/w && head -c "$ILAB_N" | tar xz && exec '   # same stdin handover as a Run
IDLE_S, PING_S, RETRY_S = 30 * 60, 4 * 60, 30   # stop after idle; keepalive (the proxy cuts a silent stream at 10 min); retry after failure
CAPS = {"textDocument": {
    "completion": {"completionItem": {"snippetSupport": True, "documentationFormat": ["markdown", "plaintext"]}},
    "hover": {"contentFormat": ["markdown", "plaintext"]},
    "signatureHelp": {"signatureInformation": {"documentationFormat": ["markdown", "plaintext"]}},
    "publishDiagnostics": {"versionSupport": True}, "synchronization": {}},
    "workspace": {"configuration": True, "workspaceFolders": True}}


def clean(x):
    """Paths and links never leave: container paths are cut to Files paths, Markdown links become their text."""
    if isinstance(x, str): return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", x.replace("file://" + W + "/", "").replace(W + "/", ""))
    if isinstance(x, list): return [clean(i) for i in x]
    if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
    return x


class Session:
    """One container. state: starting | ready | unavailable."""

    def __init__(self, n, lang):
        self.n, self.lang, self.cfg = n, lang, SERVERS[lang]
        self.state, self.reason, self.failed_at = "starting", "", 0
        self.cid, self.sock, self.last = None, None, time.time()
        self.cv, self.wlock = threading.Condition(), threading.Lock()
        self.pending, self.diags, self.docs, self.nid = {}, {}, {}, 0
        self.seq, self.synced = 0, {}   # diagnostics without a version (jdtls) count only if published after the last sync
        self.stopping = threading.Event()
        threading.Thread(target=self._boot, daemon=True).start()

    def _fail(self, reason):
        with self.cv:
            if self.state != "unavailable": self.state, self.reason, self.failed_at = "unavailable", reason, time.time()
            self.cv.notify_all()
        self.kill()

    def _boot(self):
        try:
            files = store.work_files(self.n) | self.cfg["extra"](store.manifest(self.n).get("round"))
            payload = runner._tar(files)
            body = {"Image": runner.LSP_IMAGES[self.lang], "Entrypoint": ["sh", "-c", BOOT + self.cfg["cmd"]], "Cmd": [],
                    "Env": runner.BASE_ENV + [f"ILAB_N={len(payload)}"], "WorkingDir": "/tmp",
                    "OpenStdin": True, "StdinOnce": True, "AttachStdin": True, "AttachStdout": True, "AttachStderr": True,
                    "Tty": False, "Labels": {"ilab.lsp": runner.INSTANCE}, "HostConfig": dict(runner.LOCKED)}
            try: self.cid = runner.api("POST", "/containers/create", body)["Id"]
            except runner.DockerError as e:
                if "-> 404" in str(e): raise runner.DockerError("The code-help image is missing. Run ./install.sh to build it.")
                raise
            self.sock, rest = runner._attach(self.cid, 30)
            self.sock.settimeout(None)
            threading.Thread(target=self._read, args=(rest,), daemon=True).start()
            runner.api("POST", f"/containers/{self.cid}/start")
            self.sock.sendall(payload)
            ok = self.request("initialize", {"processId": None, "rootUri": "file://" + W, "capabilities": CAPS,
                                             "workspaceFolders": [{"uri": "file://" + W, "name": "w"}]}, 30, raw=True)
            if ok is None: raise runner.DockerError("The language server did not start.")
            self._send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
            self.state = "ready"
            threading.Thread(target=self._watch, daemon=True).start()
        except Exception as e:
            print("code help:", e, file=sys.stderr)
            self._fail(str(e) if isinstance(e, runner.DockerError) else "The language server could not start.")

    # ---- wire: LSP frames inside Docker's multiplexed attach stream (8-byte header: kind, 0, 0, 0, length)
    def _send(self, msg):
        b = json.dumps(msg).encode()
        with self.wlock: self.sock.sendall(b"Content-Length: %d\r\n\r\n" % len(b) + b)

    def _read(self, buf):
        out, buf = bytearray(), bytearray(buf)
        try:
            while True:
                while len(buf) >= 8 and len(buf) >= 8 + struct.unpack(">I", buf[4:8])[0]:
                    n = struct.unpack(">I", buf[4:8])[0]
                    if buf[0] == 1: out.extend(buf[8:8 + n])
                    del buf[:8 + n]
                while True:
                    h = out.find(b"\r\n\r\n")
                    m = re.match(rb"Content-Length: *(\d+)", out[:h], re.I) if h >= 0 else None
                    if not m or len(out) < h + 4 + int(m[1]): break
                    msg = json.loads(out[h + 4:h + 4 + int(m[1])]); del out[:h + 4 + int(m[1])]
                    self._on(msg)
                chunk = self.sock.recv(1 << 16)
                if not chunk: break
                buf.extend(chunk)
        except (OSError, ValueError): pass
        if not self.stopping.is_set(): self._fail("The language server stopped.")

    def _on(self, msg):
        with self.cv:
            if "method" not in msg:
                self.pending[msg.get("id")] = msg; self.cv.notify_all()
            elif msg["method"] == "textDocument/publishDiagnostics":
                self.seq += 1; p = msg["params"]; self.diags[p["uri"]] = (p.get("version"), p["diagnostics"], self.seq); self.cv.notify_all()
        if "id" in msg and "method" in msg:   # a request from the server: answer, the settings if it asks for them
            items = msg.get("params", {}).get("items", []) if msg["method"] == "workspace/configuration" else None
            try: self._send({"jsonrpc": "2.0", "id": msg["id"], "result": None if items is None else [self.cfg["settings"].get(i.get("section")) for i in items]})
            except OSError: pass

    def request(self, method, params, timeout=2.5, raw=False):
        """The result, or None on timeout / error (a timed-out request is cancelled). raw: True for a null result too."""
        with self.cv:
            self.nid += 1; i = self.nid
        try: self._send({"jsonrpc": "2.0", "id": i, "method": method, "params": params})
        except OSError: return None
        with self.cv:
            got = self.cv.wait_for(lambda: i in self.pending, timeout)
            msg = self.pending.pop(i, None)
        if not got:
            try: self._send({"jsonrpc": "2.0", "method": "$/cancelRequest", "params": {"id": i}})
            except OSError: pass
            return None
        if "error" in msg: return None
        return True if raw and msg.get("result") is None else msg.get("result")

    # ---- documents
    def sync(self, rel, text):
        """Tell the server this file's text: didOpen the first time, then didChange (full text) when it differs."""
        uri = f"file://{W}/{rel}"
        with self.cv:
            v, old = self.docs.get(rel, (0, None))
            if old == text: return v
            self.docs[rel] = (v + 1, text); self.synced[f"file://{W}/{rel}"] = self.seq
        if v == 0:
            self._send({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {"uri": uri, "languageId": self.lang, "version": 1, "text": text}}})
        else:
            self._send({"jsonrpc": "2.0", "method": "textDocument/didChange", "params": {"textDocument": {"uri": uri, "version": v + 1}, "contentChanges": [{"text": text}]}})
        return v + 1

    def diagnostics(self, rel, wait=2.0):
        uri, v = f"file://{W}/{rel}", self.docs[rel][0]
        with self.cv:
            fresh = lambda d: bool(d) and (d[0] == v or (d[0] is None and d[2] > self.synced.get(uri, 0)))
            self.cv.wait_for(lambda: fresh(self.diags.get(uri)) or self.state != "ready", wait)
            d = self.diags.get(uri)
        return d[1] if fresh(d) else None

    def _watch(self):
        last_ping = time.time()
        while not self.stopping.wait(5):
            if time.time() - self.last > IDLE_S: return stop(self.n)
            if time.time() - last_ping > PING_S:   # a round trip both ways, so the proxy's idle timeout never fires
                self.request("$/ilab/ping", {}, 5, raw=True); last_ping = time.time()

    def kill(self):
        self.stopping.set()
        if self.cid:
            try: runner.api("POST", f"/containers/{self.cid}/kill")
            except runner.DockerError: pass   # already gone (AutoRemove)
        try: self.sock and self.sock.close()
        except OSError: pass


_s, _lock = None, threading.Lock()
# ponytail: one session per app (module global + lock); the app is single-user. Per-set sessions if that changes.


def call(n, lang, op, rel, text=None, line=0, col=0, item=None):
    global _s
    if lang not in SERVERS or not rel.endswith(SERVERS[lang]["ext"]): return {"state": "unsupported"}
    with _lock:
        if _s and (_s.n != n or (_s.state == "unavailable" and time.time() - _s.failed_at > RETRY_S)): _s.kill(); _s = None
        if not _s: _s = Session(n, lang)
        s = _s
    s.last = time.time()
    if s.state != "ready": return {"state": s.state} | ({"reason": s.reason} if s.reason else {})
    try:
        if text is not None: s.sync(rel, text)
        pos = {"textDocument": {"uri": f"file://{W}/{rel}"}, "position": {"line": line, "character": col}}
        if op == "check":
            if rel not in s.docs: return {"state": "ready", "diagnostics": []}
            d = s.diagnostics(rel)
            if d is None: return {"state": s.state}   # nothing published for this text yet: say nothing, never a false "no errors"
            return {"state": "ready", "diagnostics": clean(d)}
        res = s.request(OPS[op], item if op == "resolve" else pos)
    except OSError: return {"state": "unavailable", "reason": "The language server stopped."}
    return {"state": "ready", "result": clean(res)}


def file_saved(n, rel, data):
    """A file saved through the Files API shows up in the live session's other files."""
    s = _s
    if s and s.n == n and s.state == "ready" and rel.endswith(s.cfg["ext"]):
        try: s.sync(rel, data.decode(errors="replace"))
        except OSError: pass


def stop(n=None):
    """Leave the round, delete the set, idle, shutdown. n: only if the session is for that set."""
    global _s
    with _lock:
        if _s and (n is None or _s.n == n): _s.kill(); _s = None


def sweep():
    """At startup: remove language-server containers left by a crash."""
    for c in runner.api("GET", '/containers/json?all=1&filters={"label":["ilab.lsp=%s"]}' % runner.INSTANCE) or []:
        try: runner.api("DELETE", f"/containers/{c['Id']}?force=1")
        except runner.DockerError: pass
