# Round 1 HLD: Honest round close

Spec: `SPEC.md` in this folder. Code references are to `origin/main` (e537022).

## Today's flow and where it goes wrong

```
UI End ─► POST /end ─► end():  s = session()            (outside the lock: two Ends both see ended=None)
                               mutate: log("end"); ended = now
                               busy()  ─► 409 if a Run/Submit is in flight  (ended set, final never written)
                               grade_tags(...)
                               mutate: final = {t: stamp(s, r)}   stamp: after_time = over(s) = ended or expired → always true
UI 00:00 ─► tick(): poll().then(showFinal)              (no server call; card shows st.results or "Nothing was submitted")
submit():  grade (up to grade_timeout_s) ─► mutate: stamp(s, r)  (stamped when grading ends, not when it started)
export():  submission/ = work/ now
```

`over()` mixes two questions: "is the round closed?" (used for showing failed names and the `ended` status, which is
right) and "did this action happen after the round?" (used for `after_time` and the "(after time)" suffix, which needs the
action's own moment). The design splits them.

## Design

### Backend (`backend/server.py`)

```python
GRACE_S = 5   # ponytail: autosave lag + one request; raise if real rounds show false "after time" on the final grade

def deadline(s): return s["start"] + s["minutes"] * 60
def cutoff(s):   return s.get("ended") or deadline(s)          # ended <= deadline from this round on
def late(s, t):  return t > cutoff(s)
def minute(s, t): return round((t - s["start"]) / 60, 1)

def clock(s):                                                  # left/expired freeze at the close
    now = time.time(); stop = min(now, s["ended"]) if s.get("ended") else now
    left = s["minutes"] - (stop - s["start"]) / 60
    return (now - s["start"]) / 60, max(left, 0), left <= 0

def closed(s): return bool(s.get("ended")) or clock(s)[2]      # was over(); names + "ended" status only

def log(s, text, t=None):
    t = t or time.time()
    s["events"].append([minute(s, t), text + (" (after time)" if late(s, t) else "")])

def stamp(s, res, t): return res | {"at": minute(s, t), "after_time": late(s, t)}
```

- `run()`, `submit()`, `mytests()`: take `t0 = time.time()` on entry and pass it to `log()`/`stamp()`.
- `state()`: `has_next = bool(locked(s, m))` (no `ended` condition), `names = closed(s)`.
- `ready_info()`: status uses `closed(s)`.
- `end(n)`:
  1. Acquire the set's busy lock **blocking**, timeout `grade_timeout_s + 30`; on timeout 409 "a Run/Submit is still
     running". Lock order is always busy → set lock (`mutate()` never takes busy), so no deadlock.
  2. Under `mutate()`: if not yet ended, close: before the deadline `log("end", now); ended = now`; after it
     `ended = deadline; log("time up", deadline)`.
  3. (PR 2) If this call closed the round, copy `work/` to `final/` (`shutil.copytree`, keeps mtimes).
  4. If the set has hidden tests and `results.json` has no `final`, grade the unlocked tags and write
     `final = {t: r | {"at": minute(s, ended), "after_time": last_edit(n) > deadline(s) + GRACE_S}}`, where
     `last_edit` is the newest mtime under `final/` (PR 2) or `work/` (PR 1).
  5. Release the busy lock; return `state(n)`.
- `export(n)` (PR 2): also write `final/<rel>` for each file under `final/` if it exists.

Not changed: `start()`, import, files, `time_reveals()` (still stops at `ended`), the runner, grading.

### UI (`ui/app.js`, `ui/index.html`, `ui/style.css`)

- `tick()`: when `left === 0 && !st.ended`, call `autoClose()` once per poll period: `await save()`, `POST /end`,
  `setState`, `showFinal()`. It skips while `busy` (a Submit in flight finishes first, and the server waits too) and
  retries on the next 5-second poll on failure, showing the error in `#results` once.
- Timer: while `st.ended`, show `st.left_s` (frozen) and set the timer-wrap label to "closed"; `.over` only when
  `st.expired`.
- `showFinal()`: title from `st.expired` ("Time's up") or not ("Interview ended"); rows from `st.final` only; empty state
  "This set has no hidden tests (Run only)" when `!st.has_submit`, else "No final grade: <reason or 'press End to
  retry'>"; a line "Closed at mm:ss of N min"; a next-step line; actions unchanged (`#final-export`, `#final-close`).
- New `#closed-bar` (in `index.html`, under the toolbar, `role="status"`): shown when `st.ended` and the card is closed.
  Text plus `#closed-results` ghost button that calls `showFinal()`.
- `gradeRow()`: append `<span class="late">after time</span>` when `g.after_time`. `doRun()`/`doMyTests()`: add the same
  word to the result head when `st.ended`.
- `setState()`: `show('next-btn', s.has_next)`; `#next-bar` text gets "It is marked after time." when `st.ended`.
- `doExport()` (PR 4): after the download, `flash('Downloaded export.zip. Send it to Claude for the debrief. A copy is in data/exports/.')`.
  `flash()` restarts visibly when the same text is already showing (hide, force reflow, show).

Styles: `.closed-bar` = `--surface` background, 1px `--line` bottom border, `--fg-2` text, `--t-small`; `.late` =
`--warn` text with the word, no background, `--t-small` (`--warn` is 4.5:1+ on `--bg`/`--surface` in both themes:
#7a5900 on #f3f4f3, #fdca40 on #080708). No new tokens, no shadows, no second accent (Submit stays the only
`.btn-accent`; Export on the card stays `.btn-solid`).

### Data and interface changes (all backward compatible)

| Thing | Change |
|---|---|
| `session.json` | Same shape. `ended` is now never later than the deadline. New event text "time up". "(after time)" = started after the close |
| `results.json` | Same shape. `at`/`after_time` are taken when the action started. `final.<tag>.after_time` = code edited after the deadline + 5 s; `final.<tag>.at` = close minute |
| state (API) | Same fields. `left_s`/`expired` frozen at the close; `has_next` true after the close while a part is locked |
| POST `/end` | Idempotent; waits for an in-flight Run/Submit; after the deadline it closes as "time up" |
| `export.zip` | Adds `final/` when the round closed under this version. Other entries unchanged |
| `data/sets/<n>/final/` | New folder, written once at the close |

## PR plan

Order to open: **PR 1 → PR 4 → PR 5 (draft) → PR 2 → PR 3**. Merge in the same order, PR 5 last.

Parallel groups (disjoint files):
- **Group 1, start together:** PR 1 (backend), PR 4 (`doExport`/`flash` in `ui/app.js` only), PR 5 (SKILL.md, README.md;
  opened as a draft, merged after PR 2 so it documents what shipped). PR 3 may also be built now against this HLD's
  contract, but it merges after PR 2 and rebases on PR 4 (same file, different functions).
- **Stacked (unavoidable):** PR 2 on PR 1 (same functions in `server.py`, same doc sections).

Verification for every PR: on the running stack, never while the owner is in a live round (check
`data/sets/*/session.json` for a started, not-ended set with time left). Deploy backend with
`docker compose up -d --build backend`, UI with `docker compose build nginx && docker compose up -d nginx`. Check UI at
1440×900 and ~400 px, light and dark.

---

### PR 1: Stamp actions at their own moment; make End one atomic close
- **Files:** `backend/server.py`, `tests/api_test.py`, `API.md`, `FORMAT.md`.
- **Interface changes:** API.md: grade JSON `at`/`after_time` defined as "when the action started" / "started after the
  round closed (End or time up)"; final grade's `after_time` = "code edited after the deadline (+5 s)"; POST `/end`
  idempotent, waits for an in-flight Run/Submit, closes as "time up" after the deadline; state `left_s`/`expired` frozen
  at the close. FORMAT.md "Data written by the app": `ended` ≤ deadline, "time up" event, "(after time)" meaning.
- **Data changes:** none in shape; values now correct (see table above).
- **UI/UX conventions:** none (backend only).
- **Tests (api_test.py, new section "honest clock", 1-minute sets so it needs one ~62 s wait):**
  - set A: Start, Submit at once → `after_time false`; End at ~5 s → event "end" without suffix, `final.*.after_time
    false`, `final.*.at` ≤ 0.2; two `GET /state` 3 s apart give the same `left_s`; Submit after End → `after_time true`
    and "(after time)" in the event.
  - set B: two `POST /end` in parallel threads → exactly one close event in `session.json`, both 200.
  - set C (slow hidden test, `time.sleep(4)`): start a Submit in a thread, `POST /end` while it runs → End returns 200
    with `final` present; the Submit's stamp is in time.
  - sets D and E started together, wait until expired: D `POST /end` with no edits → event "time up" at 1.0,
    `session.ended == start + 60`, `final.*.after_time false`; E `PUT` a file, then `POST /end` → `final.*.after_time true`.
  - existing `grading()` flows keep passing; add `all(not g["after_time"] for g in final.values())` to the End check.
- **Acceptance (on the running product):**
  1. Import any set, Start, press End within the first minute: the final card's timeline shows "end" with no "(after
     time)"; `results.json` `final.*.after_time` is `false`.
  2. With a round open, run `curl -X POST -H 'X-ILab: 1' http://127.0.0.1:8765/api/sets/<n>/end` twice at once
     (`& wait`): `session.json` has one "end" event.
  3. Import a 1-minute set, Start, wait 70 s without the tab open (close it), then `POST /end`: event "time up" at 1.0,
     `final.*.after_time false`, `tools/status.py` prints `used_min 1.0`.
  4. `python3 tests/api_test.py` passes.

