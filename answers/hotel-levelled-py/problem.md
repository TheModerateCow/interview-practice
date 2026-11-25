# Hotel front desk

You're building the in-memory front desk for a small hotel. It keeps rooms and their nightly rates, takes bookings for ranges of nights, and later grows availability searches, check-in and check-out, and rate history. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in `hotel.py`, in class `Hotel`. Keep building on the same class: later levels add methods to it. Python standard library only.

**Days.** Dates are integers. Every method takes `day` as its first argument: today, the day of the call. Days only ever increase from one call to the next. Level 1 doesn't use `day` yet, but keep it in the signatures.

**Nights.** A booking with `check_in = 10` and `check_out = 13` covers the nights of days 10, 11 and 12. The guest leaves on day 13, so another booking of the same room can start on day 13.

**Money** is in integer cents.

## Level 1: rooms and bookings

| Method | Behaviour |
|---|---|
| `add_room(day, room_id: str, room_type: str, rate: int) -> bool` | Adds a room of `room_type` (for example `"double"`) costing `rate` per night. Returns `False` if `room_id` already exists or `rate <= 0`. |
| `book(day, guest: str, room_id: str, check_in: int, check_out: int) -> str` | Books the room for the nights `check_in` to `check_out - 1` and returns the booking's id. Ids are `"b1"`, `"b2"`, `"b3"`, … in order, counted across the whole hotel; a failed call uses no id. Returns `""`, changing nothing, if the room doesn't exist, `check_in >= check_out`, or any of those nights is already booked in that room. |
| `cancel(day, booking_id: str) -> bool` | Cancels the booking, so its nights can be booked again. Returns `False` if the booking doesn't exist or is already cancelled. |
| `cost(day, booking_id: str) -> int` | The booking's price: number of nights times the room's nightly rate. `-1` if the booking doesn't exist or is cancelled. |

### Example

```
add_room(1, "101", "double", 12000)  -> True
book(2, "maya", "101", 10, 13)       -> "b1"
book(3, "leo", "101", 12, 14)        -> ""      (night 12 is maya's)
book(4, "leo", "101", 13, 15)        -> "b2"
cost(5, "b1")                        -> 36000   (3 nights)
cancel(6, "b1")                      -> True
book(7, "ana", "101", 11, 12)        -> "b3"
```

## Checking your work

- **Run** runs `main.py`, a small program that reads commands from stdin (`room`, `book`, `cancel`, `cost`; see the top of the file). Extend it as you go.
- **My tests** runs your own `test_*.py` files with pytest. `test_example.py` is an example to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
