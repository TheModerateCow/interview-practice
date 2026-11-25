# Round 2: Drop to ready

Findings addressed (docs/PRODUCT.md §7): the import half of F9 and of F5 ("every click answers"), the picker half of F8,
F12, the import-error wording from A-report finding 13, and the round-1 follow-up "a drop within ~1 s of page load can
be overridden by the app's own first load".

## Problem

The hand-off from Claude's zip to the right ready screen is the one step that cannot be undone. Once the candidate
presses Start, the clock runs and that set can never be imported again under its name. Today that step is guesswork:

- **A drop gives no answer.** A good drop just changes the screen. Dropping the same unstarted zip again replaces it with
  no message (A-report finding 6, shot A-31).
- **A failed drop looks like a success.** With a set open, a bad zip leaves that set's ready screen and its Start button
  on screen, under a red toast in the corner. Nothing says "not imported" (B-report finding 5, shot B-E-e2a-error).
  The reason is written for set authors: `invalid set: format: must be "interview-set/1"; problem.md missing` (A-28).
- **Sets look alike.** The header picker shows the title and a raw status, so five copies read "Rate limiter · ready"
  (A-report finding 5, B-report finding 4, shot A-03). The ready screen never shows the set's name, which is the name
  Claude, the error messages and the data folder use.
- **The drop can lose.** With a round in progress, a drop made while the page is still loading can be overridden by the
  app reopening the round (found in round-1 verification; `tests/e2e.spec.mjs` works around it with a fallback click).
- **Broken sets reach the candidate.** `tools/pack.py` and the importer accept a reveal chain that can never work: a part
  whose tag no hidden test carries, the same part file revealed twice, two parts unlocking the same tag (B-report §4,
  cases C1–C3). The candidate finds out mid-round, when Part 3 can never pass or Part 2 shows up twice.

The candidate loses: they can start the wrong set, or a broken one, and burn it. The interviewer agent loses: it cannot
tell the candidate what to look for, and its own packing mistakes surface only after the clock started.

## Why this theme (and not the alternatives)

| | Drop to ready (pick) | During the round (F5 My tests, F11 timer cues, F10 finish state) | Debrief kit (F7, F13 remainder) |
|---|---|---|---|
| User value | Makes the one irreversible step safe: the right set, confirmed, before Start | Removes friction in a round already under way | Saves Claude hand work in the debrief |
| Persona impact | Both, every round: the candidate starts each round here; Claude's pack mistakes are caught here | Candidate, most rounds | Agent, every debrief; round 1 already moved it onto the true `final` grade and `final/` code |
| Effort | S–M: 5 small PRs, mostly UI, one small validator change | S–M | M, mostly SKILL.md |
| Cost of waiting | High: a wrong or broken Start burns the set and the candidate's time | Low: annoying, not lossy | Low: the debrief works today with the kept set |

Rejected, one line each:
- **Timer cues (F11):** real but small. It belongs with My tests and the finish state in a "during the round" theme.
- **Finish state (F10), narrow layout (F14), editor and results (F15, F16):** in-round ergonomics; next round's theme.
- **Debrief kit (F7, F13):** round 1 fixed what made the debrief wrong; what is left is comfort, not correctness.
- **Tests leave `t-*` sets in the picker:** already fixed by #13 (tests run on their own stack, `tests/stack.sh`).
  Sets left by earlier runs need "Archive sets" (Later).

## What is missing in the code today

All references are to `main` at 6003d09.

| Gap | Where |
|---|---|
| No success message after a drop | `ui/src/App.svelte` `onDrop()` calls `loadSets(name)` and nothing else |
| Import doesn't say it replaced a set | `backend/server.py` `do_import()` deletes the unstarted set and returns only `{"name": n}` |
| Failure toast doesn't name the zip or say "not imported" | `onDrop()`: `showFlash('Import failed: ' + err.message, true)`, and only when a set is open |
| Author-speak reasons | `do_import()`: `"invalid set: " + "; ".join(errs)` |
| Picker shows title and raw status | `App.svelte` header: `options={sets.map(s => ({ value: s.name, label: s.title, meta: s.status }))}` |
| No time left anywhere outside the round | `server.py` `r_sets()` returns name, title, language, round, status only |
| Ready screen without the set's name | `App.svelte` `#ready` card: eyebrow, title, pills, rules |
| A late navigation overwrites a newer one | `loadSets()`, `openSet()`, `enterRound()` and `goHome()` all await network or Monaco, then set the screen, with no check that they are still the latest |
| Reveal chains and tags unchecked | `tools/pack.py` `validate()` checks each reveal entry alone; nothing reads the hidden tests. The same code is copied into `skill/interview-practice/SKILL.md` |

## Definitions

