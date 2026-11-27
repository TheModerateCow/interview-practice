# Business-class desk

You're building the in-memory core of an airline's business-class desk for **one multi-stop flight**. The aircraft calls at stops `0, 1, …, n`; **leg** `k` is the hop from stop `k` to stop `k+1`. Some business seats are already sold elsewhere, so the number of seats the desk controls **differs per leg**. Passengers (identified by a string like `ana`) take a business seat from the stop where they board to the stop where they get off. The desk later grows an upgrade waitlist, busiest-leg reports and upgrade planning. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{Flight}}` type, created with `{{new Flight}}({{seats}})`: `{{seats}}[k]` (≥ 0) is the number of seats the desk has on leg `k`, and the flight has `n = len({{seats}})` legs (at least 1). Keep building on it: later levels add methods to it.

**Trips.** A trip from `{{board}}` to `{{alight}}` uses legs `{{board}}`, `{{board}}+1`, …, `{{alight}}-1`. It is valid when `0 <= {{board}} < {{alight}} <= n`. A passenger who gets off at stop `s` frees their seat for someone boarding at `s`.

## Level 1: bookings

| Method | Behaviour |
|---|---|
| `{{book}}({{passenger}}, {{board}}, {{alight}}) → bool` | Gives the passenger one seat on every leg of the trip. Returns `false`, changing nothing, if the trip isn't valid, the passenger already holds a seat, or **any** leg of the trip has no free seat (a passenger is never seated for only part of a trip). Passenger ids are case-sensitive. |
| `{{cancel}}({{passenger}}) → bool` | The passenger gives up their seat, freeing it on every leg of their trip. Returns `false` if they hold no seat. They may book again afterwards. |
| `{{free_seats}}({{leg}}) → count or none` | How many of the desk's seats on leg `{{leg}}` nobody holds; *none* if there's no such leg (`{{leg}} < 0` or `{{leg}} >= n`). |

### Example

```
{{new Flight}}([2, 1, 2])           (3 legs, stops 0..3)
{{book}}("ana", 0, 2)               → true
{{free_seats}}(1)                   → 0
{{book}}("ben", 1, 3)               → false   (leg 1 is full)
{{book}}("ben", 2, 3)               → true    (ana gets off at stop 2)
{{book}}("ana", 2, 3)               → false   (ana already holds a seat)
{{free_seats}}(2)                   → 1
{{cancel}}("ana")                   → true
{{book}}("cy", 1, 3)                → true
{{free_seats}}(0)                   → 2
{{free_seats}}(3)                   → none
{{book}}("dee", 2, 2)               → false   (not a trip)
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
