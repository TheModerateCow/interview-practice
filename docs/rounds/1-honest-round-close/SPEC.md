# Round 1: Honest round close

Findings addressed (docs/PRODUCT.md §7): F1, F2, F3, F4, the close-and-export half of F6, the Clock/Debrief half of F13.

## Problem

The app's only output is the truth about a timed round: what passed, by when, with which code. Today that truth is
wrong at exactly the moment it matters, the close:

- Every final grade says `after_time: true`, even when End was pressed 3 minutes into a 45-minute round
  (`server.py` `end()` sets `ended`, then `stamp()` asks `over()`, which is true whenever `ended` is set).
- 00:00 does not close the round. Nothing is graded; the card says "No results. Nothing was submitted." with code in the
  editor; after Close, Run/Submit/edit carry on with nothing on screen saying they are after time (A-26, A-18..21).
- The close is not atomic: a second End logs "end (after time)" and overwrites the final grade (the owner's log showed
  "end (after time)" 0.1 min into a 30-minute round); an End during an in-flight Run/Submit sets `ended`, fails with 409
  and never writes `final`; a Submit pressed at 29:50 that grades for 15 s is stamped after time.
- The export's `submission/` is the code at export time, so practice after the close reaches the debrief as the round.
- Export gives no confirmation, and the skill reads `ended` as "time is over" and re-derives time by hand.

Both personas lose: the candidate cannot tell what counts, and the interviewer agent's debrief ("say which results came
after time") repeats the app's wrong flags.

## Why this theme (and not the two strongest alternatives)

| | Honest round close (pick) | Every action answers (F5, F9, export toast) | Debrief kit (F7, F13, connect status.py / exports / hints) |
|---|---|---|---|
| User value | Makes the product's one output (the result of a round) true. Without it every debrief is wrong about lateness | Removes daily friction (the owner clicked My tests 10 times in a minute) | Lets a fresh Claude conversation debrief from the export |
| Persona impact | Both, every round | Candidate, most rounds | Agent, every debrief, but only once the data it reads is true |
| Effort | M: 5 small PRs, ~150 lines of code plus tests | S | M, mostly SKILL.md, and it would document today's wrong flags |
| Risk of waiting | High: every round played now produces untrue `results.json` | Low: annoying, not untrue | Medium: depends on this round's data being right first |

"Every action answers" is cheaper but cosmetic next to untrue results; the export toast from it is pulled into this round
because the export is the last step of the close. "Debrief kit" builds on the flags this round fixes, so it goes next.

## Definitions (these become the contract in API.md and FORMAT.md)

- **Deadline**: `start + minutes × 60`.
- **Close**: the first of End and the deadline. Closing is one event: it records `ended`, grades the unlocked tags once
  into `results.json` `final`, and snapshots the code. `ended` is never later than the deadline: a close requested after
  the deadline records `ended = deadline` and logs **"time up"** at the round's last minute; a close before it logs
  **"end"**.
- **After time**: an action that **started** after the close (after `ended`, or after the deadline if not yet closed).
  It is stamped from the moment the request arrived, not from when grading finished. The words stay "after time" so the
  skill and API vocabulary don't change; API.md defines them as "after the round closed".
- **Final grade's `after_time`**: true only if the graded code was edited after the deadline plus a 5-second grace (the
  autosave lag). A round closed on time, or reopened later without edits, reads on time.
- **Practice after the close** stays allowed (skill rule 4): Run, My tests, Submit, Next part and editing all work and are
  all marked after time. They never change `final` or the snapshot.

## Requirements

### R1. On-time results read on time (backend)
1. End before the deadline → event "end" with no suffix; every `final.<tag>.after_time` is `false`; `final.<tag>.at` is
   the close minute.
2. A Submit, Run or My tests that starts before the close is in time, however long grading takes.
3. Anything that starts after the close is "(after time)" in events and `after_time: true` in `results.json`.
4. After the close, `state.left_s` and `state.expired` stop moving (they describe the round at its close).

