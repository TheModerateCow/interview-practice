# Clinic scheduler

You're building the in-memory scheduling core of an outpatient clinic. **Clinicians** see patients in **consulting rooms**; every appointment has a **type** (like `checkup`) with a fixed length. The scheduler later grows rankings and free-slot search, check-ins, no-shows and waitlists, then reschedules, hand-overs between clinicians and an audit history. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{Clinic}}` type: later levels add methods to it.

**Time.** Every method takes `{{ts}}` as its first argument: the time of the call, in minutes. Timestamps strictly increase from one call to the next. Appointment start times are minutes on the same clock.

**Intervals.** An appointment of a 30-minute type starting at `540` runs `540-570`: it holds its clinician and its room from minute 540 up to, but not including, 570. Back-to-back appointments (one ends at 570, the next starts at 570) don't clash. Every type lasts at least 15 minutes.

## Level 1: clinicians, rooms and bookings

| Method | Behaviour |
|---|---|
| `{{add_clinician}}({{ts}}, {{id}}) → bool` | Adds a clinician. `false`, changing nothing, if the id is taken. Ids (all kinds) are case-sensitive. |
| `{{add_room}}({{ts}}, {{id}}) → bool` | Adds a room. `false` if the id is taken. |
| `{{add_type}}({{ts}}, {{name}}, {{minutes}}) → bool` | Adds an appointment type lasting `minutes`. `false` if the name is taken. |
| `{{book}}({{ts}}, {{clinician}}, {{patient}}, {{kind}}, {{start}}) → appointment id, or absent` | Books `{{patient}}` with `{{clinician}}` for an appointment of type `{{kind}}` from `{{start}}`. Returns its id: `"appt1"`, `"appt2"`, … numbered across the whole clinic. Returns nothing (absent) if the clinician or type doesn't exist, `{{start}} < {{ts}}`, the clinician already has an appointment that overlaps, or no room is free for the whole interval. Failed calls use up no id. |
| `{{cancel}}({{ts}}, {{id}}) → bool` | Cancels a booked appointment. `false`, changing nothing, if the id doesn't exist, it's already cancelled, or it has started (`{{ts}} >= start`). A cancelled appointment holds no clinician or room. |
| `{{appointment}}({{ts}}, {{id}}) → string, or absent` | `"clinician patient type room start-end status"` e.g. `"dr-lee pat-7 checkup room-1 540-570 booked"`; Absent for an unknown id. In this level the status is `booked` or `cancelled`. |

**Rooms.** Patients don't pick rooms: `{{book}}` gives the appointment the free room whose id comes first in plain string order (by character code), whatever order the rooms were added in. Anyone's appointment holds its room; two appointments never share a room at the same time.

### Example

```
{{add_clinician}}(1, "dr-lee")                         → true
{{add_clinician}}(2, "dr-ng")                          → true
{{add_room}}(3, "room-2")                              → true
{{add_room}}(4, "room-1")                              → true
{{add_type}}(5, "checkup", 30)                         → true
{{book}}(6, "dr-lee", "pat-1", "checkup", 540)        → "appt1"
{{book}}(7, "dr-lee", "pat-2", "checkup", 555)        → absent     (dr-lee is busy until 570)
{{book}}(8, "dr-ng", "pat-2", "checkup", 555)         → "appt2"
{{appointment}}(9, "appt2")                           → "dr-ng pat-2 checkup room-2 555-585 booked"
{{book}}(10, "dr-lee", "pat-3", "checkup", 570)       → "appt3" (room-1 again)
{{cancel}}(11, "appt1")                               → true
{{cancel}}(12, "appt1")                               → false
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
