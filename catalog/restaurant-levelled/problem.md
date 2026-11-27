# Restaurant reservation book

You're building the in-memory reservation book for a busy restaurant. It keeps the tables and their seat counts and puts each party on a table for a seating, and later grows a walk-in waitlist, joined tables for large parties, and no-show handling. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{Restaurant}}` type. Keep building on it: later levels add methods to it. Standard library only.

**Time.** Every method takes `ts` as its first argument: the time of the call, in minutes. Times only ever increase from one call to the next. Levels 1 to 3 don't use `ts` yet, but keep it in the signatures.

**Slots.** A reservation is for a seating `slot`, a time on the same clock (`1140` is 19:00). Each slot is a separate seating: a table holds at most one party per slot, and reservations for different slots never clash.

## Level 1: tables and reservations

| Method | Behaviour |
|---|---|
| `{{add_table}}(ts, table_id, seats) → bool` | Adds a table with `seats` seats. Returns `false` if `table_id` already exists or `seats <= 0`. |
| `{{book}}(ts, name, size, slot) → string` | Reserves a table for a party of `size` called `name` at `slot` and returns the reservation's id. Ids are `"r1"`, `"r2"`, `"r3"`, … in order, counted across the whole restaurant; a failed call uses no id. Returns `""`, changing nothing, if `size <= 0` or no table fits. |
| `{{cancel}}(ts, reservation_id) → bool` | Cancels the reservation, so its table is free again at that slot. Returns `false` if the reservation doesn't exist or is already cancelled. |
| `{{table_of}}(ts, reservation_id) → string` | The id of the table the reservation holds. `""` if the reservation doesn't exist or is cancelled. |
| `{{party_at}}(ts, table_id, slot) → string` | The `name` of the party holding the table at `slot`. `""` if nobody does or the table doesn't exist. |

**Which table.** `{{book}}` picks, among the tables free at that slot with `seats >= size`, the one with the fewest seats; ties go to the smallest table id in plain string order (by character code), whatever order the tables were added in.

### Example

```
{{add_table}}(1, "T1", 2)         → true
{{add_table}}(1, "T2", 4)         → true
{{add_table}}(1, "T3", 4)         → true
{{book}}(2, "maya", 3, 1140)      → "r1"
{{book}}(3, "leo", 2, 1140)       → "r2"
{{book}}(4, "ana", 2, 1140)       → "r3"
{{book}}(5, "sam", 4, 1140)       → ""      (no 4-seat table left at 19:00)
{{book}}(6, "sam", 4, 1260)       → "r4"
{{table_of}}(7, "r3")             → "T3"    (T1 is leo's, T2 is maya's)
{{cancel}}(8, "r1")               → true
{{book}}(9, "sam", 4, 1140)       → "r5"
{{party_at}}(10, "T2", 1140)      → "sam"
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
