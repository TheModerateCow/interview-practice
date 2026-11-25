# Interview Lab

A local, Docker-only app for timed coding-interview practice. Claude (`/interview-practice`) sends you a set `.zip`.
Drag it onto http://127.0.0.1:8765, read the ready screen, press **Start**. Run, Submit, Next part, End, then Export.
Send `export.zip` back to Claude for the debrief.

## Install / remove
```
./install.sh      # docker compose up -d --build, pre-pulls runner images, adds an "Interview Lab" launcher
./uninstall.sh    # removes containers, built images, the Go cache volume and the launcher; KEEPS data/
                  # --images also removes the pinned base images
```
The services restart by themselves after a reboot or a Docker restart (`restart: unless-stopped`).

## How it fits together
```
browser ──127.0.0.1:8765──> nginx (UI: Svelte + Monaco + marked, built at image build; offline; CSP) ──/api──> backend (Python, Flask on Waitress)
                                                                            │ DOCKER_HOST=tcp://docker-proxy:2375
                                                       docker-socket-proxy (CONTAINERS, IMAGES, POST only)
                                                                            │
                         one runner container per Run / Submit: --network none, read-only root, tmpfs /tmp 256m,
                         512 MB, 2 CPUs, 256 pids, cap-drop ALL, no-new-privileges, auto-removed.
                         Code in / results out as tar.gz over the attach stream; no bind mounts.
```
Only nginx publishes a port. The backend and proxy sit on internal networks. `/api` needs `X-ILab: 1` plus the
127.0.0.1/localhost Host, and it rejects any foreign Origin.

| Path | What |
|---|---|
| `FORMAT.md` | The interview-set/1 zip + manifest spec, the runner images, and what the app writes |
| `API.md` | The HTTP API |
| `backend/server.py` | API, import, session/clock, reveal logic, export |
| `backend/runner.py` | DockerRunner (Run: verdicts, time, memory) + the pinned runner image list |
| `backend/grade.py` | Hidden-test grading in the runner, with the same CLI/JSON as the skill's grade.py |
| `backend/gate.py` | The skill's gate.py, unchanged |
| `tools/pack.py` | Packs a set dir into a zip (refuses reference/, mutants.json, bugs.json) |
| `tools/status.py` | `python3 tools/status.py data/sets/<name>` → time left, from session.json |
| `data/` | Your sets, sessions and exports (bind-mounted; never deleted by uninstall) |

## Building a set by hand
```
docker compose run --rm -T -v "$PWD/<set>:/set:ro" backend python3 gate.py /set     # must print GATE PASS
python3 tools/pack.py <set> ~/Downloads/<name>.zip
```
Re-grade an export (unzipped into `<export>`, with the set folder `<set>` that holds the hidden tests; `final/` is the code at the close, `submission/` the latest code, older exports have only `submission/`): `docker compose run --rm -T -v <export>:/c:ro -v <set>:/s:ro backend python3 grade.py /c/final /s/<hidden tests file> -k test_l1_ --names`.

## Tests
`tests/run_all.sh [--clean]`: gates every set in `tests/sets/`, then runs `tests/api_test.py` (all 7 languages,
TLE/MLE/fork bomb/no network/read-only/truncation, leak check, grading flows, import validation, security), then
`tests/e2e.sh` (Playwright: a real drop event → ready → Start → Run → Submit → reveal → End → Export).

Tests never touch the stack you use or `data/`. `run_all.sh` builds a separate stack from the checkout it runs in
(compose project `ilab-test` on 127.0.0.1:8766, an empty data folder in `tests/out/stack-data`, its own images, runners
and Go cache) and removes it at the end. To run one suite by hand: `tests/stack.sh up`, then `python3 tests/api_test.py`
or `tests/e2e.sh`, then `tests/stack.sh down`.
