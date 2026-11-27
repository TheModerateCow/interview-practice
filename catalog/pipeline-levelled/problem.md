# Release pipeline

You're building the in-memory core of a monorepo's release pipeline. The pipeline is made of **jobs** identified by name (like `lint`), each taking a fixed number of minutes. A job's artifact is used by at most one downstream job, its **consumer**, so many jobs fan in towards a release. The pipeline later grows a run order and cycle checks, finish-time estimates, and choosing which build caches to pre-warm. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Pipeline}}` type: later levels add methods to it.

**Inputs.** If `a`'s consumer is `b`, then `a` is one of `b`'s **inputs**: `b` can only run once `a` has finished. A job with no consumer is the end of a pipeline. Links come from config files people edit by hand, so nothing stops them from going round in a loop.

**Names** are case-sensitive. Lists of names are sorted in plain string order (by code unit, so `"Zeta"` comes before `"alpha"`).

## Level 1: jobs, links and the run tracker

| Method | Behaviour |
|---|---|
| `{{add_job}}(job, minutes) → bool` | Adds an unfinished job that takes `{{minutes}}` minutes (0 or more). Returns `false`, changing nothing, if the name is taken. |
| `{{set_consumer}}(job, consumer) → bool` | `{{job}}`'s artifact now feeds `{{consumer}}`, replacing `{{job}}`'s previous consumer if it had one. A job may name itself. Returns `false`, changing nothing, if either job doesn't exist or `{{consumer}}` has already finished. |
| `{{inputs}}(job) → list of string` | The jobs whose consumer is `{{job}}`, sorted; empty for an unknown job. |
| `{{ready}}() → list of string` | Every unfinished job whose inputs have all finished (a job with no inputs is ready straight away), sorted. |
| `{{finish}}(job) → bool` | Marks a ready job finished. Returns `false`, changing nothing, if the job doesn't exist, has already finished, or isn't ready. |

### Example

```
{{add_job}}("lint", 3)                         → true
{{add_job}}("test", 10)                        → true
{{add_job}}("release", 5)                      → true
{{add_job}}("lint", 4)                         → false
{{set_consumer}}("lint", "release")            → true
{{set_consumer}}("test", "release")            → true
{{set_consumer}}("test", "deploy")             → false    (no job "deploy")
{{inputs}}("release")                          → ["lint", "test"]
{{ready}}()                                    → ["lint", "test"]
{{finish}}("release")                          → false    (its inputs haven't finished)
{{finish}}("lint")                             → true
{{finish}}("test")                             → true
{{ready}}()                                    → ["release"]
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
