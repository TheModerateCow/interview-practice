# Gym classes

You're building the in-memory class booking desk for a gym. Members book spots in scheduled classes and cancel them; later the desk grows waitlists, class credits and weekly series. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Studio}}` type: later levels add methods to it.

**Time.** Every method takes `ts` as its first argument: the time of the call, in minutes. Timestamps only ever increase from one call to the next. A class's `start` is a minute on the same clock. A class **has started** once `ts >= start`.

## Level 1: classes, bookings and cancellations

| Method | Behaviour |
|---|---|
| `{{add_class}}(ts, {{class_id}}, start, capacity) → bool` | Schedules a class with `capacity` spots, starting at `start`. Returns `false` if `{{class_id}}` already exists, `capacity <= 0`, or `start <= ts`. |
| `{{book}}(ts, {{class_id}}, member) → bool` | Books one spot for `member`. Returns `false`, changing nothing, if the class doesn't exist, has started, is full, or `member` already has a spot in it. |
| `{{cancel}}(ts, {{class_id}}, member) → bool` | Gives up `member`'s spot, so someone else can book it (and `member` can book again). Returns `false` if the class doesn't exist, has started, or `member` has no spot in it. |
| `{{spots_left}}(ts, {{class_id}}) → int` | Spots not yet booked, or `-1` if the class doesn't exist. |
| `{{upcoming}}(ts, member) → list of strings` | The ids of the classes `member` has a spot in that haven't started yet: earliest `start` first, ties by class id ascending. An empty list if there are none. |

A member's spot belongs to one class: cancelling `"a"` doesn't touch a spot in `"b"`.

### Example

```
{{add_class}}(1, "spin-am", 480, 2)   → true
{{book}}(2, "spin-am", "maya")        → true
{{book}}(3, "spin-am", "maya")        → false   (already booked)
{{book}}(4, "spin-am", "leo")         → true
{{book}}(5, "spin-am", "sam")         → false   (full)
{{cancel}}(6, "spin-am", "leo")       → true
{{spots_left}}(7, "spin-am")          → 1
{{upcoming}}(8, "maya")               → ["spin-am"]
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
