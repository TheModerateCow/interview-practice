# Round 5: Code help in the editor

Request (owner, 2026-11-27): "can you add intellisense for the monaco text editor?"

Round 2's notes left this open: Monaco's built-in language services cover JS/TS only, so Python, Go and Java get
"words already in this file". This round decides what "IntelliSense" means for a candidate in a timed round, and
plans it. Code references are to `main` at b28fa5c. Measurements, scripts and raw results are in
`.iteration/work/round-5/` (`scripts/`, `results/`).

## Problem

All 30 built-in problems come in Go, Java and Python. In all three the editor helps with almost nothing:

- **No library help.** In Python, type `heapq.heap`: no `heappush`, no `heappop`. The only suggestions are words
  already in the files you have opened this round. Monaco's default (`wordBasedSuggestions: matchingDocuments`) is the
  only completion source: `ui/src/lib/monaco.js` registers no provider, and Monaco has none for these languages.
- **No help on your own code.** In Settlement ledger (Codebase, 18 Java files), typing `l.` on a `Ledger` doesn't list
  its methods. You get them as words only after opening `Ledger.java`, and you get every other word in that file too.
- **No parameter hints or hover.** `Math.max(` shows nothing, and hovering `new Ledger()` shows nothing. To check a
  method's arguments you open its file and scroll.
- **Errors show up only on Run.** A missing argument or a misspelt name is reported only after a Run or a Submit, by
  the compiler, in the results pane.
- **The ready screen says so.** `#ready-assist` reads "Autocomplete: suggests only words already in your files, not
  library functions or methods." (`ui/src/features/ready/Ready.svelte` line 27). It is honest, but it is a gap.

Real interview platforms do give this help, at different levels:

