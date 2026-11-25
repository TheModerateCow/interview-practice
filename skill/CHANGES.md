# interview-practice: changes for Interview Lab

- Frontmatter description: added "coding rounds are delivered through the Interview Lab app".
- Rule 1: time comes from clock.py (talking rounds) or the app (coding rounds); results from grade.py/gate.py or the app's Submit; "how long is left" = ask the user to read the app or compute from session.json; never guess.
- Rule 5: hint logging in app rounds goes to `$W/hints.log` with the app's minute.
- Session engine: "three helpers" -> four; pack.py embedded verbatim after gate.py with usage and authoring layout (hidden tests at set root, parts in `levels/`, `.hidden/<file>` manifest paths). Note that clock.py isn't started in coding rounds.
- Languages: new paragraph on writing for the runner images (Python 3+pytest, Go stdlib + `go 1.22`, Java 21 no JUnit, Node 24 node:test with type-stripping limits; avoid newer features). Local-toolchain gate and session-start toolchain check unchanged.
- "Where the candidate works" and "Grading a submission" replaced by a new section "Coding rounds in Interview Lab": delivery (pack, send zip, drag to http://127.0.0.1:8765, read ready screen, press Start), clock, in-round results, full manifest field table, Codebase/Levelled/DSA-TDD patterns, one complete example manifest, and the export.zip debrief flow.
- Codebase: phase 3 reveal line now says the app does it via `reveal` (Next part = "asked to move on"); "start the clock" -> user presses Start.
- Levelled: next-level reveal is done by the app via `reveal`; dropped the `status` call at each reveal.
- DSA: time is stated from the app's clock.
- Debrief step 1: "where the time went" uses session.json events and the hints log.
- Unchanged: grade.py and gate.py (byte-identical), standing rules 2-4 and 6-11, round types, difficulty table, company brief.
- Tip for review: the "Never guess" ending of rule 1 is new wording; the TDD/AI-assisted sections were not touched.
- Languages: pinned runner image versions listed; Levelled Go/Java authoring rule (helpers use only the L1 API, imports used outside level tests) so the app can compile one level at a time.
- When Claude runs on your machine (Claude Code): gate in the app's runner images (`docker compose run … backend python3 gate.py /set`) and save the zip to `~/Downloads/<name>.zip`.
- Debrief: for Go/Java Levelled rounds that stopped early, re-grade each level against a copy of the hidden tests with other levels' test functions removed (otherwise the skill's unchanged grade.py can't compile them).
- Languages: the per-tag compile rule now covers Codebase as well as Levelled sets (imports used outside phase tests, e.g. `var _ = time.Second`), and Go hidden-test helpers are prefixed `hidden` so they can't clash with the candidate's own test files.
