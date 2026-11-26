# Round 4 HLD: Pick the language once

Spec: `SPEC.md` in this folder. Code references are to `main` at 1a42f81.

## Today's flow and where it goes wrong

```
Home ─► Catalog.svelte
  head:  "Problems · 9 of 30"   [Round ▾] [All languages ▾] [Difficulty ▾]        f.language is a filter …
  row:   <div .set-item>
           <button .set-row aria-label="<title> in <langFor(p)>">  title / meta / "not tried"
           <div .langs> <button .lang-chip>Go</button> Java Python                no hover, no pressed state
  langFor(p) = first of [f.language, usual, p.last_language] that p has, else p.languages[0]
                                                                                   … and also what a row opens
  pick(p, lang): usual = lang; LS 'ilab.lang' = lang                               every pick moves the default
                 POST /api/catalog/<id>/attempt {language} ─► onpick(name) ─► ready screen (no clock until Start)
```

Nothing on screen shows `langFor(p)`. The only place it appears is the row's `aria-label`, which also hides the row's
difficulty, minutes and history from screen readers.

## Design

One change, all in the catalog. The Language filter becomes a "Practise in" switch built from the existing `.seg`
(the header's theme switch). The pills go. Each row names its language in its second line.

### UI: `ui/src/features/catalog/Catalog.svelte`

```js
let lang = $state(LS.get('ilab.lang') || 'python');   // "Practise in": only the switch changes it
let f = $state(Object.assign({ round: '', difficulty: '' }, JSON.parse(LS.get('ilab.filters') || '{}')));
const langs = $derived([...new Set(problems.flatMap(p => p.languages))].sort());
const chosen = $derived(langs.includes(lang) ? lang : langs[0]);
const choose = l => { lang = l; LS.set('ilab.lang', l); };

// filters: round and difficulty only (drop the language test from `shown`, and the language branch from `opts`)
const langFor = p => [chosen, p.last_language].find(l => l && p.languages.includes(l)) || p.languages[0];
const langWords = p => { const l = langFor(p), n = LANGNAME[l] || l; return p.languages.length === 1 && l !== chosen ? n + ' only' : n; };
const meta = p => [ROUND[p.round] || p.round, langWords(p), cap(p.difficulty), p.minutes + ' min'].join(' · ');

async function pick(p) {            // no longer writes ilab.lang
  const lang = langFor(p); …same POST and onpick as today…
}
```

```svelte
<div class="filters">
  {#if langs.length}
    <span class="lang-pick"><span id="lang-pick-label" class="label">Practise in</span>
      <span id="lang-pick" class="seg" role="group" aria-labelledby="lang-pick-label">
        {#each langs as l}<button type="button" data-lang={l} aria-pressed={String(l === chosen)} onclick={() => choose(l)}>{LANGNAME[l] || l}</button>{/each}
      </span></span>
  {/if}
  <Dropdown id="f-round" …/>  <Dropdown id="f-difficulty" …/>     <!-- #f-language goes -->
</div>
{#each shown as p (p.id)}
  <button type="button" class="set-row" data-problem={p.id} disabled={!!picking} onclick={() => pick(p)}>
    …title, meta(p), history as today…                                <!-- no aria-label: the visible text is the name -->
  </button>
{/each}
```

The `.set-item` wrapper and the `.langs` group go: the row is the only control. `.set-row` already has its own bottom
hairline, hover (`surface`) and focus ring. The comment at the top of the file is updated to match.

### Styles: `ui/src/styles/style.css` (and the same `.seg` lines in `design/system/project/components/bundle.css`)

```css
.filters { …; align-items: center; }
.lang-pick { display: inline-flex; align-items: center; gap: var(--s-2); }   /* the label never wraps away from its switch */
.seg button:not([aria-pressed="true"]):hover { background: var(--surface-2); color: var(--fg); }
.seg button:focus-visible { outline-offset: -2px; }   /* .seg clips anything drawn outside a button */
```

Delete `.langs`, `.lang-chip`, `.lang-chip:focus-visible`, `.lang-chip:disabled`. Keep `.set-item:hover` (Home's
In progress / Not started / Finished rows still use it for their Delete button); its comment becomes "the whole row,
Delete included". No new tokens.

Contrast (worked out from `tokens.css`, light / dark): "Practise in" `fg-3` on `bg` 4.9:1 / 5.3:1; a button that
isn't chosen, `fg-2` on `bg` 8.2:1 / 8.6:1; on hover, `fg` on `surface-2` 14.5:1 / 13.8:1; the chosen one, `bg` on
`fg` 18.2:1 / 16.3:1. The row's second line is `fg-2`, unchanged.

### Data and interface changes

| Thing | Change |
|---|---|
| API, backend, `data/` | None |
| Browser key `ilab.lang` | Was "the language last picked", written by every pick. Now "Practise in", written only by the switch. Same key, so a returning user keeps their language |
| Browser key `ilab.filters` | No longer read for `language`. An old stored value is ignored |
| Element ids | New: `#lang-pick` (group), `#lang-pick [data-lang]`, `#lang-pick-label`. Removed: `#f-language`, `.lang-chip`, `.langs` (no test uses them). Kept: `#catalog`, `#f-round`, `#f-round-list`, `#f-difficulty`, `[data-problem]`, `.set-row`, `.set-meta`, `.set-name`, `#ready`, `#ready-name`, `#home-btn` |

UI rules: tokens only; borders, not shadows; no accent on Home (the chosen language is filled with `fg`, like the theme
switch; Submit stays the app's only `btn-accent`); 4.5:1 text; check 1440×900 and 400 px, light and dark, no
sideways scroll.

## PR plan

**PR 1** is the language switch. The change is about 20 lines of UI, 6 lines of CSS and one e2e test. Splitting it
would leave Home with neither the pills nor the switch, or with both.
**PR 2** (added by the owner, 2026-11-27) is the Settings page with word wrap. It is built in parallel with PR 1 and
merged after it (see PR 2 for the shared files).

Verify on the isolated test stack (`tests/stack.sh up`, http://127.0.0.1:8766), never on the owner's app at 8765.
The UI is built into the stack's image, so `tests/stack.sh up` picks up the branch.

---

### PR 1: Choose the language once, see it on every row
- **Example** (owner finding O1; screenshot `.iteration/work/round-4/shots/OWNER-01-language-chips.png`, Home with the
  Round filter on Levelled round, dark theme):
  1. On Home, set Round to "Levelled round".
  2. Look at the first row, "Bank ledger: rankings, scheduled payments and merges". Which language will a click open?
  3. Move the pointer over "Java", then choose Java.
  4. Click the Bank ledger row.
  - **Expected:** above the list, "Practise in" with Go, Java and Python as one switch, and one of them filled in.
    Every row's second line names that language: "Levelled round · Python · Hard · 90 min". Hovering "Java" shades
    it. Clicking it fills Java, and every row now says Java. The Bank ledger row opens the ready screen with a "Java"
    pill and the name `banking-levelled-java-1` (or the next free number). The clock has not started.
  - **Got today** (screenshot): each row ends in "not tried  Go  Java  Python", three outlined pills that look like
    tags. Nothing shows which language the row opens. Hovering "Java" changes only the row's background, as hovering
    anywhere on the row does. Choosing Java means clicking that pill, which opens the ready screen at once. A click on
    the row instead opens whichever language was picked last, and nothing on screen says which.
- **Files:** `ui/src/features/catalog/Catalog.svelte`, `ui/src/styles/style.css`,
  `design/system/project/components/bundle.css` (the three `.seg` lines → the same as `style.css`),
  `tests/e2e.sh`, `tests/e2e.spec.mjs`.
- **Interface changes:** none in the API. Browser key `ilab.lang` is written only by the switch (see the table above).
- **Data changes:** none.
- **Tests:**
  - `tests/e2e.sh`: add one pair, `"$E2E_NAME-lang:"`, to the zip loop, and pass `E2E_NAME_LANG` and
    `E2E_ZIP_LANG` to the container. It is the Python sample set under its own name, so it joins the catalog as a
    one-language problem.
  - New e2e test "Catalog: the language you choose is the one that opens":
    1. Find a levelled problem with Java in `GET /api/catalog` (the DSA test picks `dsa[0]`, so the two never share an
       attempt). Go to Home.
    2. `#lang-pick [aria-pressed="true"]` has count 1; `#catalog .lang-chip` has count 0.
    3. Click `#lang-pick [data-lang="java"]`: it has `aria-pressed="true"`, the others `"false"`. The problem's
       `[data-problem] .set-meta` contains "Java".
    4. Click the row: `#ready .pill` contains "Java"; `#ready-name` matches `^<id>-java-\d+$`; `#round` is hidden (no
       clock yet).
    5. Import `E2E_ZIP_LANG` through `POST /api/import`. Back on Home (`#home-btn`), its row's `.set-meta` contains
       "Python only". Click it: `#ready .pill` contains "Python". Back on Home, Java is still pressed.
    6. Reload: Java is still pressed.
    7. Keyboard: focus `#lang-pick [data-lang="go"]`, press Enter: Go is pressed.
    8. Resize to 400×800: `document.documentElement.scrollWidth <= innerWidth`; the problem's row is at least 360 px
       wide; `#lang-pick` fits on one line (its height is under 40 px).
  - Existing "Catalog: filter, then pick a problem" test passes unchanged (it uses `#f-round`, `[data-problem]` and
    `.set-meta` starting "DSA round", all kept).
  - `tests/api_test.py`: no change (no backend change). `npm run build` in `ui/` succeeds.
- **Acceptance** (on the test stack, by using the app):
  1. The example above gives the expected result, in light and in dark.
  2. Hover each language button that isn't chosen: it shades. The chosen one stays filled. The header's Auto / Light
     / Dark switch shades the same way.
  3. Tab from the top of Home: the three language buttons, then Round and Difficulty, then one stop per row. Each
     language button, and each header theme button, shows a full focus ring, including the filled one in dark.
  4. With a screen reader (or the browser's accessibility tree): a group "Practise in" with three toggle buttons and
     their pressed state; each row reads its title, round, language, difficulty, minutes and history.
  5. Choose Java and reload: Java is still chosen. Choosing never starts a clock or adds anything under "Not
     started".
  6. Drop `tests/sets/_zips/rate-limiter-py.zip` with Java chosen: its row says "Python only" and opens in Python.
     Back on Home, Java is still chosen.
  7. At 400 px, light and dark: no sideways scroll; "Practise in" and its three buttons sit on one line; the Bank
     ledger title wraps to at most two lines (before: three or four, captured as the before shot).
  8. `tests/run_all.sh` ends with every step PASS.
- **Not in this PR:** the ready screen, filtering by language (owner's open question), and `docs/PRODUCT.md` §4a. The
  Home step there still means "pick a problem, land on its ready screen", so the user-flow diagrams don't change.

---

## Design addition (owner, 2026-11-27): Settings and word wrap

Spec: `SPEC.md`, "Addition", R4–R6. Code references are to `main` at 4903d76.

### Today

```
App.svelte header:  brand · [All sets] · [set picker ▾] · spacer · parts · clock · <ThemeToggle/> (Auto|Light|Dark)
screen(v):          app.view = v; if v !== 'round' → stopTimers()      (the clock poll, the tick and the 00:00 auto-close)
ThemeToggle:        theme = LS 'ilab-theme'; $effect sets <html data-theme>; onMount listens to the system theme
loadMonaco():       monaco.editor.create(el, { …, no wordWrap })      → Monaco's default, off; one editor per page
```

### Settings panel: `ui/src/features/settings/Settings.svelte` (new)

Always in the page and hidden while closed, like `#delete-confirm`. This keeps `ThemeToggle` mounted, so the saved
theme still applies on load.

```svelte
<script>
  import ThemeToggle from '../../components/ThemeToggle.svelte';
  import { LS } from '../../lib/util.js';
  import { setWrap } from '../../lib/monaco.js';
  import { app } from '../../app.svelte.js';
  import { round } from '../round/round.svelte.js';
  let wrap = $state(LS.get('ilab-wrap') === 'on'), panel = $state();
  const close = () => { app.settings = false; document.getElementById('settings-btn')?.focus(); };
  $effect(() => { if (round.finalOpen) app.settings = false; });            // 00:00 while open: the end card wins
  $effect(() => { if (app.settings) panel?.querySelector('button')?.focus(); });
</script>
<svelte:window onkeydown={e => { if (e.key === 'Escape' && app.settings) close(); }} />
<div id="settings" class="overlay settings" class:hidden={!app.settings} role="dialog" aria-labelledby="settings-title">
  <div class="final-card" bind:this={panel}>
    <h2 id="settings-title">Settings</h2>
    <div class="setting"><div><span id="wrap-label">Word wrap</span>
        <p>Long lines wrap at the editor's edge instead of scrolling sideways. Your code doesn't change.</p></div>
      <div id="wrap-pick" class="seg" role="group" aria-labelledby="wrap-label">
        {#each [[false, 'Off'], [true, 'On']] as [v, label]}
          <button type="button" data-wrap={v ? 'on' : 'off'} aria-pressed={String(wrap === v)} onclick={() => { wrap = v; setWrap(v); }}>{label}</button>
        {/each}</div></div>
    <div class="setting"><div><span>Theme</span></div><ThemeToggle /></div>
    <p class="muted">The language problems open in is set on Home, above the problem list ("Practise in").</p>
    <div class="actions"><button id="settings-close" class="btn btn-outline" type="button" onclick={close}>Done</button></div>
  </div>
</div>
```

`ThemeToggle.svelte` is not edited: its group is already labelled "Theme" (`aria-label`). #38 changes only its insides.

### Header and app state: `ui/src/App.svelte`, `ui/src/app.svelte.js`

```svelte
<header id="top" class:above={app.settings}>
  … brand · All sets · picker · spacer · <Clock/> …
  <button id="settings-btn" class="btn btn-ghost" type="button" aria-expanded={app.settings}
    aria-controls="settings" onclick={() => (app.settings = !app.settings)}>Settings</button>   <!-- replaces <ThemeToggle /> -->
</header>
… <Round /> <Settings />
```

- `screen(v)` starts with `app.settings = false`. Every navigation goes through it ("All sets", the picker, Start, a
  pick on Home), so choosing one closes Settings. Opening and closing Settings never calls `screen()`, so the clock's
  timers keep running.
- `app.svelte.js`: `app` gains `settings: false`.

### Word wrap: `ui/src/lib/monaco.js`

```js
import { LS } from './util.js';
const wrapOpt = () => (LS.get('ilab-wrap') === 'on' ? 'on' : 'off');
// in loadMonaco(): monaco.editor.create(el, { …, wordWrap: wrapOpt() })
export function setWrap(on) { LS.set('ilab-wrap', on ? 'on' : 'off'); monacoP?.then(ed => ed.updateOptions({ wordWrap: wrapOpt() })); }
```

Monaco's `wordWrap: 'on'` wraps at the viewport and hides the horizontal scrollbar. It changes the view only: the
model text, autosave, Run, My tests and Submit are untouched. When the editor isn't loaded yet (Home, Ready),
`setWrap()` only saves the choice, and the editor reads it when it is created.

### Styles: `ui/src/styles/style.css`, a new "settings" block (no edits to existing rules)

```css
#top.above { position: relative; z-index: 31; }   /* over the Settings overlay (30): the clock stays in sight */
.settings .final-card { max-width: 560px; }
.setting { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--s-2) var(--s-4);
  padding-top: var(--s-4); border-top: 1px solid var(--line); }
.setting p { margin: var(--s-1) 0 0; max-width: 40ch; color: var(--fg-3); font-size: var(--t-small); }
```

Reused as they are: `.overlay`, `.final-card` (and its `h2` and `.actions`), `.seg`, `.btn-ghost`, `.btn-outline`,
`.muted`. No new tokens and no accent: Settings has no `btn-accent`, and on the round screen Submit stays the only
one. Hint text is `fg-3` on `bg`: 4.9:1 light, 5.3:1 dark.

### Data and interface changes (PR 2)

| Thing | Change |
|---|---|
| API, backend, `data/` | None |
| Browser key `ilab-wrap` | New: `"on"` or `"off"` (missing means off) |
| Browser key `ilab-theme` | Unchanged |
| Element ids | New: `#settings-btn`, `#settings`, `#settings-title`, `#settings-close`, `#wrap-pick [data-wrap]`. The theme buttons (`[data-t]`) move from `#top` into `#settings`; no test uses them. Kept: `#top`, `#home-btn`, `#set-picker`, `#set-picker-list`, `#timer`, `#round`, `#editor`, `#file-tree`, `#final`, `#drop-confirm-open` |

---

### PR 2 (added by the owner, 2026-11-27; parallel with PR 1, merge after it): Settings, with word wrap
- **Example** (`catalog/fares-tdd/java/starter/Fares.java` line 9 is a 169-character comment):
  1. On Home, choose Transit fares: peaks, transfers and caps (TDD) in Java. Press Start.
  2. In Files, open `Fares.java`. Look at line 9, the comment above `journeyFare(...)`.
  3. Look for a way to make long lines wrap.
  4. Open Settings, set Word wrap to On, close Settings.
  - **Expected:** step 3: a "Settings" button at the right end of the header. Step 4: Settings opens over the round,
    and the clock in the header keeps counting. With Word wrap On, line 9 wraps onto two lines inside the editor and
    ends `"adult", "child" or "senior". */`, with no sideways scrollbar. "Done" returns to the same file, and the clock
    has kept running. After a reload, wrap is still on.
  - **Got today:** step 2: line 9 runs past the editor's right edge at 1440 px. About the last 60 characters (the
    list of concessions) are out of sight; the candidate scrolls sideways or moves the cursor to read them. Step 3:
    there is no word wrap option and no Settings; the header holds only the theme switch.
- **Files:** `ui/src/features/settings/Settings.svelte` (new), `ui/src/App.svelte` (header, `screen()`, render
  `<Settings />`), `ui/src/app.svelte.js` (`settings`), `ui/src/lib/monaco.js` (`wordWrap`, `setWrap`),
  `ui/src/styles/style.css` (new "settings" block), `design/system/project/README.md` (the Layout paragraph: the
  header ends in "Settings", not the theme switch), `tests/e2e.spec.mjs`.
- **Interface changes:** none in the API. New browser key `ilab-wrap`.
- **Data changes:** none.
- **Shared files and order:**
  - PR 1 also edits `style.css` (the `.seg` and catalog rules; PR 2 only adds a new block at the end of the Home
    section) and `tests/e2e.spec.mjs` (each PR appends its own test). Rebase, don't merge blind.
  - PR 2 relies on PR 1's `.seg` hover and full focus ring for its two switches. Built before PR 1 lands, they work
    but don't shade. **Merge order: PR 1 → PR 2.**
  - #38 (motion, open) edits `ThemeToggle.svelte` (PR 2 doesn't), `style.css` (keyframes and toast; no overlap with
    the new block) and `design/system/project/README.md` ("States and motion"; PR 2 edits only "Layout"). Either can
    merge first. If #38 lands first, its crossfade must still run when the switch is inside Settings (acceptance 6).
  - Neither PR touches `bundle.css` for Settings: the new rules live in `style.css` only.
- **Tests:**
  - New e2e test "Settings: word wrap, mid-round, and the clock keeps running":
    1. Through the API: `POST /api/catalog/fares-tdd/attempt {"language": "java"}`, then `POST /api/sets/<name>/start`.
       Open it with the picker (`pickSet`), after `openIfAsked`. Wait for `#editor .monaco-editor`.
    2. Click `#file-tree div` with text `Fares.java`. The `.view-line` containing `"senior"` ends right of the
       `#editor` box (no wrap).
    3. Note `#timer`. Click `#settings-btn`: `#settings` is visible, `#settings-btn` has `aria-expanded="true"`,
       `#timer` is still visible.
    4. Click `#wrap-pick [data-wrap="on"]`: it has `aria-pressed="true"`. The text `"senior"` is now inside the
       `#editor` box.
    5. Wait 2 s: `#timer` shows less time than in step 3.
    6. Press Escape: `#settings` is hidden, `#round` is visible, `#settings-btn` is focused, and `Fares.java` is
       still the selected file (`#file-tree div.sel`).
    7. Reload and reopen the round: `#wrap-pick [data-wrap="on"]` is still pressed, and `"senior"` is inside `#editor`.
    8. `#top [data-t]` has count 0 and `#settings [data-t]` count 3. Click `#settings [data-t="dark"]`:
       `<html data-theme="dark">`. Reload: still dark.
    9. Resize to 400×800 and open Settings: no sideways scroll (`scrollWidth <= innerWidth`); `#settings-close` is in
       view and `#settings-btn` is visible.
    10. With Settings open, click `#home-btn`: Home shows and `#settings` is hidden.
  - Every existing e2e test passes unchanged: none uses the theme switch, and every id they use is kept (table above).
  - `tests/api_test.py`: no change (no backend change). `npm run build` in `ui/` succeeds.
- **Acceptance** (on the test stack, by using the app):
  1. The example above gives the expected result, in light and in dark.
  2. Settings opens from Home, from a ready screen and mid-round. On the ready screen, opening and closing it starts
     no clock. Mid-round the clock keeps counting the whole time Settings is open.
  3. Done, Esc and the Settings button each close it, and focus lands back on "Settings".
  4. Drop a 1-minute copy of the sample set (made the way `tests/e2e.sh` makes its `-1m` zip), press Start, open
     Settings, and wait: at 00:00
     Settings closes and the end card shows the final grade.
  5. With wrap On: type a line longer than the editor and press Run, then Submit. Both behave as with wrap Off, and
     the exported `submission/Fares.java` has no added line breaks.
  6. Theme: Auto / Light / Dark from Settings changes the page and the editor at once, and the choice survives a
     reload. The header no longer has the switch.
  7. 1440 px: "Settings" at the right end of the header, after the clock. 400 px, light and dark: "Settings" is the
     header's last item; the panel fits with no sideways scroll; each switch wraps under its name.
  8. Keyboard only: Tab reaches Word wrap, Theme and Done. A screen reader announces the dialog "Settings" and each
     switch's pressed state.
  9. `tests/run_all.sh` ends with every step PASS.
- **Not in this PR:** other editor options (font size, tab width, minimap); a keyboard shortcut for Settings;
  mirroring "Practise in". `docs/PRODUCT.md` §4a doesn't change: Settings is outside the practice loop it draws.
