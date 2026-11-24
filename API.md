# Interview Lab HTTP API (backend, behind nginx at http://127.0.0.1:8765)

Every `/api` request needs header `X-ILab: 1`, and Host `127.0.0.1:8765` or `localhost:8765`. An `Origin` header, if
present, must be `http://127.0.0.1:8765` or `http://localhost:8765`. Anything else gets **403**. Errors are `{"error": "..."}`
with a 4xx/5xx status. If Docker or the proxy is unreachable, the response is **503** `{"error": "Docker is unreachable ..."}`.
`<n>` = set name.

| Method & path | Body | Response |
|---|---|---|
| GET `/api/health` | | `{"ok": true, "docker": bool, "error": str\|null, "images": {"python": "ready"\|"pulling"\|"missing", "go":…, "java":…, "c":…, "javascript":…}}` |
| POST `/api/import` | raw zip bytes | `{"name": n}` or 400 `{"error": "clear message"}` |
| GET `/api/sets` | | `{"sets": [{"name","title","language","round","status": "ready"\|"running"\|"ended"}]}` |
| GET `/api/sets/<n>` | | Ready info **only**: `{"name","title","company","role","round","language","difficulty","minutes","rules","status"}`. Never the problem, tags, parts or files |
| POST `/api/sets/<n>/start` | | state (below). The only thing that starts the clock. Starting again returns the existing state |
| GET `/api/sets/<n>/state` | | 409 `{"error":"not started"}` before Start, otherwise **state** |
| GET `/api/sets/<n>/files/<path>` | | text/plain file content from work/ (409 before Start) |
| PUT `/api/sets/<n>/files/<path>` | raw text | `{"ok": true}`. Writing to a new path creates the file |
| POST `/api/sets/<n>/run` | `{"file": path, "stdin": str}` | **run result** (below) |
| POST `/api/sets/<n>/mytests` | | grade JSON for the candidate's own tests (`your_tests` glob), `failed` names included |
| POST `/api/sets/<n>/submit` | | `{"results": {tag: grade JSON}, "revealed": ["l2.md", …], "state": state}` |
| POST `/api/sets/<n>/next` | | state (reveals the next locked part, logged "asked to move on") |
| POST `/api/sets/<n>/end` | | state (with `final`) |
| GET `/api/sets/<n>/export` | | `application/zip` export.zip: submission/, session.json, results.json, manifest.json |

**grade JSON**: `{"status": "graded"|"did not finish"|"could not be graded"|"no tests selected", "passed", "total",
"last_error"?, "last_line"?, "failed"? (names, only after End or time up), "at": minute, "after_time": bool}`

**state**:
```
{"name","title","company","role","round","language","difficulty","minutes","rules",
 "status": "running"|"ended", "start": epoch_s, "now": epoch_s, "left_s": float (>=0), "expired": bool, "ended": bool,
 "problem": "markdown", "parts": [{"file": "l2.md", "md": "..."}],   # revealed parts, in order
 "unlocked": ["test_l1_", ...], "has_next": bool,                     # has_next: a locked part remains
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
