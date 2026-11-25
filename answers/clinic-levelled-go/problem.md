# Clinic scheduler

You're building the in-memory scheduling core of an outpatient clinic. **Clinicians** see patients in **consulting rooms**; every appointment has a **type** (like `checkup`) with a fixed length. The scheduler later grows rankings and free-slot search, check-ins, no-shows and waitlists, then reschedules, hand-overs between clinicians and an audit history. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in package `clinic`, in `clinic.go`. Keep building on the same `Clinic` type: later levels add methods to it.

**Time.** Every method takes `ts int` as its first argument: the time of the call, in minutes. Timestamps strictly increase from one call to the next. Appointment start times are minutes on the same clock.

**Intervals.** An appointment of a 30-minute type starting at `540` runs `540-570`: it holds its clinician and its room from minute 540 up to, but not including, 570. Back-to-back appointments (one ends at 570, the next starts at 570) don't clash. Every type lasts at least 15 minutes.

## Level 1: clinicians, rooms and bookings

| Method | Behaviour |
|---|---|
| `AddClinician(ts int, id string) bool` | Adds a clinician. `false`, changing nothing, if the id is taken. Ids (all kinds) are case-sensitive. |
| `AddRoom(ts int, id string) bool` | Adds a room. `false` if the id is taken. |
| `AddType(ts int, name string, minutes int) bool` | Adds an appointment type lasting `minutes`. `false` if the name is taken. |
| `Book(ts int, clinician, patient, kind string, start int) (string, bool)` | Books `patient` with `clinician` for an appointment of type `kind` from `start`. Returns its id and `true`: `"appt1"`, `"appt2"`, … numbered across the whole clinic. Returns `"", false` if the clinician or type doesn't exist, `start < ts`, the clinician already has an appointment that overlaps, or no room is free for the whole interval. Failed calls use up no id. |
| `Cancel(ts int, id string) bool` | Cancels a booked appointment. `false`, changing nothing, if the id doesn't exist, it's already cancelled, or it has started (`ts >= start`). A cancelled appointment holds no clinician or room. |
| `Appointment(ts int, id string) (string, bool)` | `"clinician patient type room start-end status"` and `true`, e.g. `"dr-lee pat-7 checkup room-1 540-570 booked"`; `"", false` for an unknown id. In this level the status is `booked` or `cancelled`. |

**Rooms.** Patients don't pick rooms: `Book` gives the appointment the free room whose id comes first in plain Go string order, whatever order the rooms were added in. Anyone's appointment holds its room; two appointments never share a room at the same time.

### Example

```
AddClinician(1, "dr-lee")                         -> true
AddClinician(2, "dr-ng")                          -> true
AddRoom(3, "room-2")                              -> true
AddRoom(4, "room-1")                              -> true
AddType(5, "checkup", 30)                         -> true
Book(6, "dr-lee", "pat-1", "checkup", 540)        -> "appt1", true
Book(7, "dr-lee", "pat-2", "checkup", 555)        -> "", false     (dr-lee is busy until 570)
Book(8, "dr-ng", "pat-2", "checkup", 555)         -> "appt2", true
Appointment(9, "appt2")                           -> "dr-ng pat-2 checkup room-2 555-585 booked", true
Book(10, "dr-lee", "pat-3", "checkup", 570)       -> "appt3", true (room-1 again)
Cancel(11, "appt1")                               -> true
Cancel(12, "appt1")                               -> false
```

## Checking your work

- **Run** runs `cmd/run/main.go`, a small program that reads commands from stdin (`clinician`, `room`, `type`, `book`, `cancel`, `show`; see the top of the file). Extend it as you go.
- **My tests** runs your own `*_test.go` files. `clinic_example_test.go` is an example to copy.
- **Submit** runs the hidden tests for every level you've unlocked.
