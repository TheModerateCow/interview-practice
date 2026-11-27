# Parking garage

You're building the in-memory system that runs a multi-storey parking garage. It tracks spots of three sizes and the vehicles that park in them, and later grows occupancy queries, reservations and a billing history. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Garage}}` type: later levels add methods to it.

**Timestamps.** Every method takes `ts` (an integer) as its first argument: the time of the call, in minutes. Timestamps only ever increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

**Sizes.** Spots and vehicles are `"small"`, `"medium"` or `"large"`; any other string is invalid. A vehicle fits a spot of its own size or larger.

## Level 1: spots, parking and leaving

| Method | Behaviour |
|---|---|
| `{{add_spot}}(ts, spot_id, size)` | Adds a free spot. Returns `false` if `spot_id` already exists or `size` is invalid. |
| `{{park}}(ts, plate, size)` | Parks a vehicle of `size` and returns the id of the spot it got: the free spot of the **smallest size that fits**, and among those the **lowest spot id** (plain string order, so `"m10"` comes before `"m2"`). Returns `""`, changing nothing, if `size` is invalid, `plate` is already parked, or no free spot fits. |
| `{{leave}}(ts, plate)` | The vehicle drives out and its spot is free again. Returns `false` if `plate` isn't parked. |
| `{{spot_of}}(ts, plate)` | The spot `plate` is parked in, or `""` if it isn't parked. |

A plate that has left can park again later, in whatever spot `{{park}}` picks then.

### Example

```
{{add_spot}}(1, "A1", "small")    -> true
{{add_spot}}(2, "B1", "medium")   -> true
{{add_spot}}(3, "B2", "medium")   -> true
{{park}}(4, "KX-101", "small")   -> "A1"
{{park}}(5, "VN-220", "small")   -> "B1"   (no small spot left; B1 < B2)
{{park}}(6, "TR-900", "large")   -> ""     (nothing fits)
{{leave}}(7, "KX-101")           -> true
{{spot_of}}(8, "KX-101")          -> ""
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