### PR 2 (stacked on PR 1): Snapshot the code at the close; keep Next part after the close
- **Files:** `backend/server.py` (`end()`, `export()`, `state()` `has_next`), `tests/api_test.py`, `API.md`, `FORMAT.md`.
- **Interface changes:** API.md export row: adds `final/`; state `has_next` no longer false after the close. FORMAT.md:
  `final/` under "Data written by the app" and in the export line.
- **Data changes:** new `data/sets/<n>/final/`; export adds `final/` only when present (older closed sets export as
  before). `last_edit` reads `final/`.
- **UI/UX conventions:** none (backend only; PR 3 uses `has_next`).
- **Tests:** after End, `PUT` a changed file, export → `final/<file>` has the code at End and `submission/<file>` has the
  new code; `final/` absent in the export of a set never closed; Levelled set: End, then `has_next` true and `POST /next`
  reveals with "(after time)".
- **Acceptance:**
  1. Start a set, edit, End, edit again, Export: the zip has `final/` with the code at End and `submission/` with the
     latest code; `session.json`, `results.json`, `manifest.json` still at the top.
  2. A Levelled set: End before L2 unlocks; `GET /state` shows `has_next: true`; `POST /next` reveals L2 and the event
     reads "revealed l2.md (asked to move on) (after time)".

