# Round 3 HLD: one problem, every language

Owner's decisions (2026-11-26): a problem is language-neutral with Go, Java and Python variants; all 30 problems get
all three; DSA, Levelled and TDD tests are written once as shared JSON cases; restructure before the catalog PR opens.

## Today

```
catalog/<id>/          one interview-set/1 set = one problem in ONE language (id ends in -go / -py / -java)
answers/<id>/          its source: reference/, mutants.json, bugs.json, hidden tests written in that language
attempt                POST /api/catalog/<id>/attempt → copy catalog/<id> → data/sets/<id>-<k>/
grading                grade.py runs the variant's hidden tests file (pytest / go test / Java mini-runner)
```

Porting a problem = rewriting its statement, starter, reference, mutants and every test by hand in another language.

## Target

```
catalog/<problem>/                         # one folder per problem, no language in the id
  problem.json     title, round, difficulty, minutes, company, tags, reveal, rules
  problem.md       statement; code names written as {{create_event}} and rendered per language
  levels/*.md      later parts (Levelled / Codebase p3), same placeholders
  api.json         DSA/Levelled/TDD: the functions/classes, parameter and return types, records, error kinds
  cases/*.json     DSA/Levelled/TDD: the hidden tests, written once (big inputs in cases/data/*.json)
  go/ java/ python/
    starter/       per language (stubs, run_entry, example test)
    hidden/        Codebase only: that language's hidden tests (its bugs are language-specific)
answers/<problem>/{go,java,python}/  reference/, mutants.json, bugs.json (Codebase)
data/sets/<problem>-<lang>-<k>/      an attempt: an ordinary interview-set/1 set, rendered when the attempt starts
```

**Rendering** (`backend/lab/variants.py`, also used by the tools): `render(problem, lang) → interview-set/1 set` with
`manifest.json` (from problem.json + language), `problem.md` with names in the language's style (`create_event` →
Go `CreateEvent`, Java `createEvent`, Python `create_event`), `starter/`, and `.hidden/` = the generated tests file +
the language's harness + the cases. The attempt is that rendered set, so the clock, Run, Submit, reveal, export, `final/`
and `grade.py` don't change. A dropped Claude zip is still one interview-set/1 set: a problem with one variant.

## Shared cases

```json
// cases/l1.json (Levelled: a script against one object)
[{"name": "refund_all_left", "steps": [
   {"new": "Office"},
   {"call": "create_event", "args": [1, "gig", 10], "expect": true},
   {"call": "buy",          "args": [2, "gig", "ana", 5], "expect": true},
   {"call": "refund",       "args": [3, "gig", "ana", 6], "expect": false}]}]
// cases/p1.json (DSA: one call)
[{"name": "single_junction", "call": "fastest_delivery", "args": [1, 0, 0, [0], []], "expect": 0},
 {"name": "large", "call": "fastest_delivery", "data": "data/large.json", "expect": 14023,
  "budget_ms": {"go": 2000, "java": 3000, "python": 20000}}]
// an error case (TDD): {"call": "redeem", "args": [5, 900], "error": "insufficient_points"}
```

`api.json` declares the types the harness converts JSON to: `int` (64-bit), `bool`, `string`, `list<T>`, `optional<T>`,
and records (`{"Road": {"a": "int", "b": "int", "minutes": "int", "energy": "int"}}` → Go struct, Java record, Python
dataclass). Error kinds map per language: `insufficient_points` → Go `ErrInsufficientPoints` (checked with
`errors.Is`), Java `InsufficientPointsException`, Python `InsufficientPointsError`.

**Harness** (one generic file per language, in `.hidden/`, never shown): reads a case, builds the arguments from the
declared types, calls by name through reflection (Go `reflect`, Java reflection, Python `getattr`), compares the
JSON-normalised result, measures `budget_ms`. Java has no JSON in its standard library, so its harness carries a small
parser. The generated tests file has **one test per case** (`Test_l1_refund_all_left`, `test_l1_refund_all_left`), so
tags, per-test results, failed names and the debrief keep working. Calls go through reflection, so a missing later-level
method fails that test at run time instead of breaking the compile: the per-tag compile rule from round 2 goes away for
these rounds.

**Expected values** come from one canonical reference (`tools/cases.py fill`); the gate then checks every language's
reference against them, so the three variants provably agree.

## Gate and tools

- `tools/gate_problem.py answers/<problem>`: for each language, render the set + that language's reference and
  mutants into a temp folder and run today's `gate.py` (unchanged) on it in the runner images. Prints GATE PASS per language.
- `tools/cases.py fill <problem>`: run the canonical reference over `cases/*.json` and write the `expect` values.
- `tools/pack.py` keeps packing interview-set/1 zips (for Claude-made sets); `render` can also emit one.

## App

- `GET /api/catalog`: one row per problem with `languages: ["go", "java", "python"]` and per-language attempt counts.
- `POST /api/catalog/<problem>/attempt` with `{"language": "go"}`; attempts are `<problem>-<lang>-<k>`, manifest
  carries `problem` and `language`. Older attempts and dropped sets keep working.
- Home: each row shows language chips; clicking a chip starts that language. The language filter becomes "has a
  version in"; the last language used is remembered and pre-selected.
- Skill: Claude-made sets are unchanged (interview-set/1); the debrief reads `answers/<problem>/<lang>/`.

## Content

| Rounds | Problems | Work per problem |
|---|---|---|
| DSA, Levelled, TDD | 24 | convert its tests to `cases/` + `api.json` (once), port starter, reference and mutants to the 2 other languages |
| Codebase | 6 | port the whole codebase twice: its planted bugs, slow path and hidden tests are rewritten idiomatically per language |

About 72 language ports in total, each by a sub-agent, each gated in the runner images. Large token cost.

## PRs

1. **This branch (catalog PR):** the layout, rendering, harnesses in 3 languages, tools, API and Home changes; every
   existing problem moved to `catalog/<problem>/<lang>/` as one variant (Codebase ones keep `hidden/`; DSA/Levelled/TDD
   ones converted to shared cases); two problems carried to all three languages as the proof (one DSA, one Levelled);
   full `run_all.sh`. The job queue (Java Codebase) joins as its single variant.
2. **Ports, DSA/Levelled/TDD:** the remaining 22 problems to all three languages.
3. **Ports, Codebase:** 6 problems × 2 languages.

## Risks

- Reflection harnesses are the new core: a bug there mis-grades every round. They get their own unit tests per
  language, run in the runner images, plus every problem's gate.
- Timing budgets differ by language (CPython is ~10–30× slower): budgets are per language, set from each reference's
  measured time × 10, minimum 0.5 s.
- Records and error kinds are the awkward parts of a neutral API; problems that need more (maps, generics, callbacks)
  stay per-language tests like Codebase.
