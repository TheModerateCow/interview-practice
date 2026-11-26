Interview Lab is a local, timed coding-interview simulator. Everything on screen serves one person under time pressure: read the problem, write code, run it, submit, watch the clock. Build every screen so the clock, the code and the result are the only things that compete for attention.

## Content fundamentals

- Write from the candidate's side of the screen, in plain sentences, second person where needed ("The clock starts when you press Start."). No "we", no exclamation marks, no emoji.
- Sentence case everywhere: buttons, labels, headings. Uppercase only through the `label` style, which adds the caps itself; never type text in capitals.
- A control says exactly what happens: **Start interview**, **Run**, **My tests**, **Submit**, **Next part**, **End interview**, **Export**. The confirmation that follows uses the same verb ("End interview" / "Keep going").
- Results are facts, never praise or scores: `4/5`, "did not finish in 45 s", the last failing line. Never "Great job" or a percentage presented as a grade.
- During the round never show hidden test names or test code. Names appear only after End or time up.
- Errors say what went wrong and what to do: "The go runner image is missing. Run deploy/install.sh." No apologies.
- Verdicts use the judge's words exactly: Accepted, Wrong Answer, Compile Error, Runtime Error, Time Limit Exceeded, Memory Limit Exceeded.

## Color

- Neutrals carry the layout. `bg` is the page and the editor; `surface` holds panels (file tree, results, stdin); `surface-2` marks hover and the selected row. Separate panes with `line` hairlines, never shadows.
- Text: `fg` for primary text, `fg-2` for body copy in the problem pane, `fg-3` for captions, labels, placeholders and line numbers. All three read on `bg` and `surface` in both themes.
- `accent` (blue) appears **once per screen**: the Submit button. Text on it is `on-accent`, the page background cut out of the blue (grey in light, black in dark). Do not use the accent for links, chips, icons or decoration.
- `timer-low-bg` (yellow) appears only as the clock's last-5-minutes highlight; `warn` covers Time Limit Exceeded, Memory Limit Exceeded and "did not finish". `fail` covers every other failing verdict, End and time up. `pass` covers Accepted and full meters. A status color always comes with a word or a ✓/✗, never alone.
- Solid neutral buttons (Start interview, Export at the end) and toasts use `inverse-bg` with `inverse-fg`.
- The `brand-*` tokens are the source palette (#080708, #3772ff, #df2935, #fdca40, #e6e8e6). Build with the role tokens, not the brand tokens; small red text uses `fail`, which is darker than `brand-red` in light so it passes 4.5:1.
- Both themes are first-class. Light: grey page, black ink. Dark: `brand-black` ground, grey ink. Theme follows the system unless the person picks Light or Dark in the header.

## Type

- Two families: Inter Tight (`--font-sans`) for interface and headlines, Geist Mono (`--font-mono`) for code, the clock, file names, test tags and every number that lines up. Both are self-hosted from `fonts/`: the app runs offline and its CSP allows fonts only from its own origin.
- Headlines are weight 400 with negative tracking (`display`, `h1`, `h2`, `h3`). Size makes hierarchy; bold never does. Use 500 for buttons and badges, 600 only for the wordmark.
- `display` is for the set title on the ready screen and the drop zone headline, nowhere else. `small` (13px) is the working size of the round screen: buttons, tables, the problem body.
- Numbers use tabular figures (`font-variant-numeric: tabular-nums`) so counts and the clock don't jitter.

## Layout

- Three screens. **Home**: the dashed drop zone, the only way to import a set, above the sets grouped In progress / Not started / Finished; the app opens here unless a round is in progress. **Ready**: eyebrow (company · role · round), the title in `display`, pills for language, difficulty and minutes, the rules, then **Start interview**; the problem is never shown here. **Round**: header (wordmark, set picker, part chips, clock, **Settings** button; the theme switch and word wrap live in the Settings panel), toolbar, then three panes: files (`surface`), editor over stdin and results, problem (`bg`).
- Spacing is a 4px grid: `s-1` … `s-8`. Toolbar gaps `s-2`, panel padding `s-3`–`s-5`, page sections `s-7`–`s-8`.
- Radii are small: `r-md` (6px) for controls, `r-sm` for badges and rows, `r-xl` only for the drop zone and the ready and end cards; pills and part chips are `r-pill`.
- Borders, not shadows. The one translucent layer is the end-of-round overlay.

## States and motion

- Hover: buttons and rows move to `surface-2`; Submit moves to `accent-hover`. Disabled: 45% opacity, `not-allowed` cursor, while a run is in progress.
- Focus: a 2px solid `focus` ring with 2px offset on every interactive element.
- Destructive or irreversible actions confirm inline, in the page, never with a browser dialog: End shows a `fail`-tinted bar with **End interview** and **Keep going**; Next part shows a neutral bar.
- Loading: a wait longer than 300 ms shows a small turning ring with words for what is happening ("Running hidden tests…"), in the one place the answer will appear. The ring is the only continuous motion; with `prefers-reduced-motion` it stands still.

## Motion

Motion explains a change in place. It never decorates, and it never makes the candidate wait. Every animation uses `ease`, the only easing curve, with one of two durations: `dur` (160ms) or `dur-slow` (280ms).

- Color: hover, pressed and selected states change color over `dur`. The dropdown chevron turns over `dur`.
- Entering: a layer that appears fades in (`fade`) or fades in and rises 4px (`rise`). Use `rise` for things that sit in the flow or come up from below: confirm bars, the toast and the end card. Use `fade` for things that drop down or cover the page: the dropdown list and the overlay behind the end card. Small layers take `dur`; the end overlay and its card take `dur-slow`.
- Leaving: things disappear at once. Nothing animates out, so closing never delays the next action.
- Progress: a grade meter's fill grows to its new width over `dur-slow` when a count changes.
- Theme: switching between Light and Dark in the header crossfades the whole page, editor included, over `dur-slow`. The switch runs inside a view transition (`document.startViewTransition`). Browsers without view transitions switch at once, and so does a system theme change while the switch is on Auto.
- Never: the clock, the code in the editor, pane sizes while dragging a splitter, or a layout change. Nothing bounces, overshoots, scales, slides in from off screen or loops (the loading ring is the one exception).
- `prefers-reduced-motion` turns off every transition, animation and the theme crossfade. Changes then happen at once and the words carry the meaning.

## Iconography

- There is no icon set and no logo. The wordmark is "Interview Lab" set in Inter Tight 600.
- Meaning comes from words plus two glyphs: ✓ and ✗ in test tables and part chips. The dropdown's chevron is drawn with a border, not a glyph. Keyboard shortcuts appear as `kbd` hints inside the button: `Ctrl '` for Run, `Ctrl ↵` for Submit.

## Components

Buttons (accent · outline · ghost · danger · solid), confirm bars, the clock, verdict badges, part chips, pills, grade rows, the testcase table, the event log, the drop zone, the ready card, the code editor theme, the toast, the loading ring and the dropdown (used instead of the browser's `select`). Each has a guideline and a live preview under Components. All are plain HTML with the classes in `components/bundle.css`; there is no script bundle.