- **Navigation:** anything that decides which screen shows: the first page load, a drop, a picker choice, a row on Home,
  "All sets", Start. **The latest navigation wins**; an older one that finishes later does nothing.
- **Set identity:** title plus name. The name is the manifest's `name` (the folder under `data/sets/`).
- **Status words** (the Home groups already use them): "not started", "N min left" (running), "finished".

## Requirements

### R1. The drop wins (UI)
1. The screen after a drop is the dropped set's ready screen, even if the page was still opening another set.
2. The same holds for every navigation: two quick picker choices end on the second; "All sets" during loading ends on Home.
3. A click made while a drop is still importing wins over the drop; the import still finishes and says so (R2).

### R2. Every drop answers (UI, backend)
1. A good drop shows a toast: "Imported Rate limiter (rate-limiter-py)." and opens its ready screen.
2. A drop that replaces an unstarted set says so: "Imported Rate limiter (rate-limiter-py), replacing the copy you
   hadn't started."
3. A failed drop shows a red toast that starts "Not imported: <file name>." and gives the reason. On Home the drop box
   shows the same text. The screen does not change.
4. Reasons are in plain words, with the author detail after them:
   - Not a valid set: "This zip is not a valid Interview Lab set. Ask Claude to pack it again. Details: …"
   - Already started: "You already started rate-limiter-py, so it can't be replaced. Ask Claude for a copy with a new
     name."
   - Not a zip, too big, unsafe paths: today's messages, which are already plain.
5. Error toasts stay 10 s (other toasts stay 5 s, as today).

### R3. Sets say which is which (UI, backend)
1. Each picker row shows the title, then the name and status words: "Rate limiter   rate-limiter-py · not started".
2. A running set shows its time left: "rate-limiter-b · 18 min left". It refreshes with each 5-second poll.
3. Home rows in "In progress" add the time left to the meta line ("Codebase round · Python · 18 min left").
4. The ready screen shows the name under the title, in the mono font.

### R4. Pack and import catch broken reveal chains (pack.py, importer, skill copy)
1. Two `reveal` entries that unlock the same tag → `reveal[1].unlocks: test_p2_ is already unlocked by reveal[0]`.
2. The same file in two `reveal` entries → `reveal[1].file: .hidden/p2.md is already revealed by reveal[0]`.
3. An `after_tag` that is neither unlocked at Start nor unlocked by another entry (for example it equals the entry's own
   `unlocks`) → `reveal[0].after_tag: test_p2_ is never unlocked before this part, so passing it can't reveal it`.
4. When the set has hidden tests, every tag must appear in the hidden-tests file (case-insensitive text match, the same
   matching the grader uses) → `tags: test_p3_ matches no test in .hidden/tests_hidden.py`.
5. The "existing path under .hidden/" message splits in two: "must be a path under .hidden/" and "<path> is missing
   (pack.py looks in .hidden/, the set folder and levels/)" (B-report finding 3, case B2).
6. `pack.py` prints these as `NOT PACKED:` lines; the importer refuses with them in the R2.4 "Details". The copy of
   `pack.py` inside SKILL.md stays identical to `tools/pack.py`.

### R5. The skill tells the candidate what to look for (docs)
1. SKILL.md "Delivery" and README: after the drop, the app says "Imported <title> (<name>)" and the ready screen shows
   the name; check it matches before pressing Start. If it says "Not imported", paste the message back to Claude.

## Non-goals
- My tests feedback (the in-round half of F5), timer cues (F11), the finish state (F10): next round.
- Deleting or archiving sets from the picker (Later: "Archive sets"). `data/` is never wiped.
- Asking before replacing an unstarted set: it is replaced, and now the toast says so.
- A second import path (file picker, URL): drag-and-drop stays the only one.
- Showing anything more on the ready screen than today plus the name. No problem text, tags, parts or files.

## Success measures
- The next five real rounds: no set started by mistake (no started set that is never exported).
- `tests/e2e.spec.mjs` drops right after page load with a round in progress and needs no fallback click.
- B-report cases C1–C3 fail at pack time with a message naming the field.
- Every drop in a usage test ends in a toast that names the set or the zip.

## Decisions defaulted (owner can override)
1. Re-dropping an unstarted set still replaces it, and the toast says so. No "keep both" choice.
2. The tag check is a text match against the hidden-tests file, not a test run. A tag that only appears in a comment
   passes; the gate's run of the reference still catches a part with no real tests.
3. The picker always shows the name, not only when two titles collide.
4. Error toasts stay 10 s instead of 5 s.

## Decided by the owner (2026-11-25)
1. A drop during a round in progress asks first: "Open <file name>? Your round keeps running while you're away."
   Stay (the default, and Esc) imports nothing and keeps the round; Open carries on with the drop. The round keeps its
   clock either way. Built in PR 1 (HLD, PR 1 "Owner decision").
