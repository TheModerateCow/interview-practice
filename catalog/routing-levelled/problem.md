# Delivery routing

You're building the in-memory routing core of a delivery company. The city's road network is a set of **junctions** joined by **roads**; every road can be driven **both ways** and takes a whole number of minutes. The network later grows road closures, fastest routes, and an electric van that has to watch its battery. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Network}}` type: later levels add methods to it.

**Timestamps.** Every method takes `{{ts}}` (an integer) as its first argument: the time of the call. Timestamps strictly increase from one call to the next. No level depends on them, but keep them in the signatures.

**Ids.** Junctions and roads have separate ids (a road may be called `"hub"` like a junction). Ids are case-sensitive. Every `{{minutes}}` passed in is at least 1.

## Level 1: junctions and roads

| Method | Behaviour |
|---|---|
| `{{add_junction}}(ts, id) → bool` | Adds a junction. Returns `false`, changing nothing, if a junction with this id exists. |
| `{{add_road}}(ts, road, a, b, minutes) → bool` | Adds a two-way road `road` between junctions `a` and `b` that takes `minutes` to drive. Returns `false`, changing nothing, if a road with this id exists, either junction doesn't exist, or `a` and `b` are the same junction. Several roads may join the same two junctions. |
| `{{roads_at}}(ts, junction) → list of string` | Every road touching the junction, as `"road:other:minutes"` where `other` is the junction at its far end, sorted by road id in plain string order (by code unit, so `"R5"` comes before `"r1"`, and `"r10"` before `"r2"`). An empty list for a junction with no roads, or one that doesn't exist. |
| `{{reachable}}({{ts}}, {{origin}}, {{dest}}) → bool` | Whether a van can drive from `{{origin}}` to `{{dest}}` along roads. A junction reaches itself. `false` if either junction doesn't exist. |

A call that fails uses up no id: the road id can be added later.

### Example

```
{{add_junction}}(1, "depot")                  → true
{{add_junction}}(2, "a")                      → true
{{add_junction}}(3, "b")                      → true
{{add_junction}}(4, "c")                      → true
{{add_junction}}(5, "depot")                  → false
{{add_road}}(6, "r1", "depot", "a", 10)       → true
{{add_road}}(7, "r2", "a", "b", 5)            → true
{{add_road}}(8, "r1", "b", "c", 3)            → false   (r1 exists)
{{add_road}}(9, "r3", "depot", "zz", 4)       → false   (no junction zz)
{{add_road}}(10, "r4", "b", "b", 2)           → false
{{roads_at}}(11, "a")                         → ["r1:depot:10", "r2:b:5"]
{{reachable}}(12, "depot", "b")               → true
{{reachable}}(13, "depot", "c")               → false
{{reachable}}(14, "c", "c")                   → true
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
