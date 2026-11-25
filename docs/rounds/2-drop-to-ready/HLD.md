# Round 2 HLD: Drop to ready

Spec: `SPEC.md` in this folder. Code references are to `main` at 6003d09.

## Today's flow and where it goes wrong

```
page load ─► onMount: loadSets() ─► GET /sets ─► a round is running? openSet(it) : goHome()
              openSet(): leaveSet() → GET /sets/<n> → enterRound(): await editor() (Monaco, ~1 s) → openFile(cur …)
                         nothing checks that this is still the screen the user asked for
drop ──────► onDrop(): POST /import ─► {"name"} ─► loadSets(name) ─► openSet(name)        (no toast on success)
              on error: showFlash('Import failed: ' + msg) only if a set is open; the open set stays on screen
              a drop while the first openSet() waits for Monaco: the old enterRound() resumes on the new cur,
              st is null by then, and the error lands on the new set's ready screen in place of Start
do_import(): unstarted set with the same name? rmtree + replace, return {"name"}         (caller can't tell)
             invalid → 400 "invalid set: <field errors>"; started → 409 "… Change "name" in manifest.json …"
header picker: options = {label: title, meta: status}  →  "Rate limiter · ready" five times
ready card:    eyebrow, title, pills, rules, Start      →  no name
pack.validate(): each reveal entry checked alone; hidden-tests content never read
                 → duplicate unlocks, the same file twice, tags with no tests: all "packed"
```

Reproduced while writing this plan, with today's `tools/pack.py` on a copy of `tests/sets/rate-limiter-py`:
adding a third part (`tags` + `test_p3_`, a reveal of `.hidden/p3.md` unlocking it) printed `packed 7 files`; revealing
`.hidden/p2.md` twice printed `packed 6 files`. Neither set can be played as written.

## Design

### UI: the latest navigation wins (`ui/src/App.svelte`)

One counter, checked after every wait. This fixes the drop race and every sibling (two quick picker choices, "All sets"
while a set opens, a Home row while the first load resumes a round) in one place.

```js
let nav = 0;   // bumped by every navigation; an older async step that sees a newer value stops

async function openSet(name, my = ++nav) {
  await leaveSet(); if (my !== nav) return;
  cur = name; …
  const i = await api('/sets/' + name); if (my !== nav) return;
  if (i.status === 'ready') { …; return; }
  await enterRound(await api('/sets/' + name + '/state'), my);
  // catch: only show the error if my === nav
}
async function enterRound(s, my) { …; await flush(); await editor(); if (my !== nav) return;
  if (first) await openFile(first); if (my !== nav) return; …start poll/tick… }
async function goHome() { const my = ++nav; await leaveSet(); if (my !== nav) return; … }
async function loadSets(select, my = nav) {  // first load, and after an import
  sets = (await api('/sets')).sets;
  if (my !== nav) return;                   // something newer (a drop, a click) happened while we waited
  if (select) return openSet(select);
  …resume or goHome… }
startRound: enterRound(state, ++nav)
onDrop: const my = ++nav before POST /import  // a first load still in flight never lands on top of the drop
        on success: loadSets(name, my)        // opens the set unless the user clicked elsewhere during the import
```

`openFile()` keeps its own guard: it reads `cur` once and returns without touching Monaco if `cur` changed while it
waited. No new state is shown; nothing changes for a user who never races.

### UI and backend: every drop answers

Backend, `do_import()`:

```python
if errs: raise HTTPError(400, "This zip is not a valid Interview Lab set. Ask Claude to pack it again. Details: " + "; ".join(errs))
…started → HTTPError(409, f"You already started {n}, so it can't be replaced. Ask Claude for a copy with a new name.")
replaced = os.path.isdir(dest)          # read under the set lock, before the replace
return {"name": n, "title": m["title"], "replaced": replaced}
```

UI, `onDrop()` and `showFlash()`:

```js
const { name, title, replaced } = await api('/import', …);
showFlash('Imported ' + title + ' (' + name + ')' + (replaced ? ", replacing the copy you hadn't started." : '.'));
await loadSets(name, my);              // PR 1's navigation number, taken before the import
// catch:
const msg = 'Not imported: ' + f.name + '. ' + err.message;
dropErr = msg; showFlash(msg, true);       // always, on Home too; the screen stays as it was
showFlash(text, bad): hide after bad ? 10000 : 5000 ms
```

