# Search box autocomplete

You're building the autocomplete behind a shop's site search box. Every search a visitor runs goes into the **query log**; the box suggests completions from it as people type. The service later grows log clean-up (deleting and merging queries), bulk imports with top-k suggestion lists, and finally a measure of how many keystrokes the autocomplete saves. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{SearchBox}}` type: later levels add methods to it.

**Queries** are 1 to 30 lowercase letters `a`-`z`. A **prefix** is 0 to 30 lowercase letters; the empty prefix `""` is the empty search box.

## Level 1: logging and suggestions

| Method | Behaviour |
|---|---|
| `{{log_query}}({{query}}) → int` | Records one search for `{{query}}`. Returns its new **popularity**: how many times it has been logged. |
| `{{popularity}}({{query}}) → int` | How many times `{{query}}` has been logged; `0` if never. A query's prefixes don't count as the query (`"lam"` is not `"lamp"`). |
| `{{suggest}}({{prefix}}) → query or none` | The **suggestion** for that box text: the most popular logged query that starts with `{{prefix}}`. The prefix itself counts if it was logged. Ties go to the alphabetically first query (plain string order). The empty prefix matches every query. *None* if no logged query starts with `{{prefix}}`. |

### Example

```
{{log_query}}("shoes")                        → 1
{{log_query}}("shirts")                       → 1
{{log_query}}("shoes")                        → 2
{{log_query}}("shirt")                        → 1
{{popularity}}("shoes")                       → 2
{{popularity}}("sandals")                     → 0
{{suggest}}("sh")                             → "shoes"
{{suggest}}("shi")                            → "shirt"    (tied with "shirts"; "shirt" sorts first)
{{suggest}}("")                               → "shoes"
{{suggest}}("shirts")                         → "shirts"
{{suggest}}("x")                              → none
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
