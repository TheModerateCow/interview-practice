# Parking garage

You're building the in-memory system that runs a multi-storey parking garage. It tracks spots of three sizes and the vehicles that park in them, and later grows occupancy queries, reservations and a billing history. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in package `parking`, in `garage.go`. Keep building on the same `Garage` type: later levels add methods to it.

**Timestamps.** Every method takes `ts int` as its first argument: the time of the call, in minutes. Timestamps only ever increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

**Sizes.** Spots and vehicles are `"small"`, `"medium"` or `"large"`; any other string is invalid. A vehicle fits a spot of its own size or larger.

## Level 1: spots, parking and leaving

| Method | Behaviour |
|---|---|
| `AddSpot(ts int, spotID, size string) bool` | Adds a free spot. Returns `false` if `spotID` already exists or `size` is invalid. |
| `Park(ts int, plate, size string) string` | Parks a vehicle of `size` and returns the id of the spot it got: the free spot of the **smallest size that fits**, and among those the **lowest spot id** (plain string order, so `"m10"` comes before `"m2"`). Returns `""`, changing nothing, if `size` is invalid, `plate` is already parked, or no free spot fits. |
| `Leave(ts int, plate string) bool` | The vehicle drives out and its spot is free again. Returns `false` if `plate` isn't parked. |
| `SpotOf(ts int, plate string) string` | The spot `plate` is parked in, or `""` if it isn't parked. |

A plate that has left can park again later, in whatever spot `Park` picks then.

### Example

```
AddSpot(1, "A1", "small")    -> true
AddSpot(2, "B1", "medium")   -> true
AddSpot(3, "B2", "medium")   -> true
Park(4, "KX-101", "small")   -> "A1"
Park(5, "VN-220", "small")   -> "B1"   (no small spot left; B1 < B2)
Park(6, "TR-900", "large")   -> ""     (nothing fits)
Leave(7, "KX-101")           -> true
SpotOf(8, "KX-101")          -> ""
```

## Checking your work

- **Run** runs `cmd/run/main.go`, a small program that reads commands from stdin (`add`, `park`, `leave`, `spot`; see the top of the file). Extend it as you go.
- **My tests** runs your own `*_test.go` files. `garage_example_test.go` is an example to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
