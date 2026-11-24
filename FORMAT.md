# interview-set/1

An interview set is a zip that you drag onto Interview Lab (http://127.0.0.1:8765). Build it with
`python3 tools/pack.py <set_dir> <name>.zip`. pack.py validates the manifest and **never** packs `reference/`,
`mutants.json` or `bugs.json`. The importer validates the zip again and deletes those three if a hand-made zip contains them.

## Zip layout
```
manifest.json
problem.md            shown after Start (never before)
starter/...           copied to the candidate's work/ folder at import
.hidden/<tests file>  hidden tests: tests_hidden.py · hidden_test.go · HiddenTest.java · hidden.test.ts · hidden.test.js
.hidden/<part>.md     later parts (p3.md, l2.md ...), revealed by `reveal`
```
The zip may also contain one top-level folder that holds all of these.
Limits: 2000 files, 50 MB unpacked, no absolute paths, no `..`, no symlinks.

## manifest.json
| Field | Req | Meaning |
|---|---|---|
| `format` | yes | `"interview-set/1"` |
| `name` | yes | `[a-z0-9-]`, max 64. This is the folder name under `data/sets/`. Re-importing replaces a set that hasn't started; a started set refuses |
| `title` | yes | Shown on the ready screen |
| `company`, `role` | no | Ready screen |
| `round` | yes | `codebase` · `levelled` · `ai-assisted` · `tdd` · `dsa` |
| `language` | yes | `python` · `go` · `java` · `typescript` · `javascript` (`c` · `cpp`: Run only, no hidden tests) |
| `difficulty` | yes | `medium` · `hard` |
| `minutes` | yes | Round length. The clock starts only when the candidate presses Start |
| `rules` | no | Short markdown for the ready screen |
| `tags` | no | Every test-name tag in order, e.g. `["test_p1_","test_p2_","test_p3_"]` or `["test_l1_",…,"test_l4_"]`. Default `["test_"]`. At Start, the unlocked tags are the ones that no `reveal` entry `unlocks` |
| `hidden_tests` | no | `.hidden/<tests file>`. Submit runs it once per unlocked tag (`-k <tag>`) |
| `reveal` | no | `[{"file", "after_tag", "or_minutes_left", "unlocks"}]`, in order. `file` (`.hidden/…md`) is shown and tag `unlocks` is graded once every test in `after_tag` passes, **or** once `or_minutes_left` minutes are left (null = never), **or** when the candidate presses *Next part* (the next locked entry, logged "asked to move on"). Locked parts are hidden and not graded |
| `your_tests` | no | Glob over work/ for the candidate's own tests (*My tests*), e.g. `test_*.py`, `*_test.go`, `*Test.java`, `*.test.ts` |
| `run_entry` | no | Path in starter/ that the `testcases` run against, e.g. `main.py`, `cmd/run/main.go`, `Main.java` |
| `testcases` | no | `[{"stdin": "...", "expected": "..."}]`. Run shows ✓/✗ per case for `run_entry`. Trailing whitespace on each line and at the end is ignored |
| `grade_timeout_s` | no | Time limit per grading call, default 45 |

### Patterns
- **Codebase:** `tags ["test_p1_","test_p2_","test_p3_"]`; problem.md = overview + bug report + phase 2 spec;
  `reveal [{"file":".hidden/p3.md","after_tag":"test_p2_","or_minutes_left":15,"unlocks":"test_p3_"}]`.
- **Levelled:** `tags ["test_l1_",…,"test_l4_"]`; problem.md = L1 only; `reveal` = l2.md, l3.md, l4.md, each
  `{"after_tag":"test_l<n-1>_","or_minutes_left":null,"unlocks":"test_l<n>_"}`.
- **DSA / TDD:** usually one tag, no `reveal`. Add `run_entry` + `testcases` for stdin/stdout practice.

## Runner images (write code for these)
Pinned: `ilab-python:3.15.2-pytest9.2.0` (python:3.15.2-slim + pytest 9.2.0), `golang:1.27.4` (standard library only,
`GOTOOLCHAIN=local`; put `go 1.22` in go.mod), `eclipse-temurin:21.0.13.1_2-jdk` (no JUnit: the `Runner` + `Expect`
mini-runner from grade.py), `node:24.22.3-slim` (`node:test`; TypeScript through type stripping: no enums, namespaces or
parameter properties; import local files with their extension), `gcc:14.4.0` (C/C++ Run only). Change them in one place:
`IMAGES` in `backend/runner.py`. Write code that also runs on older toolchains (claude.ai gates with local ones).
Containers have no network, a read-only root, a 256 MB `/tmp`, 512 MB RAM, 2 CPUs and 256 pids. Run cases get 5 s each.

**Levelled Go/Java:** when Submit grades one tag, the app drops the other tags' test functions from its copy of the
hidden tests before compiling. This is so code without later levels' methods still compiles. Keep helpers to the L1 API, keep every import
used outside level tests, and keep gofmt layout (a Go test ends at `}` in column 0; a Java test ends at `}` at its own indent).

## Data written by the app (`data/sets/<name>/`)
- `work/`: the candidate's code (autosaved).
- `session.json`: `{"start": epoch_s|null, "minutes", "hints": [], "events": [[minute, "text"], …], "ended": epoch_s|null,
  "unlocked": [tags], "revealed": [files]}`. This is clock.py's shape, so time left = `minutes - (now - start)/60`.
- `results.json`: `{"<tag>": {grade.py JSON + "at": minute, "after_time": bool}}` (latest Submit per tag), and `"final"` after End.
- Export → `export.zip` = `submission/` (work/), `session.json`, `results.json`, `manifest.json`.
