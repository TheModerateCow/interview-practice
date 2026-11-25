# Converting a single-language problem to the shared-case format

For one problem `catalog/<old>/` (an interview-set/1 set, e.g. `kvstore-levelled-go`) with its answers in `answers/<old>/`.
Read `CONTRACT.md` first. Worked example of the target format: `tests/fixture/` (problem.json, problem.md, api.json,
cases/, `<lang>/starter/`, `answers/<lang>/`).

## Steps

1. **New id** = the old id without its language suffix (`kvstore-levelled-go` → `kvstore-levelled`). `L` = its language.
2. **api.json**: describe the public API (functions, classes and their methods with `level`, records, error kinds) in
   neutral names chosen so that `backend/lab/langs/<L>.py`'s `name()` reproduces the EXISTING names exactly (check with
   `python3 -c "import sys; sys.path.insert(0,'backend'); from lab.langs import go; print(go.name('method','event_id'))"`).
   Then the existing starter, reference and mutants keep working unchanged. If an existing name can't be produced
   (e.g. a Go method `GetAt` you'd need as `get_at` → fine; an odd abbreviation that can't round-trip), rename it in the
   reference, starter, mutants and statement consistently.
3. **cases/<t>.json**: one case per existing hidden test (same name minus the tag prefix), translated faithfully:
   same calls, arguments and expected values (they came from the reference). Use `steps` for stateful tests. Tests that
   build big inputs with a generator: run the generator once (in L, via the runner image or locally) and store the
   arguments in `cases/data/<name>.json`; keep it under ~2 MB. Timing assertions become `budget_ms` for L only (other
   languages get theirs when ported). Assertions that only make sense in L (e.g. "returns a non-nil slice", aliasing)
   are dropped or expressed through behaviour; list each one in your report.
4. **problem.json** = the old manifest minus `format`, `name`, `language`, `hidden_tests`, `run_entry`, `testcases`,
   `your_tests`. **`L/manifest.json`** = `{"run_entry", "testcases", "your_tests"}` from the old manifest (those present).
5. **problem.md** and **levels/*.md**: the old texts with code names replaced by placeholders (`{{create_event}}`,
   `{{new Office}}`, `{{insufficient_points}}`), and language-specific signature blocks / type syntax removed or made
   neutral (the renderer appends a "Your code" section with the signatures). Keep examples, written neutrally
   (`create_event(1, "gig", 10) → true`). Worked examples must stay correct.
6. **`L/starter/`** = the old `starter/` (unchanged unless step 2 renamed something). Keep its run_entry program and
   example test.
7. **answers/<new>/L/** = the old `answers/<old>/reference/` and `mutants.json` (paths relative to reference/).
8. **Gate**: `python3 tools/gate_problem.py catalog/<new> answers/<new>` must print `L: GATE PASS` (run it from the repo
   root; it uses the app's runner images; one docker command at a time). If a mutant survives because a dropped test
   was what caught it, add a case that catches it.
9. Remove `catalog/<old>/` and `answers/<old>/` (plain `rm -rf`; don't run git commands — the lead commits).

Write only inside `catalog/<new>/`, `answers/<new>/`, and the removal of the two old folders. Never touch other problems,
`backend/`, `tools/` or `tests/`; if the harness or renderer seems wrong, report it instead of working around it.

## Report (short)
Old → new id; number of cases per tag; anything dropped or renamed; gate output line; anything unsure.
