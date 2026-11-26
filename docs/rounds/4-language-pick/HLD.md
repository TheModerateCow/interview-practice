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

**One PR.** The change is about 20 lines of UI, 6 lines of CSS and one e2e test. Splitting it would leave Home with
neither the pills nor the switch, or with both.

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
