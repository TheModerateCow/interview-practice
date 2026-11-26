"""DockerRunner: every Run / test call is one throwaway container, started through docker-socket-proxy.

Code goes in as a tar.gz on stdin (attach before start), results come back as a tar.gz on stdout.
No bind mounts: the backend's paths are not host paths.
"""
import http.client, io, json, os, socket, struct, tarfile, threading
try: from sandbox.toolchains import TOOLCHAINS   # imported by the server
except ImportError: from toolchains import TOOLCHAINS   # grade.py run as a script

_hp = os.environ.get("DOCKER_HOST", "tcp://docker-proxy:2375").removeprefix("tcp://")
DHOST, DPORT = _hp.rsplit(":", 1)[0], int(_hp.rsplit(":", 1)[1])

IMAGES = {
    "python": os.environ.get("ILAB_IMG_PYTHON", "ilab-python:3.15.2-pytest9.2.0"),
    "go": os.environ.get("ILAB_IMG_GO", "golang:1.27.4"),
    "java": os.environ.get("ILAB_IMG_JAVA", "eclipse-temurin:21.0.13.1_2-jdk"),
    "c": os.environ.get("ILAB_IMG_GCC", "gcc:14.4.0"),
    "cpp": os.environ.get("ILAB_IMG_GCC", "gcc:14.4.0"),
    "javascript": os.environ.get("ILAB_IMG_NODE", "node:24.22.3-slim"),
    "typescript": os.environ.get("ILAB_IMG_NODE", "node:24.22.3-slim"),
}
GO_ENV = ["GOTOOLCHAIN=local", "GOFLAGS=-mod=mod", "GOCACHE=/gocache", "GOPATH=/tmp/gopath", "CGO_ENABLED=0"]
BASE_ENV = ["HOME=/tmp", "PYTHONDONTWRITEBYTECODE=1", "NODE_NO_WARNINGS=1"]
OUT_CAP = 65536  # bytes kept per stream per case
CASE_TL = 5      # seconds per Run case
# Unpack stdin (exactly ILAB_N bytes, so no half-close is needed through the proxy), run the harness
# under an overall limit, then stream /tmp/out back as tar.gz.
BOOT = ('mkdir -p /tmp/w /tmp/out && cd /tmp/w && head -c "$ILAB_N" | tar xz && '
        'timeout -k 2 "$ILAB_LIMIT" sh /tmp/w/_harness.sh >/tmp/out/_harness.log 2>&1; '
        'echo $? >/tmp/out/_rc; cd /tmp/out && tar cz .')
# One stack's runners and Go cache, kept apart from any other stack on the same Docker daemon (the test stack sets these).
INSTANCE = os.environ.get("ILAB_INSTANCE", "1")
GO_CACHE = os.environ.get("ILAB_GO_CACHE", "ilab-go-cache")
_sem = threading.Semaphore(int(os.environ.get("ILAB_PARALLEL", "3")))


class DockerError(Exception):
    """Docker or the proxy is unreachable / refused the call."""


def api(method, path, body=None, timeout=30, raw_body=False):
    c = http.client.HTTPConnection(DHOST, DPORT, timeout=timeout)
    try:
        data = json.dumps(body).encode() if body is not None else None
        c.request(method, path, body=data, headers={"Content-Type": "application/json"} if data else {})
        r = c.getresponse(); raw = r.read()
    except OSError as e:
        raise DockerError(f"Docker is unreachable through docker-proxy ({e}). Is the docker-proxy container running?")
    finally:
        c.close()
    if r.status >= 400:
        raise DockerError(f"Docker API {method} {path.split('?')[0]} -> {r.status}: {raw[:300].decode(errors='replace')}")
    if raw_body: return raw
    return json.loads(raw) if raw.strip() else None


def image_ready(img):
    try:
        api("GET", f"/images/{img}/json"); return True
    except DockerError as e:
        if "-> 404" in str(e): return False
        raise


def pull(img):
    repo, _, tag = img.rpartition(":") if ":" in img.split("/")[-1] else (img, "", "latest")
    # The response is a stream of JSON progress lines; failures arrive as {"error": ...} with status 200.
    for line in api("POST", f"/images/create?fromImage={repo}&tag={tag}", timeout=1800, raw_body=True).splitlines():
        try: msg = json.loads(line)
        except ValueError: continue
        if msg.get("error"): raise DockerError(f"pull {img}: {msg['error']}")