### PR 3 (after PR 2; rebase on PR 4): 00:00 closes the round; the round screen says it is closed
- **Files:** `ui/app.js` (`tick`, new `autoClose`, `showFinal`, `gradeRow`, `doRun`, `doMyTests`, `setState`),
  `ui/index.html` (`#closed-bar`, `#closed-results`, an id on the timer-wrap label: `#timer-label`), `ui/style.css`
  (`.closed-bar`, `.late`), `tests/e2e.spec.mjs`, `tests/e2e.sh` (second zip with `minutes: 1`, env `E2E_NAME_1M`).
- **Interface changes:** none (uses PR 1/2 contract).
- **Data changes:** none.
- **UI/UX conventions:** tokens only (`--surface`, `--line`, `--fg-2`, `--warn`); borders not shadows; status color always
  with the word "after time"; Submit stays the only accent; headings weight 400; 4.5:1 text. Keeps every id the e2e uses:
  `#dropzone #ready #set-picker #problem #start-btn #round #timer #run-btn #verdict #submit-btn #results #end-btn
  #end-confirm #final #final-export #export-btn`. The bar wraps at 400 px with no horizontal scroll.
- **Tests:** e2e main flow: after End, `#final .late` count is 0, then Close → `#closed-bar` visible. New e2e test
  "time up closes the round": drop the 1-minute zip, Start, wait for `#final` (≤ 90 s) → contains "Time's up" and
  `\d+/\d+`; `#final .late` count 0; Close → `#closed-bar` visible; Submit → `#results .late` visible; API state:
  `ended` true, `final[tag].after_time` false; events include "time up" and no "end (after time)". e2e.sh's export
  check also asserts a `final/` entry (the main flow ends with End).
  `node --check ui/app.js`.
