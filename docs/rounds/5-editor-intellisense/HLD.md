# Round 5 HLD: Code help in the editor

Spec: `SPEC.md` in this folder. Code references are to `main` at b28fa5c. Measurements:
`.iteration/work/round-5/` (`scripts/lsp_bench.py`, `scripts/pyodide_bench.mjs`, `scripts/proxy_idle.py`,
`scripts/gen_*`; raw output in `results/`).

## Today's flow

```
Round screen ─► round.svelte.js openFile(p)
                  GET /api/sets/<n>/files/<p>  ─► monaco.editor.createModel(text, langOf(p), inmemory:///<p>)
                  models[p] kept until leaveRound()                       only files opened this round have a model
Monaco 0.52.2:  no completion / hover / signature provider for python, go, java
                wordBasedSuggestions: 'matchingDocuments'  ─► words from open models of the same language
Ready.svelte:   #ready-assist "Autocomplete: suggests only words already in your files, not library functions or methods."
Errors:         only from Run / Submit (the compiler, in the results pane)
```

## Design

```
 Browser (Monaco)                       backend (Waitress, 32 threads)            docker-socket-proxy        LS container
 ───────────────                        ──────────────────────────────            ───────────────────        ────────────
 completion / hover / signature ──POST /api/sets/<n>/assist──► lsp.call()  ──attach stream (stdio)──►  pyright | gopls | jdtls
 providers (assist.js)                  one Session per app                   CONTAINERS, IMAGES, POST     /tmp/w = work/ files
 markers ◄── op "check" (0.5 s idle)    files PUT ─► lsp.file_saved()          (unchanged)                  --network none, read-only,
                                        idle 30 min / leave / restart ─► stop                               512 MB, 2 CPUs, --rm
```

### Why HTTP and stdio, not a WebSocket and a port

- **Waitress has no WebSocket support.** A WebSocket bridge would need a second server process or service. A POST per
  request costs a few milliseconds on localhost, below the servers' own 1–46 ms.
- **Language servers speak LSP over stdin/stdout.** The runner already talks to its containers over the attach stream
  through the socket proxy (`_attach()` in `backend/sandbox/runner.py`). A language server is the same thing kept open
  longer. So the container needs no network at all (`--network none`, as a runner), and nothing new listens anywhere.
- **The proxy keeps its permissions.** Create, attach, start and kill are the calls the runner makes today.