def sweep():
    """Remove runner containers left over from a crash."""
    for c in api("GET", '/containers/json?all=1&filters={"label":["ilab.runner=%s"]}' % INSTANCE) or []:
        try: api("DELETE", f"/containers/{c['Id']}?force=1")
        except DockerError: pass


def _tar(files):
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode="w:gz") as t:
        for name, data in files.items():
            if isinstance(data, str): data = data.encode()
            ti = tarfile.TarInfo(name); ti.size = len(data); ti.mode = 0o755 if name in ("prog",) else 0o644
            t.addfile(ti, io.BytesIO(data))
    return b.getvalue()


def _untar(data):
    out = {}
    if not data: return out
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        for m in t.getmembers():
            if m.isfile(): out[m.name.removeprefix("./")] = t.extractfile(m).read()
    return out


def _attach(cid, timeout):
    s = socket.create_connection((DHOST, DPORT), timeout=timeout)
    s.sendall((f"POST /containers/{cid}/attach?stream=1&stdin=1&stdout=1&stderr=1 HTTP/1.1\r\n"
               "Host: docker\r\nConnection: Upgrade\r\nUpgrade: tcp\r\nContent-Length: 0\r\n\r\n").encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(65536)
        if not chunk: raise DockerError("attach: connection closed")
        buf += chunk
    head, rest = buf.split(b"\r\n\r\n", 1)
    if b" 101 " not in head.split(b"\r\n")[0] and b" 200 " not in head.split(b"\r\n")[0]:
        raise DockerError("attach refused: " + head.split(b"\r\n")[0].decode(errors="replace"))
    return s, rest


def _demux(raw):
    out, err, i = bytearray(), bytearray(), 0
    while i + 8 <= len(raw):
        kind, n = raw[i], struct.unpack(">I", raw[i + 4:i + 8])[0]
        (out if kind == 1 else err).extend(raw[i + 8:i + 8 + n]); i += 8 + n
    return bytes(out), bytes(err)


def container(lang, files, harness, limit, env=()):
    """Run harness.sh over files in a fresh locked-down container. Returns ({name: bytes} from /tmp/out, timed_out)."""
    files = dict(files); files["_harness.sh"] = harness
    payload = _tar(files)
    hc = {"AutoRemove": True, "NetworkMode": "none", "ReadonlyRootfs": True,
          "Tmpfs": {"/tmp": "rw,exec,nosuid,size=256m"}, "Memory": 512 << 20, "MemorySwap": 512 << 20,
          "NanoCpus": 2_000_000_000, "PidsLimit": 256, "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"]}
    envs = BASE_ENV + [f"ILAB_N={len(payload)}", f"ILAB_LIMIT={int(limit)}"] + list(env)
    if lang == "go":
        hc["Mounts"] = [{"Type": "volume", "Source": GO_CACHE, "Target": "/gocache"}]
        envs += GO_ENV
    body = {"Image": IMAGES[lang], "Entrypoint": ["sh", "-c", BOOT], "Cmd": [], "Env": envs, "WorkingDir": "/tmp",
            "OpenStdin": True, "StdinOnce": True, "AttachStdin": True, "AttachStdout": True, "AttachStderr": True,
            "Tty": False, "Labels": {"ilab.runner": INSTANCE}, "HostConfig": hc}
    with _sem:
        try:
            cid = api("POST", "/containers/create", body)["Id"]
        except DockerError as e:
            if "No such image" in str(e) or "-> 404" in str(e):
                raise DockerError(f"Runner image {IMAGES[lang]} is missing. Run ./install.sh (or wait for the backend to finish pulling it).")
            raise
        timed_out = False
        try:
            s, raw = _attach(cid, limit + 20)
            api("POST", f"/containers/{cid}/start")
            s.sendall(payload)
            raw = bytearray(raw)
            try:
                while True:
                    chunk = s.recv(1 << 16)
                    if not chunk: break
                    raw.extend(chunk)
            except socket.timeout:
                timed_out = True
            s.close()
        finally:
            try: api("POST", f"/containers/{cid}/kill")
            except DockerError: pass  # already gone (AutoRemove) — the normal case
        out, err = _demux(bytes(raw))
    try:
        res = _untar(out)
    except (tarfile.TarError, EOFError, OSError):
        res = {}
    if err and "_harness.log" not in res: res["_harness.log"] = err
    return res, timed_out or res.get("_rc", b"").strip() in (b"124", b"137")


