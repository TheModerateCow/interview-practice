# Round 4: Pick the language once

Finding addressed: owner finding O1 (2026-11-26, `.iteration/work/round-4/owner-findings.md`, screenshot
`shots/OWNER-01-language-chips.png`): "this way to selecting languages isnt really the best. its not responsive and
also not inituative. people will think its just a label and not an actual button."

## Problem

Every problem on Home comes in Go, Java and Python. The candidate has to know which one a click will open, and has to be
able to choose another. Today neither is visible:

- **The language buttons look like tags.** Each row ends in three outlined pills, "Go", "Java", "Python", next to a
  grey monospace "not tried" (screenshot). They are buttons, but nothing about them says so: no fill, no hover, no
  pressed state. #35 removed their hover and #36 removed the highlight on the usual language.
- **Nothing says what a row click opens.** A click on the row opens the problem in a language the app works out from
  four places (the Language filter, the language last picked, the language last used on that problem, the first one).
  None of them shows on screen. The Language filter reads "All languages" while the app quietly uses the last one picked.
- **Picking an imported problem changes the default without saying so.** Every pick saves its language as the new
  default. An imported Python-only set, picked once, makes every built-in problem open in Python from then on.
- **At 400 px the pills squeeze the title.** The three pills, "not tried" and the gaps take about 260 px of a 368 px
  row. The title gets about 110 px and wraps to three or four lines (worked out from `style.css`; the PR captures the
  before shot).
- **Keyboard users tab through 120 stops.** Each of the 30 rows is four tab stops: the row and three pills.

The step has no clock, so a wrong pick costs a trip back to Home, not a round. It does leave an unstarted copy in the
wrong language under "Not started".

## Why this design (and not the alternatives)

| | **A. One "Practise in" switch above the list** (pick) | B. A language switch and an Open button on every row | C. The row opens a detail step where the language is chosen |
|---|---|---|---|
| Shows what a click opens | Yes: the switch shows the chosen language filled in, and each row names it | Yes, per row | Only after the click |
| Choosing another language | One click on the switch; it stays chosen | One click per row, forgotten on reload | One click on the detail step |
| Controls on screen | 3 buttons in total; one tab stop per row (30) | 4 per row (120 tab stops), 30 Open buttons | 1 per row |
| 400 px | The row gets its full width back | Each row needs two lines of controls | Like A |
| New code | `.seg` (the theme switch) reused; ~20 lines | A per-row state and a new row layout | A new screen, or a language switch on the ready screen that makes a new unstarted copy each time it changes |
| Fits how people practise | You practise in one language at a time | Treats every problem as a fresh choice | Adds a step to every pick |

A wins: it shows the choice, it is one control instead of 90, and it reuses the switch the header already has. Its cost
is that trying one problem in another language takes two clicks (switch, then row) instead of one. B is noisy and
heavy at 400 px. C adds a step to every pick, and choosing on the ready screen mixes a problem's languages into a
screen that is about one set (the header picker also opens it).

A Dropdown ("Practise in: Python ▾") was also considered. It already exists and scales to many languages, but it hides
the options behind a click and reads as one more filter next to Round and Difficulty. With three languages, the
switch is clearer. If the catalog grows past about five languages, swap in the Dropdown.

## What is missing in the code today

All references are to `main` at 1a42f81.

| Gap | Where |
|---|---|
| The row's language is computed but never shown, except in the row's `aria-label` | `ui/src/features/catalog/Catalog.svelte` `langFor()` (line 24), row `aria-label` (line 54) |
| The pills have no hover, no pressed state, and look like the read-only `.pill` | `ui/src/styles/style.css` `.lang-chip` (lines 37–40); `.pill` in `tokens.css` |
| Every pick overwrites the default language | `Catalog.svelte` `pick()`: `usual = lang; LS.set('ilab.lang', lang)` (line 31) |
| The Language filter changes what a row opens, but shows "All languages" by default and hides almost nothing: all 30 built-in problems have Go, Java and Python | `Catalog.svelte` `#f-language` (line 47), `langFor()`; `catalog/*/{go,java,python}` |
| The header's segmented switch has no hover, and its focus ring is cut off | `style.css` `.seg` (lines 23–25): `overflow: hidden` on the group clips the 2 px ring that `tokens.css` draws 2 px outside each button |