### R2. One close, whatever happens (backend)
1. Two concurrent Ends produce one "end" (or "time up") event and one final grade.
2. End during an in-flight Run/Submit waits for it (up to `grade_timeout_s` + 30 s) and then closes; it never leaves
   `ended` set without `final` for a set that has hidden tests. If the final grade failed (e.g. Docker down), the next End
   retries it.
3. A close requested after the deadline logs "time up" at minute = `minutes` and sets `ended` to the deadline.

### R3. 00:00 closes the round (UI)
1. When the timer reaches 00:00 in an open tab, the app saves the editor and closes the round (same call as End). A tab
   that was closed at 00:00 closes the round when it is next opened.
2. The final card is titled "Time's up" (closed by time) or "Interview ended" (End), shows the **final** grade per tag,
   the timeline, "Closed at mm:ss of N min", and the next step: "Export, then send export.zip to Claude for the debrief."
   It never says "Nothing was submitted" when there is code: a set without hidden tests says "This set has no hidden
   tests (Run only)".
3. After Close, a one-line bar under the toolbar stays for the rest of the session: "Round closed at mm:ss. Anything you
   run, test or submit now is marked after time." with "Show results" to reopen the card.
4. Grade rows show the word **after time** (status color plus the word) when `after_time` is true; Run and My tests
   results show it after the close.
5. Next part stays available after the close (marked after time in its confirm text), so a Levelled candidate can keep
   practising.
6. The timer shows the time that was left at the close and the label reads "closed".

### R4. The debrief gets the round's code (backend)
1. At the close the app copies `work/` to `data/sets/<name>/final/`.
2. Export adds `final/` (the code at the close) next to `submission/` (the code now). `submission/`, `session.json`,
   `results.json`, `manifest.json` keep their meaning. Sets closed before this change export without `final/`.

### R5. Export answers (UI)
1. Every Export click shows a toast: "Downloaded export.zip. Send it to Claude for the debrief. A copy is in
   data/exports/." A repeat click re-shows it visibly.

### R6. The skill reads the truth (docs)
1. SKILL.md "Clock": use `tools/status.py` in Claude Code; `ended` means the round closed, `expired` means time ran out.
2. SKILL.md "Results during the round": `results.json` carries `failed` names for the interviewer; never relay them before
   the close.
3. SKILL.md "Debrief": the official result is `results.json` `final` (graded at the close, names included); re-grade
   `final/` (or `submission/` for older exports) against the hidden tests in the kept `$W/set/`; say "after time" from the
   app's flags. Exports without `final/` predate the fix: their `final.*.after_time` is unreliable, use the event log.
4. README's re-grade command names a real tests path.

## Non-goals
- Locking the editor or blocking Submit after time (allowed by the skill).
- My tests feedback, import feedback, picker identity, timer warning thresholds (Now, next rounds).
- Putting hidden tests in the export (would leak them to the candidate).
- A server-side timer that closes rounds with no tab open: the next page load or End closes it, and `status.py` already
  reports `expired`. Add when a headless consumer needs `final` without a browser.
- Migrating old `results.json` files.

## Success measures
- The next real round: `results.json` `final.*.after_time` matches the event log (false for an on-time End).
- No session has an "end (after time)" before the deadline, or two close events.
- A round that hits 00:00 exports a `final` grade and a `final/` folder without the candidate pressing End.
- The owner exports once per round (no repeat clicks in `data/exports/` within a few seconds).

## Decisions defaulted (owner can override)
1. 00:00 closes the round automatically (it is the realistic behaviour, and the End dialog already promises a last grade).
2. Grace for the final grade: 5 s after the deadline (`GRACE_S`, one constant).
3. Post-close actions keep the words "after time" (no new "after end" vocabulary).
4. Export keeps `submission/` as the latest code and adds `final/`, rather than changing what `submission/` means.
5. End waits for an in-flight Run/Submit instead of failing.

## Open questions for the owner
1. Is "00:00 closes and grades the round" what you want, or should time up only grade and leave End to you?
2. Should `submission/` become the code at the close (stricter, simpler for the skill) instead of adding `final/`?