### UI and backend: sets say which is which

Backend, `r_sets()`: each row adds `minutes` and `left_s` (seconds left from `clock()`, rounded; `null` unless the
status is `running`). Same rule as `state.left_s`: it freezes at the close, and a closed set has status `ended`.

UI:
- Status words, one helper next to `mmss` in `lib.js`: `statusWords(s)` → "not started" · "N min left" · "finished".
- Picker: `options = sets.map(s => ({ value: s.name, label: s.title, meta: s.name + ' · ' + statusWords(s) }))`.
  `setState()` also copies `s.left_s` onto the picker row, so the meta follows the 5-second poll.
- Home rows: the `.set-meta` line adds `statusWords(s)` for running sets. `.set-name` keeps the bare name (the e2e
  matches it exactly).
- Ready card: `<div id="ready-name" class="mono muted">{info.name}</div>` right under the `<h1>`. Existing classes only.

### Pack and import: reveal chains (`tools/pack.py`, used by the importer and copied into SKILL.md)

`validate(m, exists, read=None)`: `read(path) -> bytes` is optional, so old callers keep working.

```python
start = set(tags) - {r.get("unlocks") for r in rv if isinstance(r, dict)}
seen_file, seen_unlock = {}, {}
for i, r in enumerate(rv):
    f = r.get("file")
    if not under_hidden(f):        e.append(f"reveal[{i}].file: must be a path under .hidden/")
    elif not exists(f):            e.append(f"reveal[{i}].file: {f} is missing (pack.py looks in .hidden/, the set folder and levels/)")
    elif f in seen_file:           e.append(f"reveal[{i}].file: {f} is already revealed by reveal[{seen_file[f]}]")
    else: seen_file[f] = i
    u, a = r.get("unlocks"), r.get("after_tag")
    if u in seen_unlock:           e.append(f"reveal[{i}].unlocks: {u} is already unlocked by reveal[{seen_unlock[u]}]")
    elif u is not None: seen_unlock[u] = i
    if a in tags and a not in start and not any(o.get("unlocks") == a for j, o in enumerate(rv) if j != i and isinstance(o, dict)):
        e.append(f"reveal[{i}].after_tag: {a} is never unlocked before this part, so passing it can't reveal it")
if ht and read and not ht_errors:
    text = read(ht).decode(errors="replace").lower()
    # ponytail: text match, the grader's own case-insensitive substring rule; a tag that only appears in a comment
    # passes. The gate's run of the reference is the exact check.
    e += [f"tags: {t} matches no test in {ht}" for t in tags if t.lower() not in text]
```

Callers: `pack()` passes `read=lambda p: open(src[p], "rb").read()`; `do_import()` passes `read=lambda p: z.read(keep[p])`.
The SKILL.md copy of `pack.py` is replaced with the new file, byte for byte.

### Data and interface changes (all backward compatible)

| Thing | Change |
|---|---|
| POST `/api/import` | 200 body adds `title` and `replaced` (bool). 400/409 messages reworded (still `{"error"}`) |
| GET `/api/sets` | Each row adds `minutes` and `left_s` (`null` unless running) |
| `pack.validate()` | Optional third argument `read`. New error lines for reveal chains and tags |
| `session.json`, `results.json`, `export.zip`, `data/` layout | Unchanged |

UI rules for every PR: tokens from `ui/tokens.css` only; borders, not shadows; headings weight 400; Submit stays the only
accent; status color always with a word (the red toast says "Not imported"); 4.5:1 text (`--fg-3` on `--bg` is about
4.8:1 light and 5.2:1 dark). Check 1440×900 and 400 px, light and dark, no horizontal scroll. Keep every id and class the
e2e uses: `#dropzone #drop-error #ready #set-picker #set-picker-list [data-value] #problem #start-btn #round #timer
#run-btn #verdict #submit-btn #results #end-btn #end-confirm #final #final-export #final-close #export-btn #flash
#closed-bar #home-btn .set-row .set-name`.

## Making the example zips

Several examples need a second copy of the sample set under another name. From the repo root:

```bash
python3 - tests/sets/_zips/rate-limiter-py.zip /tmp/rate-limiter-b.zip rate-limiter-b <<'PY'
import json, sys, zipfile
src, dst, name = sys.argv[1:]
with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w") as zo:
    for i in zi.infolist():
        d = zi.read(i)
        if i.filename.endswith("manifest.json"): m = json.loads(d); m["name"] = name; d = json.dumps(m).encode()
        zo.writestr(i, d)
PY
```

