# Shared cases: the contract

Everything the renderer (`backend/lab/variants.py`) and the three language backends (`backend/lab/langs/{go,java,python}.py`)
agree on. HLD: `HLD.md`.

## Problem folder

```
catalog/<problem>/
  problem.json    {"title", "company", "round", "difficulty", "minutes", "rules"?, "tags", "reveal"?, "grade_timeout_s"?,
                   "your_tests"?, "testcases"?, "run_entry"?}      # interview-set/1 manifest fields minus name/language/hidden_tests
  problem.md      statement; {{name}} placeholders (below); levels/*.md likewise (reveal "file" stays ".hidden/<x>.md")
  api.json        shared-case rounds only
  cases/<t>.json  shared-case rounds only; <t> = the tag without "test_" and the trailing "_" ("test_l1_" → l1.json)
  cases/data/*    big inputs referenced by cases
  <lang>/         lang ∈ go, java, python; present = that language exists
    starter/      the candidate's files (stubs, run_entry, example test)
    hidden/       Codebase (no api.json): the hidden tests file, named as today (hidden_test.go, HiddenTest.java, tests_hidden.py)
    manifest.json optional per-language overrides of problem.json (e.g. "run_entry", "testcases", "your_tests")
answers/<problem>/<lang>/   reference/, mutants.json, bugs.json   (gate input; mutant/bug "file" paths are relative to reference/)
```

`render(problem_dir, lang) -> {relpath: bytes}` is a normal interview-set/1 set: `manifest.json` (problem.json + per-language
overrides + `name`, `language`, `hidden_tests: ".hidden/<file>"`), `problem.md` + `.hidden/<level>.md` with placeholders
rendered, `starter/**`, and `.hidden/<tests file>` (generated from api.json + cases, or copied from `<lang>/hidden/`).
`your_tests` default per language: go `*_test.go`, java `*Test.java`, python `test_*.py`.

## Names

api.json and cases use neutral names: functions, methods, parameters, record fields and error kinds in `snake_case`;
classes and records in `PascalCase`; `module` in lowercase letters.

| neutral | Go | Java | Python |
|---|---|---|---|
| function / method `create_event` | `CreateEvent` | `createEvent` | `create_event` |
| record field `event_id` | `EventID` | `eventId` | `event_id` |
| class / record `Office` | `Office`, constructor `NewOffice(...)` | `new Office(...)` | `Office(...)` |
| error kind `insufficient_funds` | `var ErrInsufficientFunds error` | `class InsufficientFundsException extends RuntimeException` | `class InsufficientFundsError(Exception)` |
| module `tickets` | `package tickets`, go.mod `module tickets` | free functions are static methods of `Tickets` (`api.java_class` overrides) | `tickets.py` |

Go initialisms upper-cased whole: `id`, `url`, `ttl`, `api`, `http`, `json`, `ip`, `uuid`, `sku`. Java camelCase keeps them
as words (`skuId`).

Placeholders in markdown: `{{create_event}}` → the language's name for that function/method/field/error kind;
`{{Office}}` → the class as written (Go: still `Office`); `{{new Office}}` → `NewOffice` / `new Office` / `Office`.
A parameter name (`{{spot_id}}`) → Go `spotID`, Java `spotId`, Python `spot_id`. `{{run_entry}}` and `{{your_tests}}` → that language's manifest values (`cmd/run/main.go`, `*_test.go`, …).
The renderer also appends a `## Your code` section: the language's signatures for everything in api.json (emitter's
`signatures()`), so statements never hard-code a language.

## api.json

```json
{
  "module": "tickets",
  "java_class": "Tickets",
  "records": {"Road": [["a", "int"], ["b", "int"], ["minutes", "int"]]},
  "functions": {"fastest_delivery": {"params": [["n", "int"], ["roads", "list<Road>"]], "returns": "int"}},
  "classes": {"Office": {"init": [], "methods": {
    "create_event": {"params": [["ts", "int"], ["event_id", "string"], ["capacity", "int"]], "returns": "bool", "level": 1},
    "redeem": {"params": [["points", "long"]], "returns": null, "errors": true, "level": 3}}}},
  "errors": ["insufficient_points"]
}
```

Types and their mapping:

| api type | Go | Java | Python | JSON |
|---|---|---|---|---|
| `int` (fits 32 bits) | `int` | `int` | `int` | number |
| `long` | `int` | `long` | `int` | number |
| `bool` | `bool` | `boolean` | `bool` | true/false |
| `string` | `string` | `String` | `str` | string |
| `list<T>` | `[]T` | `T[]` when T is int/long/bool or a list of them (`int[][]`), else `List<T>` | `list[T]` | array |
| record `R` | `struct R` (exported fields) | `record R(...)` | `@dataclass class R` | object with neutral field names |
| `optional<T>` (returns only) | `(T, bool)` | boxed `T`, `null` = absent | `T \| None` | value or null |
| `"returns": null` | no result | `void` | `None` | — |