- **Acceptance:**
  1. Import a 1-minute set, Start, type a fix, do not press anything: at 00:00 the card says "Time's up" with a final
     N/M per tag (not "Nothing was submitted") and "Closed at 01:00 of 1 min".
  2. Close the card: the bar "Round closed at 01:00 …" stays; Submit shows its grade row with "after time"; the timeline
     (Show results) marks it "(after time)"; the final rows do not.
  3. End a 30-minute set at ~2 min: the timer stops at ~28:00 with label "closed" (not red 00:00); the card title is
     "Interview ended".
  4. A Levelled set closed before L2: Next part is visible and its confirm says "It is marked after time."
  5. Light and dark, 1440×900 and 400 px: bar and "after time" words readable, no horizontal scroll.
  6. `tests/e2e.sh` ends with `2 passed` and `PASS export.zip contents`.

### PR 4: Export says it worked
- **Files:** `ui/app.js` (`doExport`, `flash`).
- **Interface changes / data changes:** none.
- **UI/UX conventions:** existing `.toast` (inverse colors), no new styles; text says what happened and what to do next.
- **Tests:** e2e: after the export download, `#flash` is visible and contains "export.zip". `node --check ui/app.js`.
- **Acceptance:**
  1. Click Export in the toolbar, then in the final card: each click shows the toast "Downloaded export.zip. Send it to
     Claude for the debrief. A copy is in data/exports/."; a second click within 5 s visibly re-shows it.
  2. `data/exports/` has one new zip per click.

### PR 5 (draft first; merge after PR 2): The skill and README read the truth
- **Files:** `skill/interview-practice/SKILL.md` ("Standing rules" rule 1 wording, "Clock", "Results during the round",
  "Debrief" in Coding rounds, "Debrief (all coding rounds)" item 1), `README.md` (re-grade command, `final/` in the
  export description).
- **Interface changes:** SKILL.md as in SPEC R6. The synced copy under `~/.claude/skills/synced/` is refreshed by the
  owner after merge (not part of the PR).
- **Data changes:** none.
- **UI/UX conventions:** n/a; neutral placeholders only (Acme), no company or role named.
- **Tests:** none automated; `grep -n "status.py\|final/\|expired" skill/interview-practice/SKILL.md` shows the new text;
  SKILL.md does not grow by more than 20 lines.
- **Acceptance:**
  1. Following SKILL.md "Clock" in Claude Code against a set ended early gives the correct "ended with N min left", not
     "time is over".
  2. Following SKILL.md "Debrief" on an export from PR 2 uses `results.json` `final`, re-grades `final/` against the
     kept `$W/set/`, and reports "after time" only for actions the event log marks.
  3. The README re-grade command runs as written against an unzipped export plus the set folder.
