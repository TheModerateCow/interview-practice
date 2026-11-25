# Box office

You're building the in-memory box office for a concert promoter. It sells seats for events, lets buyers get refunds, and later grows checkout holds and a history view. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in package `tickets`, in `office.go`. Keep building on the same `Office` type: later levels add methods to it.

**Timestamps.** Every method takes `ts int` as its first argument: the time of the call. Timestamps only ever increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

## Level 1: events, buying and refunds

| Method | Behaviour |
|---|---|
| `CreateEvent(ts int, eventID string, capacity int) bool` | Adds an event with `capacity` seats. Returns `false` if `eventID` already exists or `capacity <= 0`. |
| `Buy(ts int, eventID, buyer string, qty int) bool` | Gives `buyer` `qty` tickets. Returns `false`, changing nothing, if the event doesn't exist, `qty <= 0`, or fewer than `qty` seats are available. |
| `Refund(ts int, eventID, buyer string, qty int) bool` | Returns `qty` of `buyer`'s tickets to the event, so those seats can be bought again. Returns `false`, changing nothing, if the event doesn't exist, `qty <= 0`, or `buyer` owns fewer than `qty` tickets for that event. |
| `Available(ts int, eventID string) int` | Seats that can still be bought, or `-1` if the event doesn't exist. |

A buyer's tickets belong to one event: tickets for `"a"` can't be refunded against `"b"`.

### Example

```
CreateEvent(1, "jazz-night", 10)  -> true
Buy(2, "jazz-night", "maya", 4)   -> true
Available(3, "jazz-night")        -> 6
Refund(4, "jazz-night", "maya", 5) -> false   (maya owns 4)
Buy(5, "jazz-night", "leo", 7)    -> false   (only 6 left)
```

## Checking your work

- **Run** runs `cmd/run/main.go`, a small program that reads commands from stdin (`create`, `buy`, `refund`, `available`; see the top of the file). Extend it as you go.
- **My tests** runs your own `*_test.go` files. `office_example_test.go` is an example to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
