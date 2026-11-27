# Home battery fleet

You're building the in-memory core of a smart-meter platform that runs customers' home **batteries**. Each day the energy supplier publishes a half-hourly **tariff**, and every battery charges from or discharges to the grid at those prices. The platform later grows daily settlement reports, a planner that works out the best schedule a battery could have run, and warranty limits. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Fleet}}` type: later levels add methods to it.

**Time.** There's no clock: every action names the `{{day}}` (an integer) and the `{{slot}}` within that day's tariff (`0` is the first half-hour). Day `d + 1` comes straight after day `d`.

**Money** is whole pence. A tariff price is pence per kWh, the same for buying from and selling to the grid, and can be **negative** when there's surplus wind (then charging earns money). Energy moves in whole kWh.

**Results.** Where a method returns a number, it returns *none* when the call fails (the signatures below show how your language expresses that).

## Level 1: batteries, tariffs and actions

| Method | Behaviour |
|---|---|
| `{{add_battery}}(id, capacity, wear) → bool` | Registers an empty battery (0 kWh stored, cash 0) that holds at most `{{capacity}}` kWh (at least 1). `{{wear}}` (0 or more) is the cost in pence of cycling 1 kWh out of it. Returns `false`, changing nothing, if the id is already registered. Ids are case-sensitive. |
| `{{publish_tariff}}(day, prices) → bool` | Publishes the day's tariff: `{{prices}}[i]` is the price for slot `i` (at least 1 slot, at most 50). Returns `false`, changing nothing, if that day already has a tariff: a published tariff is final. |
| `{{charge}}(id, day, slot) → stored or none` | The battery takes in 1 kWh during that slot and pays the slot's price out of its cash. Returns the kWh stored afterwards. |
| `{{discharge}}(id, day, slot) → stored or none` | The battery sends out 1 kWh during that slot and earns the slot's price **minus its `{{wear}}`**. Returns the kWh stored afterwards. |
| `{{stored}}(id) → kWh or none` | Energy the battery holds now; *none* for an unknown id. |
| `{{cash}}(id) → pence or none` | Everything the battery has earned minus everything it has paid (it can be negative); *none* for an unknown id. |

**When an action is refused.** `{{charge}}` and `{{discharge}}` return *none*, changing nothing, if:

- the battery isn't registered, the day has no tariff, or the slot isn't in that day's tariff;
- the battery is full (`{{charge}}`) or empty (`{{discharge}}`);
- the battery already has an action at the same or a **later** day and slot. A battery does one thing per slot, and its actions are recorded in time order: day first, then slot. A refused action doesn't count as the battery's latest.

Energy stays in the battery from one day to the next.

### Example

```
{{add_battery}}("home-1", 2, 3)               → true
{{publish_tariff}}(1, [12, 9, 25, 14])        → true
{{charge}}("home-1", 1, 0)                    → 1        (pays 12)
{{charge}}("home-1", 1, 1)                    → 2        (pays 9)
{{charge}}("home-1", 1, 2)                    → none     (full)
{{discharge}}("home-1", 1, 2)                 → 1        (earns 25 - 3)
{{stored}}("home-1")                          → 1
{{cash}}("home-1")                            → 1
{{discharge}}("home-1", 1, 1)                 → none     (slot 1 is before its last action)
{{stored}}("home-9")                          → none
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