| Platform | What it offers | Can it be turned off? |
|---|---|---|
| CoderPad | Autocomplete ("IntelliSense") for C, C#, C++, Java, JavaScript, Kotlin, Python, Ruby and Swift. **Not Go** ([pad settings](https://coderpad.io/resources/docs/interview/pads/settings)) | Yes. Editor settings are per viewer, for interviewer and candidate |
| HackerRank | Monaco with IntelliSense ([IDE post](https://www.hackerrank.com/blog/new-and-improved-ide-on-hackerrank-platform/)) | Yes. "Autocomplete" toggle in the editor preferences ([interview settings](https://hackerrank-knowledge-base.help.usepylon.com/articles/6563947154)) |
| CodeSignal | A language server per session, in a Docker container per user, over WebSockets; 25+ languages including Go ([engineering blog](https://codesignal.com/blog/engineering/how-we-support-autocompletion/)) | Not stated |
| A shared doc or whiteboard | Nothing | n/a |

So a realistic practice app needs real help **and** a way to practise without it.

## What "code help" means here

"Code help" is the name on screen (Settings, ready screen). It has five parts. The table says what each one gives a
candidate in a timed round, and whether this round ships it.

| Part | What the candidate gets | Ships | Why |
|---|---|---|---|
| **Member completion on your own types** | `l.` on a `Ledger` lists `balance`, `balanceAt`, … with their parameters, in every file, opened or not | Yes | This saves the most time in Codebase and Levelled rounds (9 to 18 files) |
| **Standard-library completion** | `heapq.`, `strings.`, `Collections.`, and members of library types (`d.setdefault`, `b.WriteString`, `m.computeIfAbsent`) | Yes | The standard library is the only library allowed, and remembering exact names is what slows people down |
| **Parameter hints** | Typing `heapq.heappush(` shows `heappush(heap, item, /)` and highlights the current argument | Yes | Cheap, and it's what CoderPad and HackerRank show |
| **Hover** | Hovering a name shows its type or signature and its first doc line | Yes | Same source as completion; no extra cost |
| **Error underlines** | A red squiggle under `l.balance("a")` with "Argument missing for parameter "cur"" about 0.3–1.2 s after typing | Yes, in Full only | It catches typos before a Run. It is also the biggest change from a plain editor, so "Words only" and "Off" remove it |
| Go to definition, rename, quick fixes, format | | No | Not asked for. Each is a separate editor feature with its own tests. A later round can add them |

What completions may use: **the candidate's visible files and the language's standard library, nothing else.** The
analyser never sees `.hidden/` (hidden tests, later parts). This is the same rule the file list follows today
(`work_files()` in `backend/lab/store.py`).

## Why this design (and not the alternatives)

Measured on this machine (24 cores) in containers with the runner's limits (no network, read-only root, 512 MB, 2
CPUs), on Settlement ledger, the largest starter (11–18 files, 600–670 lines). Latency is the median of 15 requests,
each sent after an edit.

| | **(c) Real language servers in the backend** (pick) | (a) Lists in the browser | (b) An analyser in the browser |
|---|---|---|---|
| What it is | pyright 1.1.414 (Python), gopls v0.24.0 (Go), jdtls 1.61.0 (Java), one container per open round | Per-language keyword, builtin and library lists, plus names found in your files | Jedi in Pyodide (Python's interpreter compiled to WebAssembly), in a browser worker |
| Python | Yes | Yes, without types | Yes |
| Go and Java | Yes | Yes, without types | **No.** gopls needs the `go` tool and a filesystem; jdtls needs a JVM. Neither runs in a browser. The only browser build of pyright on npm (`@typefox/pyright-browser`) stops at 1.1.299 (2023) |
| `l.` on your own type | Exact: `balance`, `balance_at`, `trial_balance` | Every method name in every file, of every class | Exact |
| `d.setd` on a library type | Exact | Every method of every library type | Exact |
| Parameter hints | Yes (Java: needs a setting, PR 3) | Library functions only | Yes |
| Error underlines | Yes. pyright 0.27 s, gopls 3–4 ms, jdtls 0.6–1.2 s after the edit | No | Syntax errors only |
| Completion latency | pyright 8–23 ms, gopls 1–3 ms, jdtls 14–46 ms | Instant | 64–203 ms (Node stand-in for a browser) |
| Start | 1.1 s (pyright), 1.2 s (gopls), 4.0–5.1 s (jdtls) from container start to the first useful completion | None | 1.3 s to load Pyodide and 0.9 s to import Jedi, in Node, on every page load |
| Memory | 128 MB (pyright), 177 MB (gopls), 406 MB (jdtls, heap 256 MB); peak, in a container capped at 512 MB | ~0 | 233 MB in the browser tab |
| Disk / download | On top of runner images you already have: +42 MB (pyright on node:24.22.3-slim), +44 MB (gopls binary on golang:1.27.4), +55 MB (jdtls on temurin 21). About 141 MB, built at install | +37 KB gzipped in the UI (Python 19 KB, Go 6 KB, Java 12 KB, generated from the runner images) | +18.4 MB in the UI (10.3 MB gzipped): `pyodide.asm.wasm` 9.6 MB, stdlib 2.5 MB, Jedi wheel 4.9 MB |
| Offline at run time | Yes: `--network none` | Yes | Yes |
| Security | Same container flags as a runner, same socket proxy, no new port (see the HLD) | Nothing new | CSP needs `'wasm-unsafe-eval'` in `script-src` |
| Python version | 3.15 (`pythonVersion: "3.15"`, checked) | 3.15 (generated from the runner) | 3.14 (Pyodide 314.0.8), one behind the runner |

**(c) wins** for all three languages. It is the only option that gives Go and Java real help. For Python it beats (b)
on latency (3–9× faster), errors, and start-up, and needs no CSP change. It fits the measured budgets: jdtls, the
heaviest, runs in the runner's 512 MB with a 256 MB heap, at a peak of 406 MB and no out-of-memory kill. The disk cost
is small because each server sits on a runner image the app already pulls. Its costs: one more container while a round
is open, ~141 MB of images, a 1–5 s start, and a backend module of about 250 lines.

(a) is not built. Once the servers exist it adds nothing, and while a server starts, Monaco's word suggestions (today's
behaviour) cover the gap. (b) is not built: it helps only Python, and does it worse than (c).

The honest answer is "all three get real help". It is not "Python now, Go and Java later": the measurements show
gopls is the fastest and lightest of the three, and jdtls fits.

## Requirements

### R1. Code help in Python, Go and Java (UI + backend)
1. With code help on Full, in a started round, the editor offers (for `.py`, `.go`, `.java` files in a set of that
   language):
   1. Completion on `.` and as you type, with members of the candidate's own types and of the standard library, from
      every visible file, opened or not.
   2. Parameter hints on `(` and `,`.
   3. Hover: the signature or type and the first doc line.
   4. Error underlines (errors and warnings from the server) in the open file, about 0.5 s after typing stops.
2. Each suggestion shows its kind icon and, where the server gives one, its signature. Accepting a function inserts its
   name (and the server's snippet, where it gives one) and adds an import line if the server asks for one.
3. A change saved in one file shows up in suggestions in the others within one autosave (0.8 s).
4. A file the candidate creates (New file) gets code help as soon as it opens.
5. JS/TS keep Monaco's built-in services. C and C++ keep word suggestions. Nothing changes for them.

### R2. Only visible files and the standard library (backend)
1. The language server gets the files of `work/` only: the same list the Files pane shows. Never `.hidden/`, never
   `manifest.json` or `problem.md`.
2. It starts only after Start. The ready screen starts nothing.
3. Suggestions, hover text and errors name files by their path in Files (`ledger/ledger.py`), never a container path,
   and contain no web links.

### R3. Never in the way (UI)
1. While the server starts (1–5 s), the editor keeps today's word suggestions. Code help joins when ready.
2. If the server can't start (image missing, Docker down) or stops, the editor keeps word suggestions. One quiet line in
   the toolbar says "Code help unavailable" with the reason in its tooltip. Run, Submit and autosave are unaffected.
3. Typing is never blocked by a request. A suggestion request that takes longer than 1.5 s is dropped.
4. The clock, autosave and the results pane behave exactly as before.

### R4. A Settings choice for realism (UI)
1. Settings (round 4 PR 2) gains "Code help" with three choices:
   - **Full**: suggestions from your code and the standard library, parameter hints, hover and error underlines.
   - **Words only**: suggestions from words already in your files, like a plain editor and like today.
   - **Off**: no suggestions, hints, hover or underlines, like a shared doc.
2. Full by default. Remembered in the browser (`ilab-assist`). Applies to the open editor at once.
3. The ready screen's assist line says what this round will have, in this language, and where to change it. For
   example: "Code help: Full. Suggestions from your code and Python's standard library, parameter hints and error
   underlines. Change it in Settings."

### R5. Same safety, same app (backend, deploy)
1. The language server runs in a container with the runner's flags: no network, read-only root, `/tmp` tmpfs 256 MB,
   512 MB memory and swap, 2 CPUs, 256 pids, all capabilities dropped, no new privileges, removed when stopped. It is
   started through the same socket proxy with the same permissions (CONTAINERS, IMAGES, POST). No new port, no new
   service.
2. At most one language server runs at a time per app. It stops when the candidate leaves the round screen, after 30
   minutes without a request, or when the backend restarts (the startup sweep removes leftovers).
3. Images are built at install (like `ilab-python` today) from pinned versions. Nothing is downloaded at run time.
4. `data/` is untouched: no new files in a set.

## Non-goals

- Go to definition, find references, rename, quick fixes, formatting.
- AI completion of any kind.
- Code help before Start, on the ready screen, or in the problem pane.
- Recording the code-help level in the export or the results (see the open questions).
- Code help for C/C++, or replacing Monaco's TS service for JS/TS.

## Success measures

- Settlement ledger, Python, `main.py`: typing `heapq.heap` lists `heappush` within 0.5 s of the server being ready
  (today: nothing). The same for `strings.Has` → `HasPrefix` (Go) and `Collections.unmod` → `unmodifiableList` (Java).
- `l.bal` lists `balance` and `balance_at` (Python), `l.Bal` lists `Balance` and `BalanceAt` (Go), and `l.bal` lists
  `balance` and `balanceAt` (Java), before `ledger.py`, `ledger.go` or `Ledger.java` has been opened.
- No hidden name ever appears in a suggestion (an api_test leak check per language).
- First useful suggestion within 2 s (Python, Go) and 6 s (Java) of the round screen showing the editor.
- `tests/run_all.sh` stays green, with the new tests.

## Decisions defaulted (owner can override)

1. **Real language servers for all three languages**, not lists and not a browser analyser (the table above).
2. **pyright, not pylsp/Jedi, for Python.** Both start in about 1.1 s. pyright is faster (16 vs 24 ms on `l.bal`, 23
   vs 95 ms on `d.setd`), and it finds errors that run-time checks would miss. pylsp without plugins reports no errors
   at all (measured: none for a missing argument or an undefined name). pyright runs on Node, whose image the app
   already pulls for JS sets.
3. **Full by default.** It matches CoderPad, HackerRank and CodeSignal. "Words only" keeps today's behaviour one
   click away, and "Off" covers interviews in a plain doc.
4. **Error underlines are part of Full**, with no separate switch. "Words only" and "Off" both remove them.
5. **pyright's checking level is "basic"**, not "standard" or "strict", so dynamic but working Python isn't covered in
   squiggles.
6. **jdtls 1.61.0**, the newest milestone that runs on the runner's Java 21. 1.63.0 and the current snapshot (1.64)
   need Java 25 (tested). Its heap is capped at 256 MB.
7. **The language server is started by the first code-help request of a round** (when the editor opens), not at
   Start. It costs nothing when the candidate never reaches the editor.
8. **HTTP requests, not a WebSocket.** Waitress, the backend server, has no WebSocket support. A request per
   suggestion adds a few milliseconds locally (HLD).

## Open questions for the owner

1. **About 141 MB more disk for the three images, and a longer install.** The images are built once at install
   (the jdtls tarball alone is a 51 MB download) and nothing is downloaded at run time. Is that worth it for all three
   languages, or should code help be opt-in per language at install?
2. **Should a round record which code-help level it was taken with?** Today the export says nothing about the editor.
   Recording it ("code help: Full") in the export would let the debrief say "you did this with autocomplete". It
   touches `session.json` and the export, so it is left out unless you want it.
3. **Should Off be per round instead of a global setting?** For example, the skill's set could ask for "Off" to
   simulate a no-IDE interview. The plan keeps it as a personal setting, like word wrap.
