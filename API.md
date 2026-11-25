# Interview Lab HTTP API (backend, behind nginx at http://127.0.0.1:8765)

Every `/api` request needs header `X-ILab: 1`, and Host `127.0.0.1:8765` or `localhost:8765`. An `Origin` header, if
present, must be `http://127.0.0.1:8765` or `http://localhost:8765`. Anything else gets **403**. Errors are `{"error": "..."}`
with a 4xx/5xx status. If Docker or the proxy is unreachable, the response is **503** `{"error": "Docker is unreachable ..."}`.
`<n>` = set name.

| Method & path | Body | Response |
|---|---|---|
| GET `/api/health` | | `{"ok": true, "docker": bool, "error": str\|null, "images": {"python": "ready"\|"pulling"\|"missing", "go":…, "java":…, "c":…, "javascript":…}}` |
| POST `/api/import` | raw zip bytes | `{"name": n, "title": t, "replaced": bool}` (`replaced`: an unstarted copy of that name was replaced), or 400 `{"error": "clear message"}`. A zip that fails the manifest checks gets "This zip is not a valid Interview Lab set. Ask Claude to pack it again. Details: …"; a started set gets 409 "You already started <n>, so it can't be replaced. Ask Claude for a copy with a new name." |
| GET `/api/sets` | | `{"sets": [{"name","title","language","round","minutes","left_s","status": "ready"\|"running"\|"ended"}]}`; `left_s` is seconds left, `null` unless running |
| GET `/api/sets/<n>` | | Ready info **only**: `{"name","title","company","role","round","language","difficulty","minutes","rules","status"}`. Never the problem, tags, parts or files |
| POST `/api/sets/<n>/start` | | state (below). The only thing that starts the clock. Starting again returns the existing state |
| GET `/api/sets/<n>/state` | | 409 `{"error":"not started"}` before Start, otherwise **state** |
| GET `/api/sets/<n>/files/<path>` | | text/plain file content from work/ (409 before Start) |
| PUT `/api/sets/<n>/files/<path>` | raw text | `{"ok": true}`. Writing to a new path creates the file |
| POST `/api/sets/<n>/run` | `{"file": path, "stdin": str}` | **run result** (below) |
| POST `/api/sets/<n>/mytests` | | grade JSON for the candidate's own tests (`your_tests` glob), `failed` names included |
| POST `/api/sets/<n>/submit` | | `{"results": {tag: grade JSON}, "revealed": ["l2.md", …], "state": state}` |
| POST `/api/sets/<n>/next` | | state (reveals the next locked part, logged "asked to move on") |
| POST `/api/sets/<n>/end` | | state (with `final`). Idempotent: waits for an in-flight Run/Submit, closes once and grades the unlocked tags once. After the deadline it closes as "time up" (`ended` = deadline) |
| DELETE `/api/sets/<n>` | | Soft delete: moves the folder to `data/deleted/<name>-<YYYYmmdd-HHMMSS>/` and returns `{"name","title","moved_to"}`. Nothing is erased; `data/exports/` is untouched. 409 `{"error":"This round is in progress. End it first, then delete it."}` while the set is running or a Run/Submit/grade is busy; 404 for an unknown name |
| GET `/api/sets/<n>/export` | | `application/zip` export.zip: submission/ (code now), final/ (code at the close, only if the round closed under this version), session.json, results.json, manifest.json |

**grade JSON**: `{"status": "graded"|"did not finish"|"could not be graded"|"no tests selected", "passed", "total",
"last_error"?, "last_line"?, "failed"? (names, only after End or time up), "at": minute, "after_time": bool}`
`at` and `after_time` describe when the action **started**: `after_time` means it started after the round closed (End or time up). In `final`, `at` is the close minute and `after_time` means the graded code was edited after the deadline (+5 s grace).

**state**:
```
{"name","title","company","role","round","language","difficulty","minutes","rules",
 "status": "running"|"ended", "start": epoch_s, "now": epoch_s, "left_s": float (>=0), "expired": bool, "ended": bool,   # left_s/expired freeze at the close
 "problem": "markdown", "parts": [{"file": "l2.md", "md": "..."}],   # revealed parts, in order
 "unlocked": ["test_l1_", ...], "has_next": bool,                     # has_next: a locked part remains (still true after the close; Next part after it is marked after time)
 "has_submit": bool, "has_mytests": bool, "run_entry": str|null, "testcases_count": int,
 "files": ["fleet.go", "cmd/run/main.go", ...],
 "results": {tag: grade JSON}, "final": {tag: grade JSON with failed}|null,
 "events": [[minute, "text"], ...]}
```

**run result**: Run executes the file in `file`. Testcases run only when `file == run_entry`.
```
{"compile": null | {"ok": bool, "log": str},
 "stdin_case": case,                      # the stdin box run
 "testcases": [case + {"expected": str, "pass": bool}],
 "memory_kb": int|null,                   # peak memory of the run container
 "verdict": "Accepted"|"Wrong Answer"|"Compile Error"|"Runtime Error"|"Time Limit Exceeded"|"Memory Limit Exceeded"}
case = {"stdout", "stderr", "exit": int|null, "ms": int, "truncated": bool, "verdict": ...}
```
