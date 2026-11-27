# Interview Lab

A local, Docker-only app for timed coding-interview practice. Claude (`/interview-practice`) sends you a set `.zip`.
Drag it onto http://127.0.0.1:8765. The app says "Imported <title> (<name>)" and shows the name under the title; press **Start** only if the name matches. If it says "Not imported", paste the message back to Claude. Run, Submit, Next part, End, then Export.
Send `export.zip` back to Claude for the debrief.

Home is a **catalog of problems** to pick from: the built-in ones in `catalog/` plus every set you've imported (marked Yours). Each built-in problem comes in Go, Java and/or Python: click the problem to open it in your usual language, or a language chip for another. Filter by round, language and difficulty. Picking opens your round in progress in that language, an unstarted attempt, or a fresh attempt (`<id>-<lang>-1`, `-2`, …) on the ready screen, so you can retake any problem. Past attempts stay listed under Not started / Finished.

To add a built-in problem or a language to one: `docs/rounds/3-language-variants/` (`CONTRACT.md` the format, `CONVERT.md`, `PORT.md`). Check it with `python3 tools/gate_problem.py catalog/<id> answers/<id>` (every language, in the runner images) and rebuild.

## Install / remove
```
deploy/install.sh      # docker compose up -d --build, pre-pulls runner images, adds an "Interview Lab" launcher
deploy/uninstall.sh    # removes containers, built images, the Go cache volume and the launcher; KEEPS data/
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
| `backend/server.py` | The HTTP layer: routes, the Host/Origin/X-ILab guard, error mapping |
| `backend/lab/` | `store.py` set files, session, clock and reveals; `catalog.py` problems and attempts; `importer.py` zip import; `rounds.py` Start/Run/Submit/My tests/Next/End/Export/Delete |
| `backend/sandbox/runner.py` | DockerRunner (Run: verdicts, time, memory) + the pinned runner image list |
| `backend/sandbox/grade.py` | Hidden-test grading in the runner, with the same CLI/JSON as the skill's grade.py |
| `backend/sandbox/gate.py` | The skill's gate.py, unchanged |
| `backend/sandbox/images.py` | `/api/health` and the thread that keeps runner images pulled |
| `ui/src/` | `App.svelte` the shell (header, screens, toasts); `nav.js` navigation between screens; `app.svelte.js` app-wide state; `features/` one folder per screen (`home`, `catalog`, `ready`, `round`, `import`, `health`), `round/round.svelte.js` holds the round's state and actions; `components/` shared pieces; `lib/` API, Monaco and helpers; `styles/` CSS |
| `catalog/` | Built-in problems, one language-neutral folder each: `problem.json`, `problem.md`, `api.json` + `cases/` (shared hidden tests, run in every language by `backend/lab/langs/<lang>`), `<lang>/starter/`; Codebase problems keep per-language hidden tests in `<lang>/hidden/`. Rendered into an interview-set/1 set per attempt (`backend/lab/variants.py`) |
| `answers/` | The answer key per problem and language (`answers/<id>/<lang>/`): `reference/`, `mutants.json` and (Codebase) `bugs.json`. Not in the image; used by `tools/gate_problem.py`, debriefs and TDD scoring |
| `deploy/` | Everything that builds or runs the app: `docker-compose.yml`, the backend/nginx/runner-python Dockerfiles, `nginx.conf`, install/uninstall. The root `.env` points `docker compose` at it, so compose commands work from the repo root |
| `tools/pack.py` | Packs a set dir into a zip (refuses reference/, mutants.json, bugs.json) |
| `tools/status.py` | `python3 tools/status.py data/sets/<name>` → time left, from session.json |
| `data/` | Your attempts (`sets/`), your own problems (`catalog/`) and exports (bind-mounted; never deleted by uninstall). Home's Delete moves a set to `data/deleted/<name>-<stamp>/`; restore by moving it back to `data/sets/` |

## Building a set by hand
```
docker compose run --rm -T -v "$PWD/<set>:/set:ro" backend python3 gate.py /set     # must print GATE PASS
python3 tools/pack.py <set> ~/Downloads/<name>.zip
```
Re-grade an export (unzipped into `<export>`, with the set folder `<set>` that holds the hidden tests; `final/` is the code at the close, `submission/` the latest code, older exports have only `submission/`): `docker compose run --rm -T -v <export>:/c:ro -v <set>:/s:ro backend python3 grade.py /c/final /s/<hidden tests file> -k test_l1_ --names`.

## Tests
`tests/unit/run.sh`: backend unit tests, no Docker, a few seconds (needs `pip install -r backend/requirements.txt`).
One plain script per area in `tests/unit/test_*.py`: grading verdicts, test pruning, the clock, set validation, zip import.

`tests/run_all.sh [--clean]`: gates every set in `tests/sets/`, then runs `tests/api_test.py` (all 7 languages,
TLE/MLE/fork bomb/no network/read-only/truncation, leak check, grading flows, import validation, security), then
`tests/e2e.sh` (Playwright: a real drop event → ready → Start → Run → Submit → reveal → End → Export).

Tests never touch the stack you use or `data/`. `run_all.sh` builds a separate stack from the checkout it runs in
(compose project `ilab-test` on 127.0.0.1:8766, an empty data folder in `tests/out/stack-data`, its own images, runners
and Go cache) and removes it at the end. To run one suite by hand: `tests/stack.sh up`, then `python3 tests/api_test.py`
or `tests/e2e.sh`, then `tests/stack.sh down`.

CI (GitHub Actions) runs only what a change can affect:
- `.github/workflows/catalog.yml` gates catalog problems per language in the runner images. `tools/ci_affected.py` maps the changed
  files to the gates: a problem's `<lang>/` files → that problem in that language; its shared files (`api.json`, `cases/`,
  statement) → that problem in every language; a language backend (`backend/lab/langs/<lang>*`) → the canaries (`tests/fixture`, which covers every
  harness feature, and `quota-codebase`) in that language; the grader core (`variants.py`, `backend/sandbox/`, the backend
  image) → the canaries in all three. One job per language. Re-gating the whole catalog is a manual run (Actions → Catalog).
- `.github/workflows/ci.yml` builds the UI when `ui/**` changes.
- `.github/workflows/backend.yml` runs `tests/unit/run.sh` on every PR that touches `backend/`, `tools/` or `tests/unit/`.
- `.github/workflows/full.yml` runs `tests/run_all.sh` only on a merge to `main` that touches app code, on demand
  (Actions → Full suite → Run workflow), or on a PR when you add the `full-suite` label.