Verify on the isolated test stack (`tests/stack.sh up`, http://127.0.0.1:8766, its own empty data folder), never on the
owner's app at 8765. Backend changes deploy with `tests/stack.sh up` (it rebuilds from the checkout).

## PR plan

**Parallel groups (start together):** PR 1, PR 3 and PR 4. PR 5 opens as a draft at the same time.
**Stacked (unavoidable):** PR 2 on PR 1. Both rewrite `onDrop()`; PR 2's success path calls the navigation PR 1 adds.
**Merge order:** PR 4 → PR 1 → PR 3 → PR 2 → PR 5.

Files more than one PR edits (each PR edits different functions or adds its own section; rebase, don't merge blind):

| File | PRs | What each touches |
|---|---|---|
| `ui/src/App.svelte` | 1, 2, 3 | 1: `openSet` `enterRound` `goHome` `loadSets` `startRound` `openFile`, first line of `onDrop`. 2: rest of `onDrop`, `showFlash`. 3: header picker, Home rows, ready card markup, one line in `setState` |
| `backend/server.py` | 2, 3, 4 | 2: `do_import` messages and return. 3: `r_sets`. 4: the `pack.validate(…)` call in `do_import` |
| `tests/api_test.py` | 2, 3, 4 | each adds its own `@sec`; 4 also fixes the `t-snap-lvl` fixture |
| `tests/e2e.spec.mjs` | 1, 2, 3 | 1: new test + removes the fallback in the main flow. 2 and 3: new asserts after the main flow's drop |
| `API.md` | 2, 3 | 2: the import row. 3: the sets row |
| `FORMAT.md` | 2, 4 | 2: the `name` row. 4: the `tags` and `reveal` rows |
| `skill/interview-practice/SKILL.md` | 4, 5 | 4: the embedded `pack.py`. 5: "Delivery" |

---

### PR 1: The set you drop is the set you get
- **Example** (round-1 verification, PRODUCT.md "Still open"; `tests/e2e.spec.mjs` lines 47–49 work around it):
  1. Drop `rate-limiter-py.zip`, press Start (a round is now in progress).
  2. Make `/tmp/rate-limiter-b.zip` (above). Reload the page.
  3. While "Opening Rate limiter…" or "Loading the editor…" still shows (about the first second), drop `rate-limiter-b.zip`.
  - **Expected:** the ready screen for the second copy, with Start, and it stays.
  - **Got today** (traced in the code; the PR's first step is to reproduce it): the first load finishes after the drop
    and lands on the new set. The ready screen shows a red error ("Cannot read properties of null…") where Start should
    be, or the round in progress comes back.
- **Files:** `ui/src/App.svelte`, `tests/e2e.spec.mjs`, `tests/e2e.sh`.
- **Interface changes:** none. **Data changes:** none.
- **UI conventions:** no visible change except the bug going away.
- **Tests:**
  - `e2e.sh`: build the zips from one loop of (name, minutes) pairs: main, `-1m`, and two new ones, `-run` and `-race`.
  - New e2e test "a drop during page load wins": import and Start `-run` through the API; `page.goto(BASE)` and drop
    `-race` at once, without waiting; expect `#ready` to contain the title and `#start-btn` visible; wait 3 s; still
    `#ready`, `#round` hidden, no `#ready .err`.
  - Main flow: replace the try/catch fallback (lines 47–49) with a plain `expect('#ready').toContainText(title)`.
  - `npm run build` in `ui/` succeeds.
- **Acceptance:**
  1. The example above, five times in a row: each time the second copy's ready screen with Start, and it stays.
  2. Open the picker and choose two sets quickly one after the other: the second one's screen shows.
  3. `tests/run_all.sh` ends with every step PASS.

### PR 2 (stacked on PR 1): Every drop says what happened
- **Example** (A-report finding 6 and shot A-31; B-report finding 5 and shot B-E-e2a-error; A-28 for the wording):
  1. On Home, drop `tests/sets/_zips/rate-limiter-py.zip`.
  2. On its ready screen, drop the same zip again.
  3. Drop `tests/sets/_zips/invalid-bad-manifest.zip`.
  - **Expected:** 1: toast "Imported Rate limiter (rate-limiter-py)." 2: toast "Imported Rate limiter (rate-limiter-py),
    replacing the copy you hadn't started." 3: red toast "Not imported: invalid-bad-manifest.zip. This zip is not a valid
    Interview Lab set. Ask Claude to pack it again. Details: format: must be "interview-set/1"; problem.md missing";
    Rate limiter's ready screen stays.
  - **Got today:** 1 and 2: the ready screen appears with no message, and step 2 changes nothing visible. 3: Rate
    limiter's ready screen and Start stay, with a red corner toast "Import failed: invalid set: format: must be
    "interview-set/1"; problem.md missing". Nothing says the zip on screen is not the one just dropped.
- **Files:** `backend/server.py` (`do_import`), `ui/src/App.svelte` (`onDrop`, `showFlash`), `API.md` (import row),
  `FORMAT.md` (`name` row: "the app says it replaced it"), `tests/api_test.py`, `tests/e2e.spec.mjs`.
- **Interface changes:** POST `/api/import` 200 body `{"name", "title", "replaced"}`; 400 "invalid set" and 409 "already
  started" messages reworded as in SPEC R2.4.
- **Data changes:** none.
- **UI conventions:** the existing `.toast` and `.toast.bad`; the bad toast's text starts with the words "Not imported",
  so the red never carries the meaning alone. No new styles.
- **Tests:**
  - `api_test.py` new section "import answers": first import → `replaced` false and `title` set; same zip again →
    `replaced` true; Start it, import again → 409 whose error contains "new name"; the bad-manifest zip → 400 whose
    error starts "This zip is not a valid Interview Lab set" and still contains `format:`.
  - e2e main flow: after the drop, `#flash` contains "Imported" and the set name. Then drop
    `/work/tests/sets/_zips/invalid-bad-manifest.zip` (as a `File` named `invalid-bad-manifest.zip`): `#flash.bad`
    contains "Not imported: invalid-bad-manifest.zip" and `#ready` still contains the title.
- **Acceptance:**
  1. The example's three drops give the three expected toasts; the red one stays about 10 s.
  2. Drop a `.txt` file: "Not imported: notes.txt. not a zip file", screen unchanged.
  3. Drop a zip of a set you already started: the toast says it can't be replaced and to ask Claude for a copy with a
     new name.
  4. On Home with no set open, a bad drop shows the same text in the drop box and in the toast.
  5. 400 px, light and dark: the toast wraps inside the window, no horizontal scroll.

### PR 3: Sets say which is which
- **Example** (A-report finding 5, B-report finding 4, shot A-03):
  1. Drop `rate-limiter-py.zip` and `/tmp/rate-limiter-b.zip` (same title, different name).
  2. Open `rate-limiter-b` and press Start.
  3. Open the header picker. Then open `rate-limiter-py` from it.
  - **Expected:** the picker reads "Rate limiter   rate-limiter-py · not started" and "Rate limiter   rate-limiter-b ·
    30 min left" (just started); the ready screen shows `rate-limiter-py` under the title.
  - **Got today:** the picker reads "Rate limiter   ready" and "Rate limiter   running"; with two unstarted copies,
    both rows read "Rate limiter   ready". The ready screen shows no name.
- **Files:** `backend/server.py` (`r_sets`), `ui/src/lib.js` (`statusWords`), `ui/src/App.svelte` (picker options, Home
  rows, ready card, `setState`), `API.md` (sets row), `tests/api_test.py`, `tests/e2e.spec.mjs`.
- **Interface changes:** GET `/api/sets` rows add `minutes` and `left_s` (`null` unless running).
- **Data changes:** none.
- **UI conventions:** existing `Dropdown` meta slot, `.set-meta`, `.mono`, `.muted`; the picker button's title still
  ellipsizes before its meta; status as words, never color alone. New id `#ready-name`.
- **Tests:**
  - `api_test.py`: a ready set's row has `left_s` null and `minutes`; after Start, `0 < left_s <= minutes × 60`; after
    End, status `ended`.
  - e2e main flow: `#ready-name` has the set name; open `#set-picker`: the option `[data-value=NAME]` contains NAME and
    "not started"; after Start it contains "min left".
- **Acceptance:**
  1. The example: the expected picker rows and ready-screen name.
  2. Home, "In progress" row: "Codebase round · Python · 29 min left"; it goes down a minute after a minute on the
     round screen and a return to Home.
  3. 1440×900 and 400 px, light and dark: the picker button and list fit, no horizontal scroll; the name under the
     title is readable.

### PR 4: Pack and import catch broken reveal chains
- **Example** (B-report §4, cases C1 and C3; reproduced on `main` while writing this plan):
  1. Copy `tests/sets/rate-limiter-py` to a scratch folder. Copy `levels/p2.md` to `levels/p3.md`.
  2. In `manifest.json`, add `"test_p3_"` to `tags` and a reveal `{"file": ".hidden/p3.md", "after_tag": "test_p2_",
     "unlocks": "test_p3_"}`. Run `python3 tools/pack.py <folder> /tmp/c1.zip`.
  3. Instead, add a second reveal of `.hidden/p2.md` that also unlocks `test_p2_`. Pack again.
  - **Expected:** `NOT PACKED:` with `tags: test_p3_ matches no test in .hidden/tests_hidden.py` (step 2), and
    `reveal[1].file: .hidden/p2.md is already revealed by reveal[0]` plus `reveal[1].unlocks: test_p2_ is already
    unlocked by reveal[0]` (step 3). Dropping a hand-made zip of either is refused with the same lines.
  - **Got today:** `packed 7 files` and `packed 6 files`. Played, the first set shows Part 3 that grades "no tests
    selected" forever; the second shows Part 2's text twice in the problem pane.
- **Files:** `tools/pack.py`, `skill/interview-practice/SKILL.md` (the embedded `pack.py` only), `backend/server.py` (the
  `validate` call in `do_import`), `FORMAT.md` (`tags` and `reveal` rows), `tests/api_test.py`.
- **Interface changes:** `validate(m, exists, read=None)`; new error lines (SPEC R4).
- **Data changes:** none. Sets already imported are not re-checked.
- **UI conventions:** none (the importer's message reaches the toast unchanged; after PR 2 it sits under "Details:").
- **Tests:** `api_test.py` new section "manifest sanity": hand-made zips for C1 (tag with no test), C2 (two files
  unlocking one tag), C3 (one file twice) and a self `after_tag` → 400 each, with the field named; `python3 tools/pack.py`
  on every `tests/sets/*` folder still prints `packed`; the `pack.py` and `gate.py` blocks in SKILL.md equal
  `tools/pack.py` and `backend/gate.py`. Fix the `t-snap-lvl` fixture (its hidden tests gain `def test_l2_a`).
- **Acceptance:**
  1. The example's two packs print the expected `NOT PACKED:` lines.
  2. `python3 tools/pack.py tests/sets/rate-limiter-py /tmp/ok.zip` still prints `packed 6 files`.
  3. Drop the bad hand-made zip on the test stack: refused, with the same field lines.
  4. `tests/run_all.sh` ends with every step PASS.

### PR 5 (draft first; merge after PR 2 and PR 3): The skill tells the candidate what to look for
- **Example** (B-report steps 2.1 and finding 4; A-report finding 6):
  1. As Claude, follow SKILL.md "Delivery" for a set named `rate-limiter-b` while `rate-limiter-py` (same title) is in
     the app.
  - **Expected:** the message says: drag it into http://127.0.0.1:8765; the app confirms "Imported Rate limiter
    (rate-limiter-b)" and shows `rate-limiter-b` under the title; press Start only if the name matches; if it says "Not
    imported", paste the message back.
  - **Got today:** "drag it into http://127.0.0.1:8765, read the ready screen, press Start". Nothing to check, so the
    candidate can start either copy.
- **Files:** `skill/interview-practice/SKILL.md` ("Delivery", plus one line under "Gate"/pack: "If pack.py prints NOT
  PACKED, fix the named field and pack again"), `README.md` (the drop line at the top).
- **Interface changes:** none. The synced copy under `~/.claude/skills/synced/` is refreshed by the owner after merge.
- **Data changes:** none.
- **UI conventions:** n/a; neutral placeholders only (Acme), no company or role named.
- **Tests:** none automated. `grep -n "Imported\|Not imported\|NOT PACKED" skill/interview-practice/SKILL.md README.md`
  shows the new lines; SKILL.md grows by 5 lines at most.
- **Acceptance:**
  1. The words quoted in SKILL.md and README match the toast text on the test stack exactly.
  2. Following "Delivery" with two same-title sets in the app, a reader can tell which one to start.