`"errors": true` on a function/method: Go adds an `error` result (`(T, error)` or `error`); Java/Python throw. `optional`
and `errors` can't be combined. `level` (Levelled only) says which level adds the method; starters stub level 1 only.
`"init_errors": true` on a class: its constructor can fail. Go: `NewX(...) (*X, error)` (stub panics "not implemented");
Java: the constructor throws (unchecked); Python: `__init__` raises. Error kinds work as for methods. Without it, Go's
constructor is `NewX(...) *X`.
Free functions have no `level`: they are all in the starter from the start (Go needs them at compile time).

Any shared file (`problem.md`, `levels/<f>`) can be overridden per language by the same path under `<lang>/` — Codebase
rounds use this for their code-specific statement.

## Cases

```json
[{"name": "refund_all_left", "steps": [
    {"new": "Office", "args": []},
    {"call": "create_event", "args": [1, "gig", 10], "expect": true},
    {"call": "refund", "args": [3, "gig", "ana", 6], "error": "insufficient_points"}]},
 {"name": "single_junction", "call": "fastest_delivery", "args": [1, []], "expect": 0},
 {"name": "large", "call": "fastest_delivery", "data": "data/large.json",
  "budget_ms": {"go": 2000, "java": 3000, "python": 20000}}]
```

- A case is either one call (`call`, `args`, …) or `steps` run in order against one object made by the first `new` step.
  A `call` naming a function in api.json calls the free function; otherwise the method on the current object.
- `expect`: the JSON form of the result, compared exactly (records as objects with neutral field names; Go `nil` slice =
  `[]`; optional absent = `null`). Missing `expect` = not checked. `error`: an error kind name, or `true` for any error;
  the call must fail and its result is not checked.
- A `new` step may carry `error` (same forms) when the class has `init_errors`: construction must fail. A failed `new`
  leaves no object, so a case whose `new` is expected to fail must end there (it has no later steps). A stub's
  not-implemented error never counts as an expected error.
- `data`: a file under `cases/` holding `{"args": [...]}` (and `expect` if not given inline).
- `budget_ms`: per-language wall-time limit for that call (or the whole `steps` case), measured by the harness.
  Set from each language's reference time × 10, at least 500.
- Test names: `<tag><name>` → Go `Test_l1_refund_all_left`, Java and Python `test_l1_refund_all_left`. Names are
  `[a-z0-9_]+` and unique per problem.
- Failure message (becomes grade.py's `last_error`): `step 3 refund(3, "gig", "ana", 6): expected error insufficient_points, got 7`
  — the call with its arguments (arguments longer than 200 chars elided), what was expected, what came back.

## Generated hidden tests file (one file: the grader adds only this file to the candidate's code)

- Contains: the harness (generic, all identifiers prefixed `hidden`/`Hidden`/`_hidden`), the api.json and all cases
  (data files included) embedded as JSON text, and one test function per case that calls `hiddenRun("<name>")`.
- Go: `package <module>`; `func Test_<tag-rest><name>(t *testing.T) { hiddenRun(t, "<name>") }` on one line, so
  `grade.prune` keeps working; registries for what reflection can't find by name: `hiddenFuncs` (free functions),
  `hiddenNew` (constructors), `hiddenErrs` (error vars). Methods are found with `reflect.Value.MethodByName`, so a
  missing later-level method fails only its own tests. JSON text as Go string literals (strconv-quoted).
- Java: `public class HiddenTest` with `static void test_<...>() { hiddenRun("<name>"); }`; reflection for classes,
  constructors, methods and records; JSON text as string chunks of ≤ 30 000 chars joined at class init (class-file
  constant limit); a small JSON parser inside (no JSON in the JDK). Failures throw `AssertionError(message)`.
- Python: `tests_hidden.py` imports the module with `importlib`, `def test_<...>(): _hidden_run("<name>")`; dataclasses
  built with keyword arguments; failures raise `AssertionError(message)`.
- Mutants and `gate.py` are unchanged: the gate runs on the rendered set with the reference as `reference/`.

## Language backend interface (`backend/lab/langs/<lang>.py`)

```python
TESTS_FILE = "hidden_test.go"            # / "HiddenTest.java" / "tests_hidden.py"
def name(kind, neutral) -> str            # kind: "func", "method", "field", "class", "new", "error", "module"
def signatures(api) -> str                # markdown code block for "## Your code"
def tests_file(api, cases_by_tag, data) -> str   # the generated hidden tests file
def scaffold(api, example=None) -> {relpath: str}       # starter: stubs that fail loudly (records, error types, all free
                                                         # functions, level-1 methods), build files (go.mod), and if `example`
                                                         # (a case) is given an idiomatic example test with literal arguments
```

## Fixture

`tests/fixture/` is a problem in this format covering every feature (records, lists of lists, long, optional, errors
with kinds and `true`, void, a class with levels, free functions, a data file, a budget). Each language backend ships
with its reference in `tests/fixture/answers/<lang>/reference/` and must gate there in the runner images.
