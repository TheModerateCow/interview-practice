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

Write only `catalog/<p>/T/`, `answers/<p>/T/`, and the `"T"` budget keys. Don't change cases, api.json, the statement or
other languages; if a case looks wrong or untranslatable, report it. Don't run git.

## Report (short)
Problem, T; files written; T budgets set; gate output; anything unsure.
