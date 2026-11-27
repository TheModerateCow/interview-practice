# Corridor dispatch

You're building the in-memory dispatch core of a ride-sharing service that runs along one long highway corridor. **Drivers** on shift and **riders** waiting for a pickup each sit at a whole-kilometre marker on the corridor (from `0` to `1000000`), and the distance between two of them is the difference of their markers. Dispatch later grows trips, a dispatch radius, and capacity planning for operations. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Dispatcher}}` type: later levels add methods to it.

**Timestamps.** Every method takes `{{ts}}` (an integer) as its first argument: the time of the call. Timestamps strictly increase from one call to the next. No level depends on them, but keep them in the signatures.

**Ids.** Drivers and riders have separate ids (a rider and a driver may both be `"r1"`). Ids are case-sensitive.

## Level 1: drivers, riders and the nearest driver

| Method | Behaviour |
|---|---|
| `{{add_driver}}(ts, id, km) → bool` | A driver comes on shift, idle at marker `km`. Returns `false`, changing nothing, if a driver with this id is already on shift. |
| `{{add_rider}}(ts, id, km) → bool` | A rider starts waiting at marker `km`. Returns `false`, changing nothing, if a rider with this id is already waiting. |
| `{{move_driver}}(ts, id, km) → bool` | An idle driver is now at marker `km`. Returns `false` if no driver with this id is on shift. |
| `{{remove_driver}}(ts, id) → bool` | The driver goes off shift. Returns `false` if no driver with this id is on shift. |
| `{{cancel_rider}}(ts, id) → bool` | The rider stops waiting. Returns `false` if no rider with this id is waiting. |
| `{{nearest_driver}}(ts, rider) → driver id or none` | The idle driver closest to the waiting rider. When several are equally close, the one at the **lower** marker; at the same marker, the smaller id in plain string order (by code unit, so `"Zed"` comes before `"amy"`). *None* if the rider isn't waiting or no driver is idle. |

An id that went off shift (or stopped waiting) can be added again later, as new.

### Example

```
{{add_driver}}(1, "d1", 10)                   → true
{{add_driver}}(2, "d2", 30)                   → true
{{add_driver}}(3, "d1", 50)                   → false
{{add_rider}}(4, "r1", 18)                    → true
{{nearest_driver}}(5, "r1")                   → "d1"   (8 km away; d2 is 12)
{{move_driver}}(6, "d2", 24)                  → true
{{nearest_driver}}(7, "r1")                   → "d2"   (6 km)
{{remove_driver}}(8, "d2")                    → true
{{nearest_driver}}(9, "r1")                   → "d1"
{{nearest_driver}}(10, "r9")                  → none
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