## Definitions

- **Practise in**: the language the candidate has chosen. Every row opens in it unless the problem doesn't come in it.
- **One-language problem**: a problem that comes in one language only. Today these are the candidate's own imports
  (`source: "custom"`); every built-in has Go, Java and Python.

## Requirements

### R1. One visible language choice (UI)
1. The catalog head shows "Practise in" followed by a segmented switch with one button per language in the catalog,
   in alphabetical order (today: Go, Java, Python). Exactly one is filled in at all times.
2. It replaces the Language filter. Round and Difficulty stay.
3. The choice is remembered in the browser. On a first visit it is Python (decision 2). If the remembered language is
   no longer in the catalog, the first button is chosen.
4. Only the switch changes the choice. Picking a problem never changes it.
5. Choosing a language changes nothing else: it starts no clock and creates no attempt.

### R2. Each row says what it opens (UI)
1. Each row is a single button. The language pills are removed.
2. The row's second line names the language it opens: "Levelled round · Python · Hard · 90 min". This matches the
   order the "In progress" rows already use (round · language · …).
3. A one-language problem that lacks the chosen language says so: "Codebase round · Python only · Medium · 30 min".
   Its row opens in that language.
4. A click on the row opens the ready screen exactly as today (running attempt in that language, else unstarted, else a
   new one). Nothing about the problem's text, tests or parts shows before Start, and the clock starts only on Start.

### R3. The switch looks and works like a control (UI)
1. Hover on a button that isn't chosen gives it the `surface-2` background and `fg` text, as the design system's rule
   for buttons and rows says. The header's theme switch gets the same.
2. Keyboard: each button is one Tab stop; Enter or Space chooses. The focus ring shows in full on every button, in
   both segmented switches (catalog and header).
3. Screen readers hear a group named "Practise in" and toggle buttons with their pressed state. The row's spoken
   name is its visible text, so it includes the language, difficulty, minutes and history.
4. 1440 px and 400 px, light and dark: no sideways scroll. At 400 px the switch stays on one line and each row's title
   uses the row's full width minus the history column.

## Non-goals

- Changing the ready screen. It already shows the language as a pill.
- A per-problem language memory ("I always do Bank ledger in Java").
- Filtering the list by language (see the open question).
- Cleaning up unstarted copies left by earlier picks in the wrong language. "Delete" on Home covers it.
- Any backend or API change.
- Using the accent. Home has no accent today (Submit, on the round screen, is the only `btn-accent`) and keeps none:
  the chosen language is filled with `fg`, like the theme switch.

## Success measures

- A first-time user can say which language a row opens without clicking (a usage test, asked before the first click).
- Tab stops to walk the catalog: 120 → 30 for 30 problems.
- At 400 px no row's title wraps to more than two lines (it wraps to three or four today).
- No pick changes the chosen language (an e2e check).

## Decisions defaulted (owner can override)

1. The switch replaces the Language filter instead of sitting beside it. A filter that hides nothing for built-in
   problems, next to a choice of language, would be two controls for one idea.
2. First visit: Python. It is first in the app's own language list (`LANGNAME` in `ui/src/lib/util.js`) and in the
   skill's. A returning user keeps the language they last picked (the same browser key, `ilab.lang`).
3. Label "Practise in", so the switch reads as a sentence: "Practise in Python".
4. A one-language problem stays in the list and says "Python only", rather than being hidden.

## Open question for the owner

Should "Practise in Java" also hide your imported problems that are in another language? Today the built-in 30 have
all three, so this only affects your own imports. The plan keeps them listed with "Python only".