# ---------------------------------------------------------------- Run (stdin + testcases)

def _txt(b, cap=OUT_CAP):
    return (b or b"")[:cap].decode(errors="replace")


RUN_LOOP = r'''
oom() { sed -n 's/^oom_kill //p' /sys/fs/cgroup/memory.events 2>/dev/null || echo 0; }
i=0
while [ "$i" -lt "$NC" ]; do
  o=$(oom); t0=$(date +%s%N)
  ( timeout -k 1 "$TL" CMD < "/tmp/w/_cases/$i.in" 2>"/tmp/out/$i.err"; echo $? > "/tmp/out/$i.rc" ) | head -c CAP1 > "/tmp/out/$i.out"
  t1=$(date +%s%N); echo $(( (t1 - t0) / 1000000 )) > "/tmp/out/$i.ms"
  [ "$(oom)" != "$o" ] && touch "/tmp/out/$i.oom"
  head -c CAP1 "/tmp/out/$i.err" > /tmp/e && mv /tmp/e "/tmp/out/$i.err"
  i=$((i + 1))
done
cat /sys/fs/cgroup/memory.peak > /tmp/out/peak 2>/dev/null
'''


def run(lang, files, entry, stdins):
    """Compile (if needed) and run `entry` once per stdin. Returns {"compile": {...}|None, "cases": [...], "memory_kb"}."""
    tc = TOOLCHAINS[lang]
    if entry not in files: raise ValueError(f"{entry} not found")
    artifacts, compile_res = {}, None
    build = tc.build(entry, files)
    if build:
        script, files = build
        out, to = container(lang, files, script, 120)
        rc = out.get("compile.rc", b"1").strip()
        compile_res = {"ok": rc == b"0" and not to, "log": _txt(out.get("compile.log", b"") or out.get("_harness.log", b""))}
        if to: compile_res["log"] = "compilation did not finish in 120 s"
        if not compile_res["ok"]:
            return {"compile": compile_res, "cases": [], "memory_kb": None}
        artifacts = {k: v for k, v in out.items() if k == "prog" or k.startswith("classes/")}
    cmd = tc.run_cmd(entry, files)
    rfiles = dict(artifacts) if artifacts else dict(files)
    for i, s in enumerate(stdins): rfiles[f"_cases/{i}.in"] = s
    script = f"NC={len(stdins)}\nTL={CASE_TL}\n" + RUN_LOOP.replace("CMD", cmd).replace("CAP1", str(OUT_CAP + 1))
    out, to = container(lang, rfiles, script, len(stdins) * (CASE_TL + 3) + 20)
    cases = []
    for i in range(len(stdins)):
        rc_raw = out.get(f"{i}.rc", b"").strip()
        rc = int(rc_raw) if rc_raw.lstrip(b"-").isdigit() else None
        ms = int(out.get(f"{i}.ms", b"0").strip() or 0)
        so = out.get(f"{i}.out", b"")
        c = {"stdout": _txt(so), "stderr": _txt(out.get(f"{i}.err", b"")), "exit": rc, "ms": ms,
             "truncated": len(so) > OUT_CAP}
        if f"{i}.oom" in out: c["verdict"] = "Memory Limit Exceeded"
        elif rc == 124 or (rc is None and to): c["verdict"] = "Time Limit Exceeded"
        elif rc is None: c["verdict"] = "Runtime Error"; c["stderr"] = c["stderr"] or "the program was killed"
        elif rc == 0 or (c["truncated"] and rc == 141): c["verdict"] = "Accepted"
        else: c["verdict"] = "Runtime Error"
        cases.append(c)
    peak = out.get("peak", b"").strip()
    return {"compile": compile_res, "cases": cases, "memory_kb": int(peak) // 1024 if peak.isdigit() else None}

