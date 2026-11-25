# Porting a shared-case problem to another language

For a problem already in the shared-case format: `catalog/<p>/` (problem.json, problem.md, levels/, api.json, cases/,
`<S>/starter/`) and `answers/<p>/<S>/` for its existing language S. You add language `T` (go, java or python).
Read `CONTRACT.md` (names, types, how each language's harness calls your code). Example with all three languages:
`tests/fixture/` and `tests/fixture/answers/`.

## Steps

1. **Starter**: generate the stubs with the backend's scaffold, then add the run program and example test:
   ```
   python3 -c "import sys,json; sys.path.insert(0,'backend'); from lab.langs import T as b; \
     api=json.load(open('catalog/<p>/api.json')); [print(k) or open('catalog/<p>/T/starter/'+k,'w').write(v) \
     for k,v in b.scaffold(api).items()]"        # (create catalog/<p>/T/starter/ first; keep subfolders)
   ```
   - Port S's run_entry program (stdin driver) to T idiomatically, same input format and output, and put T's run
     entry, the same `testcases` (stdin/expected are language-independent) and `your_tests` in `catalog/<p>/T/manifest.json`
     (copy S's manifest.json and change `run_entry`; go `cmd/run/main.go`, java `Main.java`, python `main.py`).
   - Port S's example test to T's test style (`scaffold(api, example=<a case>)` can draft it; it must not repeat a
     hidden case).
2. **Reference**: port `answers/<p>/S/reference/` to idiomatic T in `answers/<p>/T/reference/`, matching the generated
   signatures exactly (same algorithm and complexity; Go: `go.mod` with `go 1.22`; Java: default package, Java 21; Python:
   3.10 syntax, stdlib only).
3. **Mutants**: port `answers/<p>/S/mutants.json` to T (same intent and `k`, edits against your T reference; each must
   change behaviour and be caught).
4. **Budgets**: for every case with `budget_ms`, add T's budget: run the gate with `--keep`, time T's reference on that
   case, budget = max(10 × reference time, 500) ms, rounded up. Edit only the `"T"` key in `cases/*.json`.
5. **Gate**: `python3 tools/gate_problem.py catalog/<p> answers/<p> --lang T` must print `T: GATE PASS` (runner images;
   one docker command at a time). Then the whole problem: `python3 tools/gate_problem.py catalog/<p> answers/<p>` (every
   language passes the same cases).

Write only `catalog/<p>/T/`, `answers/<p>/T/`, and the `"T"` budget keys. When one agent ports to both missing languages, do T1 fully (gate it), then T2. If the problem's statement or `rules` still names a language, make it neutral (placeholders / "Standard library only."). Don't change cases, api.json, the statement or
other languages; if a case looks wrong or untranslatable, report it. Don't run git.

## Report (short)
Problem, T; files written; T budgets set; gate output; anything unsure.

## Codebase problems (no api.json)

A Codebase problem's hidden tests, planted bugs, slow path and statement are language-specific, so a port is a rewrite
of the whole round in T that keeps the same story: same system and modules, same ticket (symptoms), same three bug
*causes* expressed idiomatically in T (adapt a bug that can't exist in T — e.g. Go slice aliasing → a shared mutable
list in Python/Java — and keep it in a different file from its symptom), same phase-2 feature and spec, same phase-3
bottleneck and fix, same test names and tags (`test_p1_…`; Go `Test_p1_…`).

1. Read `catalog/<p>/S/` (problem.md, levels/p3.md, hidden/, manifest.json, starter/) and `answers/<p>/S/` (reference/,
   bugs.json, mutants.json).
2. Write `answers/<p>/T/reference/` (idiomatic T; includes T's run program and example test, as in S's reference),
   `answers/<p>/T/bugs.json` and `mutants.json` (paths relative to reference/).
3. Write `catalog/<p>/T/hidden/<tests file>` (go `hidden_test.go`, java `HiddenTest.java`, python `tests_hidden.py`),
   same cases and expected values; Go/Java: the app compiles one tag's tests at a time, so helpers use only phase-1 code
   and every import is used outside the phase tests (`var ( _ = time.Second )`); every non-test helper prefixed `hidden`.
   Phase-3 scale tests keep S's shape: budget ≥ 10× T's reference and ≥ 0.5 s, slow version ≥ 5× over and the whole
   grade under ~20 s.
4. Write `catalog/<p>/T/problem.md` and `catalog/<p>/T/levels/p3.md` (S's texts with T's file and identifier names) and
   `catalog/<p>/T/manifest.json` (`run_entry`, `testcases` — same stdin/expected as S where the program is the same —
   `your_tests`).
5. `mkdir -p catalog/<p>/T/starter`, then build the starter from reference + bugs.json:
   `python3 tools/gate_problem.py catalog/<p> answers/<p> --lang T --build-starter`.
6. Gate: `python3 tools/gate_problem.py catalog/<p> answers/<p> --lang T` → `T: GATE PASS` (bugs caught alone and
   isolated per phase, mutants killed).

Write only `catalog/<p>/T/` and `answers/<p>/T/`. Don't run git.