Measured through a scratch copy of the pinned proxy (`scripts/proxy_idle.py`, `results/proxy-idle-*.txt`): the
attach upgrades to `HTTP/1.1 101 UPGRADED` and a line echoes back. **Left idle for 11 minutes, the stream is closed** (the
proxy's `timeout client 10m` / `timeout server 10m`, and it sets no `timeout tunnel`). With one round trip every
4 minutes it is still open after 11 minutes. So the session sends a keepalive (below) instead of touching the proxy.

### Backend: `backend/sandbox/lsp.py` (new, ~250 lines)

```python
"""Code help: one language server per open round, in a runner-shaped container, spoken to over the attach stream."""
SERVERS = {   # language -> image, command, extra files for the LS workspace only, init settings
  "python": dict(image=LSP_IMAGES["python"], cmd="pyright-langserver --stdio",
                 extra={"pyrightconfig.json": b'{"pythonVersion": "3.15", "typeCheckingMode": "basic"}'}),
  "go":     dict(image=LSP_IMAGES["go"], cmd="gopls", env=GO_ENV_LSP, settings={"gopls": {"linksInHover": False}}),
  "java":   dict(image=LSP_IMAGES["java"], cmd=JDTLS_CMD, extra={"Expect.java": runner.EXPECT_JAVA},
                 settings={"java": {"signatureHelp": {"enabled": True},
                                    "import": {"gradle": {"enabled": False}, "maven": {"enabled": False}}}}),
}
OPS = {"complete": "textDocument/completion", "resolve": "completionItem/resolve",
       "hover": "textDocument/hover", "signature": "textDocument/signatureHelp"}

class Session:            # one container; state: starting | ready | unavailable
    def __init__(self, n, lang, files): ...   # create + attach + start in a thread; files go in as tar.gz on stdin first
    def sync(self, rel, text): ...           # didOpen the first time, then didChange (full text) when it differs
    def request(self, method, params, timeout=1.5): ...   # $/cancelRequest on timeout, returns None
    def diagnostics(self, rel, wait=2.0): ...             # the newest publishDiagnostics for the version just sent
    def stop(self): ...                                    # shutdown/exit, then kill (AutoRemove)

def call(n, lang, op, file, text=None, line=0, col=0, item=None) -> dict: ...
    # -> {"state": "starting" | "ready" | "unavailable", "reason"?: str, "result"?: ..., "diagnostics"?: [...]}
def file_saved(n, rel, data): ...        # files PUT hook: sync into the live session, if it is for n
def stop(n=None): ...                    # leave the round, delete the set, idle 30 min, backend shutdown
def sweep(): ...                         # at startup: kill containers labelled ilab.lsp=<INSTANCE>
# ponytail: one session per app (module global + lock); the app is single-user. Per-set sessions if that changes.
```

- **Files in.** `store.work_files(n)` (the Files list: `work/` only, so never `.hidden/`, `manifest.json` or
  `problem.md`), plus the server's `extra` files, go in as one tar.gz on stdin, exactly as a Run does. The boot
  line is the runner's, ending in `exec <cmd>` instead of the harness: `head -c "$ILAB_N" | tar xz && exec …`.
  GNU `head -c` never reads past N bytes (each read asks for at most what is still wanted), so the rest of stdin is
  the LSP stream. PR 1's api_test saves a 100 KB file into the set before the server starts, to check this.
- **Edits.** Every assist request carries the open file's current text; `sync()` sends it only when it changed. The
  files PUT route calls `file_saved()`, so a method saved in `ledger.py` shows in `main.py` after one autosave.
- **Out.** The attach stream is multiplexed (8-byte frame headers, `Tty: false`). The reader thread demuxes it as it
  streams (the runner's `_demux()` works on a whole buffer), parses LSP frames, answers server requests
  (`workspace/configuration` → the `settings` above; others → `null`), and keeps the newest `publishDiagnostics` per file.
- **Paths and links.** Results are rewritten before they leave: `file:///tmp/w/` is removed from URIs, and Markdown
  links in hover text become plain text (jdtls adds `Source: [w_…](file:///tmp/w/…)`; gopls's pkg.go.dev link is
  turned off by `linksInHover`).
- **Start-up.** `call()` on a set with no session starts one in a thread and returns `{"state": "starting"}` at once.
  `initialize` takes 0.4–3.8 s; requests during it get `starting`. If the image is missing or Docker refuses, the state
  is `unavailable` with the reason, and the next request after 30 s tries again.
- **Keepalive.** Every 4 minutes without traffic, the session sends the request `$/ilab/ping`. LSP requires a
  server to answer an unknown `$/` request with a MethodNotFound error, so it is a round trip in both directions
  through the proxy, and it does nothing in the server. Without it, the proxy cuts the stream after 10 idle minutes
  (measured above), and a candidate who reads the problem for 10 minutes would come back to a 1–5 s restart.

### Runner: `backend/sandbox/runner.py`

```python
LOCKED = {"AutoRemove": True, "NetworkMode": "none", "ReadonlyRootfs": True,
          "Tmpfs": {"/tmp": "rw,exec,nosuid,size=256m"}, "Memory": 512 << 20, "MemorySwap": 512 << 20,
          "NanoCpus": 2_000_000_000, "PidsLimit": 256, "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"]}
# container() uses dict(LOCKED); lsp.Session uses dict(LOCKED) too, so the two can't drift apart.
LSP_IMAGES = {"python": os.environ.get("ILAB_IMG_LSP_PYTHON", "ilab-lsp-python:pyright1.1.414"), …}   # one per PR
EXPECT_JAVA = '''public class Expect { … }'''   # moved out of the Java harness string, unchanged, so both use one copy
```

The language-server container does not take the runner semaphore (`_sem`, 3 runs at once). Worst case on the host:
3 runs and 1 language server, 4 × 512 MB = 2 GB.

### API: `backend/server.py` and `API.md`

`POST /api/sets/<n>/assist` (same guard as every route: `X-ILab`, Host, Origin; set must exist and be started)

| Field | |
|---|---|
| `op` | `complete`, `resolve`, `hover`, `signature`, `check` (diagnostics for `file`), `stop` |
| `file` | path as in Files (`ledger/ledger.py`); must pass `work_path()` |
| `text` | the editor's current text for `file` (≤ `MAX_FILE`) |
| `line`, `col` | 0-based, UTF-16 (LSP's default; Monaco's 1-based line and column minus 1) |
| `item` | the completion item, for `resolve` |

Response 200: `{"state", "reason"?, "result"?, "diagnostics"?}`. `result` is the LSP result unchanged apart from the
path and link rewriting above. 400 for an unknown `op` or a bad path, 404 no set, 409 not started. The PUT on
`/files/<path>` calls `lsp.file_saved()` after writing. `rounds.delete()` calls `lsp.stop(n)`.

### Health and images: `backend/sandbox/images.py`

`image_keeper()` calls `lsp.sweep()` next to `runner.sweep()`. `health()` adds `"assist": {lang: ready | missing}`
for `LSP_IMAGES`. These images are built locally (like `ilab-python`), so the keeper never tries to pull them.

### Deploy: `deploy/lsp-<lang>/Dockerfile`, `deploy/docker-compose.yml`, `deploy/install.sh`, `deploy/uninstall.sh`

```dockerfile
# deploy/lsp-python/Dockerfile
FROM node:24.22.3-slim
RUN npm install -g pyright@1.1.414 && npm cache clean --force
# deploy/lsp-go/Dockerfile
FROM golang:1.27.4 AS build
RUN GOBIN=/out go install golang.org/x/tools/gopls@v0.24.0
FROM golang:1.27.4
COPY --from=build /out/gopls /usr/local/bin/gopls
# deploy/lsp-java/Dockerfile (ADD --checksum pins the tarball)
FROM eclipse-temurin:21.0.13.1_2-jdk
ADD --checksum=sha256:338e7e73d61836651ba2453919a0d34fa763eb4e7c03342092309bffb8934c64 https://download.eclipse.org/jdtls/milestones/1.61.0/jdt-language-server-1.61.0-202609031315.tar.gz /tmp/jdtls.tgz
RUN mkdir /opt/jdtls && tar xzf /tmp/jdtls.tgz -C /opt/jdtls && rm /tmp/jdtls.tgz
```

Each is a build-only compose service like `ilab-python` (`entrypoint: ["true"]`, `network_mode: none`, `restart:
"no"`), so `up --build` (install and `tests/stack.sh up`) builds it. `install.sh` builds them next to `ilab-python`;
`uninstall.sh` removes them next to it. Base images are the runner images the app already pulls, so each adds only
its own layer: +42 MB, +44 MB, +55 MB (measured, `results/image-sizes.txt`).

Java command (`JDTLS_CMD`): `cp -r /opt/jdtls/config_linux /tmp/cfg && exec java -Xms64m -Xmx256m -XX:+UseSerialGC
-XX:TieredStopAtLevel=1 -Declipse.application=org.eclipse.jdt.ls.core.id1 -Dosgi.bundles.defaultStartLevel=4
-Declipse.product=org.eclipse.jdt.ls.core.product -jar /opt/jdtls/plugins/org.eclipse.equinox.launcher_*.jar
-configuration /tmp/cfg -data /tmp/jws --add-modules=ALL-SYSTEM --add-opens java.base/java.util=ALL-UNNAMED
--add-opens java.base/java.lang=ALL-UNNAMED`. jdtls writes its config and workspace, so both go to `/tmp`; the root
stays read-only.

### UI: `ui/src/lib/assist.js` (new, ~150 lines)

```js
// Code help: Monaco providers for python/go/java, backed by POST /api/sets/<n>/assist.
export function register(monaco)            // once, after Monaco loads: completion ('.' trigger), hover,
                                            // signature help ('(' and ','), each per language
export function attach(set, lang, fileOf)   // round entered: fileOf(model) -> path in Files (from its inmemory:/// uri)
export function detach()                    // round left: POST {op: "stop"}, clear markers
export function watch(model)                // on content change, 500 ms after typing stops: op "check" -> setModelMarkers
export const assistState = $state({ state: '', reason: '' })   // for the toolbar line
```

- LSP → Monaco conversion: completion kind table (LSP's 1-based `CompletionItemKind` → `monaco.languages.CompletionItemKind`),
  `insertTextFormat: 2` → `InsertAsSnippet`, `textEdit` / `additionalTextEdits` ranges (0-based → 1-based), `MarkupContent`
  → `IMarkdownString`, diagnostic severity 1–4 → `MarkerSeverity` Error / Warning / Info / Hint.
- A request uses `AbortSignal.timeout(1500)`; on abort or error the provider returns nothing. Monaco then shows word
  suggestions as today. PR 1's e2e confirms that word suggestions still appear while the server is `starting`.
- `round.svelte.js`: `editor()` calls `assist.register(window.monaco)` once; `enterRound()` calls `attach()`;
  `openFile()` calls `watch(models[p])`; `leaveRound()` calls `detach()`. `monaco.js` is not touched in PRs 1–3.
- `Toolbar.svelte`: `<span id="assist-status" class="saved" title={assistState.reason}>` before `#save-status`, showing
  "Code help starting…" or "Code help unavailable". Empty when ready, and when the set's language has no server.
- `Ready.svelte` `#ready-assist`: per language, from one table in `assist.js` (`ASSIST_LINE`).

### UI: Settings "Code help" (PR 4), on round 4 PR 2's panel

```svelte
<div class="setting"><div><span id="assist-label">Code help</span>
    <p>Suggestions, parameter hints and error underlines. Real interviews differ: some have all of it, some none.</p></div>
  <div id="assist-pick" class="seg" role="group" aria-labelledby="assist-label">
    {#each [['full', 'Full'], ['words', 'Words only'], ['off', 'Off']] as [v, label]}
      <button type="button" data-assist={v} aria-pressed={String(level === v)} onclick={() => { level = v; setAssist(v); }}>{label}</button>
    {/each}</div></div>
```

`monaco.js` gains `setAssist(v)` next to round 4's `setWrap()`: it saves `ilab-assist` and calls
`ed.updateOptions(assistOpts(v))`, where `off` is `{quickSuggestions: false, suggestOnTriggerCharacters: false,
wordBasedSuggestions: 'off', parameterHints: {enabled: false}, hover: {enabled: false}}` and the others are Monaco's
defaults. `loadMonaco()` passes `assistOpts()` at create time. `assist.js` providers and `watch()` return nothing
unless the level is `full`, and clearing it to `words` or `off` clears the markers.

### Data and interface changes

| Thing | Change |
|---|---|
| API | New `POST /api/sets/<n>/assist`. `GET /api/health` gains `assist`. Nothing else changes |
| `data/` | None. No new file in a set; the language server's files live in its container's `/tmp` and go with it |
| Containers | New label `ilab.lsp=<INSTANCE>` (`test` on the test stack, so the two stacks never touch each other's) |
| Images | New local builds `ilab-lsp-python:pyright1.1.414`, `ilab-lsp-go:gopls0.24.0`, `ilab-lsp-java:jdtls1.61.0` |
| Browser key `ilab-assist` (PR 4) | New: `full` (default when missing), `words`, `off` |
| Element ids | New: `#assist-status` (PR 1), `#assist-pick [data-assist]`, `#assist-label` (PR 4). Kept: `#ready-assist` (its text changes) and every id round 4 lists |
| Proxy, ports, CSP, runner flags | None |

### Safety review

| Rule | How it holds |
|---|---|
| Nothing about hidden tests reaches the browser | The server only ever has `work_files(n)`, the list the browser already gets in `state.files`, plus `Expect.java` (the Java harness helper the example test already tells you to use) and `pyrightconfig.json`. A leak test per language asks for completions of hidden-only names (PR 1–3) |
| Offline and local | `--network none` on the container; images built at install from pinned versions; no CDN in the UI |
| Runner flags, socket proxy, one port | `LOCKED` is the runner's dict, shared. Proxy permissions unchanged. No port is published or exposed |
| Code from the candidate | Language servers analyse, they don't run the code. Gradle and Maven import are off in jdtls, so a `build.gradle` the candidate writes is never executed. Even if one were, it would run in the same sandbox as Run |
| `data/` never wiped | The session writes nothing to `data/` |

---

## PR plan

Four PRs. **PR 1** builds the bridge and Python end to end (the bridge is only checkable by typing once one language
works). **PR 2** (Go) and **PR 3** (Java) are a Dockerfile, a `SERVERS` entry and their tests each, stacked on PR 1
and built in parallel. **PR 4** (the Settings choice) is stacked on PR 1 and on round 4 PR 2.
**Merge order: PR 1 → PR 2 → PR 3 → PR 4.** PRs 2 and 3 both add one line to `LSP_IMAGES`, the compose file,
`install.sh`, `uninstall.sh` and the `ASSIST_LINE` table: rebase, don't merge blind.

Verify on the isolated test stack (`tests/stack.sh up`, http://127.0.0.1:8766), never on the owner's app at 8765. The
stack builds the UI and the language-server images from the branch.

Shared files with round 4:
- **Round 4 PR 1** (Catalog.svelte, style.css, e2e): round 5 edits neither `Catalog.svelte` nor `style.css`
  (`#assist-status` reuses `.saved`; PR 4 reuses `.setting` and `.seg`). Only `tests/e2e.spec.mjs` is shared: each PR
  appends its own test.
- **Round 4 PR 2** (Settings panel: `App.svelte` header, `Settings.svelte`, `monaco.js`, style.css, e2e, the theme
  switch mounting): PRs 1–3 touch none of them except `tests/e2e.spec.mjs` (append). PR 4 edits `Settings.svelte` and
  `monaco.js` (adds `setAssist()` next to `setWrap()`) and needs round 4 PR 2 merged first. PR 4 doesn't move or
  remount `ThemeToggle`, and adds no CSS.

---

### PR 1: Python gets real code help (pyright)
- **Example** (Settlement ledger: debug, implement, optimise; Python):
  1. On Home, with "Practise in" on Python, open Settlement ledger and press Start.
  2. `main.py` opens. At the end of `handle()`, before the last line, add a line and type `heapq.heap` (add
     `import heapq` at the top first).
  3. On a new line in `handle()`, type `l.bal`.
  4. Type `heapq.heappush(` and stop.
  5. Change the line to `l.balance('a')` and wait a second.
  - **Expected:** step 2: a list with `heapify`, `heappop`, `heappush`, `heappushpop`, `heapreplace`, each with its
    kind icon. Step 3: `balance`, `balance_at`, `trial_balance`, although `ledger/ledger.py` was never opened. Step 4:
    a hint `(heap: list[…], item: …, /) -> None` with `heap` highlighted. Step 5: a red underline; hover reads
    `Argument missing for parameter "cur"`. The toolbar showed "Code help starting…" for about a second after the
    editor appeared, then nothing.
  - **Got today:** step 2: no suggestion for `heap` beyond words already in open files (none match). Step 3: only
    `balance` (a word in `main.py`), with the "abc" word icon; no `balance_at`. Step 4: no hint. Step 5: no underline;
    the mistake shows only when a Run or Submit reaches that line, as a `TypeError` traceback in the results pane.
- **Files:** `backend/sandbox/lsp.py` (new), `backend/sandbox/runner.py` (`LOCKED`, `LSP_IMAGES`, `EXPECT_JAVA`),
  `backend/sandbox/images.py` (sweep, health), `backend/server.py` (route, PUT hook), `backend/lab/rounds.py`
  (`delete()` stops the session), `deploy/lsp-python/Dockerfile` (new), `deploy/docker-compose.yml`,
  `deploy/install.sh`, `deploy/uninstall.sh`, `ui/src/lib/assist.js` (new), `ui/src/features/round/round.svelte.js`,
  `ui/src/features/round/Toolbar.svelte`, `ui/src/features/ready/Ready.svelte`, `API.md`, `README.md` (the diagram
  gains the language-server container), `tests/api_test.py`, `tests/e2e.spec.mjs`.
- **Interface changes:** `POST /api/sets/<n>/assist`; `GET /api/health` gains `assist`.
- **Data changes:** none.
- **Tests:**
  - `tests/api_test.py`, new section "code help" (Python):
    1. Start a Settlement ledger attempt in Python. `assist` with `op: "complete"` on `main.py` before Start → 409.
    2. After Start, poll `complete` (≤ 10 s) until `state` is `ready`. Text = `main.py` + `"\nl.bal"` inside
       `handle()`: labels include `balance_at`. `heapq.heap` after `import heapq`: includes `heappush`. `signature` on
       `heapq.heappush(`: a label containing `heap`. `hover` on `Ledger`: text contains `class Ledger`.
    3. `check` with `l.balance('a')`: one diagnostic on that line, message contains `cur`, within 2 s.
    4. Save a new method `def zz_probe(self): ...` into `ledger/ledger.py` through the files PUT. `complete` on
       `l.zz_` in `main.py` (not resent) lists `zz_probe`.
    5. Leak: the Python rendering of the hidden tests defines `test_p1_…` names. `complete` on `import tests_h` and on
       `test_p1_` in a new file lists none of them. No result or hover anywhere contains `/tmp/w`, `.hidden` or `](`.
    6. The container: list containers through the test stack's own Docker (`docker ps --filter label=ilab.lsp=test`
       from the test script, as the security section already does for runners): exactly one; `docker inspect` shows
       `NetworkMode none`, `ReadonlyRootfs true`, `Memory 536870912`, `CapDrop [ALL]`, `no-new-privileges`, no ports.
    7. `stop` → the container is gone within 5 s. Delete a set with a live session → gone.
    8. Bad `op` → 400; `file: "../x"` → 400; `file: ".hidden/x"` → 400.
    9. Stdin handover: in a fresh attempt, save a 100 KB `big.py` before the first `assist` call. The server still
       reaches `ready` and `big.py`'s last function is offered from `main.py`.
  - `tests/e2e.spec.mjs`, new test "Code help: Python suggestions, hints and underlines":
    1. Start the attempt through the API (as round 4's Settings test does), open it, wait for `#editor .monaco-editor`.
    2. Click into the editor, Ctrl+End, type `\nimport heapq\nheapq.heap`. `.suggest-widget .monaco-list-row` with
       `aria-label` containing `heappush` appears within 5 s.
    3. Escape, new line, type `l.bal` inside a function: a row containing `balance_at`.
    4. Type `heapq.heappush(`: `.parameter-hints-widget` is visible and contains `heap`.
    5. Type `l.balance('a')`, wait 2 s: `.squiggly-error` count ≥ 1.
    6. `#assist-status` is empty once ready. Reload the round: suggestions still work.
  - `cd ui && npm run build` succeeds.
- **Acceptance** (on the test stack, by typing in the editor):
  1. The example gives the expected result, in light and dark (the suggestion list uses the theme's surface colours).
  2. Open `test_example.py`: no error underlines on the untouched starter file.
  3. In `ledger/payments.py`, add a method and wait for "Saved". In `main.py`, `l.` lists it.
  4. New file `helpers.py` with `def fmt(x): return x`. In `main.py`, `from helpers import f` offers `fmt`.
  5. Type fast for 10 s in `main.py`: no lag, no lost keystrokes, and "Saved" keeps appearing.
  6. Leave the round (Home): within 5 s, `docker ps --filter label=ilab.lsp=test` is empty.
  7. Stop the language server by hand (`docker kill` it): the toolbar shows "Code help unavailable", word
     suggestions keep working, Run and Submit work. The next request after 30 s starts a new one.
  8. A Go or Java round: nothing changes yet (word suggestions; no status line).
  9. `tests/run_all.sh` ends with every step PASS.
- **Not in this PR:** Go, Java, the Settings choice.

---

### PR 2 (stacked on PR 1, parallel with PR 3): Go gets real code help (gopls)
- **Example** (Settlement ledger; Go):
  1. Open Settlement ledger in Go and press Start.
  2. In `cmd/run/main.go`, inside the command loop, type `l.Bal`.
  3. On a new line, type `strings.Has`.
  4. Type `var b strings.Builder` on one line, then `b.Wri` on the next.
  5. Type `_ = l.Balance("a")`.
  - **Expected:** step 2: `Balance`, `BalanceAt` (and `TrialBalance`), with their signatures, although
    `ledger.go` was never opened. Step 3: `HasPrefix`, `HasSuffix`. Step 4: `Write`, `WriteByte`, `WriteRune`,
    `WriteString`. Step 5: underline, "not enough arguments in call to l.Balance … want (string, string)", within a
    second. Hovering `New` shows `func New() *Ledger` and "New returns an empty ledger." with no link.
  - **Got today:** step 2: only words in `main.go` (`l.Balance` is used there, so `Balance` appears as a word;
    `BalanceAt` doesn't). Steps 3 and 4: nothing relevant. Step 5: no underline until Run.
- **Files:** `deploy/lsp-go/Dockerfile` (new), `backend/sandbox/runner.py` (`LSP_IMAGES["go"]`),
  `backend/sandbox/lsp.py` (`SERVERS["go"]`, `GO_ENV_LSP`: the runner's Go env with `GOCACHE=/tmp/gocache`, no cache
  volume), `deploy/docker-compose.yml`, `deploy/install.sh`, `deploy/uninstall.sh`, `ui/src/lib/assist.js`
  (`ASSIST_LINE.go`, provider registered for `go`), `tests/api_test.py`, `tests/e2e.spec.mjs`.
- **Interface changes:** none beyond PR 1.
- **Tests:**
  - `tests/api_test.py` "code help" gains Go: the PR 1 steps 2–8 with the example's text; the leak check asks for
    `TestP1` / `test_p1` completions in the package and gets none of the hidden test names (`hidden_test.go` is never in
    the workspace); hover contains no `pkg.go.dev`.
  - `tests/e2e.spec.mjs` "Code help: Go": steps 2 and 5 of the example in the browser (`.suggest-widget` row with
    `BalanceAt`; `.squiggly-error`).
- **Acceptance:** the example, in light and dark; `ledger_example_test.go` opens with no underlines; a new file in
  package `ledger` (`extra.go`) with a function is offered from `cmd/run/main.go` as `ledger.<Name>`;
  `tests/run_all.sh` all PASS.
- **Not in this PR:** Java, Settings.

---

### PR 3 (stacked on PR 1, parallel with PR 2): Java gets real code help (jdtls)
- **Example** (Settlement ledger; Java):
  1. Open Settlement ledger in Java and press Start.
  2. In `Main.java`, inside `handle()`, type `l.bal`.
  3. On a new line, type `Collections.unmod`.
  4. Type `Map<String, List<Integer>> m = new HashMap<>();` then `m.computeIf`.
  5. Type `Math.max(`, then `l.balance("a");`.
  - **Expected:** "Code help starting…" for up to about 5 s after the editor appears. Then: step 2: `balance(String
    account, String cur) : long`, `balanceAt(String account, String cur, long ts) : long`. Step 3:
    `unmodifiableCollection`, `unmodifiableList`, `unmodifiableMap`, … Step 4: `computeIfAbsent(String key,
    Function<…> mappingFunction)`, `computeIfPresent(…)`. Step 5: a hint listing the `max` overloads; then an
    underline, "The method balance(String, String) in the type Ledger is not applicable for the arguments (String)",
    within about 1.5 s. `ExampleTest.java` opens with no underline under `Expect`.
  - **Got today:** step 2: only words from opened files. Steps 3–5: nothing; the error shows only after Run.
- **Files:** `deploy/lsp-java/Dockerfile` (new; `ADD --checksum` for the 51 MB tarball, sha256 in `.iteration/work/round-5/results/jdtls-1.61.0.sha256`), `backend/sandbox/runner.py`
  (`LSP_IMAGES["java"]`), `backend/sandbox/lsp.py` (`SERVERS["java"]`, `JDTLS_CMD`), `deploy/docker-compose.yml`,
  `deploy/install.sh`, `deploy/uninstall.sh`, `ui/src/lib/assist.js` (`ASSIST_LINE.java`, provider for `java`),
  `tests/api_test.py`, `tests/e2e.spec.mjs`.
- **Interface changes:** none beyond PR 1.
- **Tests:**
  - `tests/api_test.py` "code help" gains Java: PR 1 steps 2–8 with the example's text (poll for `ready` up to 20 s);
    `signature` on `Math.max(` returns at least one signature (checks `signatureHelp.enabled`); `check` on
    `ExampleTest.java` unchanged returns no diagnostics (checks the `Expect` stub); leak: `HiddenTest` is not offered
    for `HiddenT`; hover text has no `file://` and no `](`.
  - Memory: after the checks, `docker stats --no-stream` on the `ilab.lsp=test` container reads under 512 MB and
    `docker inspect` shows `OOMKilled: false`.
  - `tests/e2e.spec.mjs` "Code help: Java": steps 2 and 5 of the example in the browser.
- **Acceptance:** the example, in light and dark; a `build.gradle` file created in Files is ignored (no Gradle
  start, no new underline); a 30-minute round in Java with normal editing ends with the container still running and
  no OOM; `tests/run_all.sh` all PASS.
- **Not in this PR:** Settings.

---

### PR 4 (stacked on PR 1 and round 4 PR 2): Choose how much code help you get
- **Example** (Settlement ledger; Python, after PR 1):
  1. On Home, open Settlement ledger in Python. Read the ready screen's "Code help" line.
  2. Press Start. In `main.py`, type `heapq.heap` (after `import heapq`).
  3. Open Settings, set Code help to "Words only", close it, and type `heapq.heap` again on a new line.
  4. Set it to "Off" and type `heapq.heap` again, then `l.balance('a')`.
  5. Reload the page and reopen the round.
  - **Expected:** step 1: "Code help: Full. Suggestions from your code and Python's standard library, parameter
    hints and error underlines. Change it in Settings." Step 2: `heappush` and friends. Step 3: only words already in
    your files (as today), no hints, existing underlines gone. Step 4: no suggestion list at all, no hint, no hover,
    no underline. Step 5: still Off; the ready screen line says "Code help: Off. No suggestions, hints or underlines,
    like a shared doc." The clock kept running throughout.
  - **Got today:** step 1 says "Autocomplete: suggests only words already in your files, not library functions or
    methods." There is no way to turn suggestions off or on.
- **Files:** `ui/src/features/settings/Settings.svelte` (one `.setting` block), `ui/src/lib/monaco.js` (`setAssist`,
  `assistOpts`, create option), `ui/src/lib/assist.js` (level check, clear markers), `ui/src/features/ready/Ready.svelte`
  (the line reads the level), `tests/e2e.spec.mjs`.
- **Interface changes:** browser key `ilab-assist`. No API change.
- **Tests:**
  - `tests/e2e.spec.mjs` "Settings: code help Full, Words only, Off":
    1. Ready screen: `#ready-assist` contains "Code help: Full".
    2. Start; type `heapq.heap`: a suggestion row contains `heappush`.
    3. `#settings-btn`, `#assist-pick [data-assist="words"]` (pressed), Escape. Type `heapq.heap` on a new line and
       press Ctrl+Space: no row contains `heappush`; `.squiggly-error` count is 0.
    4. `[data-assist="off"]`: Ctrl+Space shows no `.monaco-list-row`; typing `heapq.heappush(` shows no
       `.parameter-hints-widget`.
    5. Reload, reopen: `[data-assist="off"]` is still pressed; the ready screen (another unstarted attempt) says
       "Code help: Off".
    6. Back to Full: suggestions return without a reload.
  - Round 4's Settings test passes unchanged. `npm run build` succeeds.
- **Acceptance:** the example, in light and dark; at 400 px the three-way switch wraps under "Code help" with no
  sideways scroll; keyboard reaches all three buttons, and a screen reader hears "Code help" and the pressed state;
  Go and Java behave the same way at each level; `tests/run_all.sh` all PASS.
- **Not in this PR:** recording the level in the export (open question 2), a per-set level (open question 3).

## Owner's decisions (2026-11-27)
- Build real language servers for all three languages (Python, Go, Java), accepting about +141 MB of runner images.
- The export does not record the code-help level: it stays a personal setting, with no change to `session.json` or `export.zip`.
- Not asked, kept as defaulted: a problem set cannot force code help Off.
