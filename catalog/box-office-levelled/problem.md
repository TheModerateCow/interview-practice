# Box office

You're building the in-memory box office for a concert promoter. It sells seats for events, lets buyers get refunds, and later grows checkout holds and a history view. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Office}}` type: later levels add methods to it.

**Timestamps.** Every method takes `ts` as its first argument: the time of the call. Timestamps only ever increase from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

## Level 1: events, buying and refunds

| Method | Behaviour |
|---|---|
| `{{create_event}}(ts, event_id, capacity) → bool` | Adds an event with `capacity` seats. Returns `false` if `event_id` already exists or `capacity <= 0`. |
| `{{buy}}(ts, event_id, buyer, qty) → bool` | Gives `buyer` `qty` tickets. Returns `false`, changing nothing, if the event doesn't exist, `qty <= 0`, or fewer than `qty` seats are available. |
| `{{refund}}(ts, event_id, buyer, qty) → bool` | Returns `qty` of `buyer`'s tickets to the event, so those seats can be bought again. Returns `false`, changing nothing, if the event doesn't exist, `qty <= 0`, or `buyer` owns fewer than `qty` tickets for that event. |
| `{{available}}(ts, event_id) → int` | Seats that can still be bought, or `-1` if the event doesn't exist. |

A buyer's tickets belong to one event: tickets for `"a"` can't be refunded against `"b"`.

### Example

```
{{create_event}}(1, "jazz-night", 10)  → true
{{buy}}(2, "jazz-night", "maya", 4)   → true
{{available}}(3, "jazz-night")        → 6
{{refund}}(4, "jazz-night", "maya", 5) → false   (maya owns 4)
{{buy}}(5, "jazz-night", "leo", 7)    → false   (only 6 left)
```

## Checking your work

- **Run** runs `{{run_entry}}`, a small program that reads commands from stdin (`create`, `buy`, `refund`, `available`; see the top of the file). Extend it as you go.
- **My tests** runs your own test files. The starter includes an example test to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
