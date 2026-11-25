# Quorum meeting finder

Your team calendar has a "find a time" button for meetings that don't need everyone: say, any 3 of the 5 reviewers. In `scheduler.ts`, implement `earliestQuorumSlot(attendees, days, duration, quorum)`: the **earliest UTC minute `t`** at which at least `quorum` attendees are each free for the **whole** of `[t, t + duration)`. Return `-1` if no such `t` exists.

All times are integer minutes. The planning window is UTC `[0, days * 1440)`, and the meeting must fit inside it.

Each attendee has:
- `offset`: their time zone as a fixed offset in minutes, local time = UTC + `offset` (e.g. `330` for UTC+5:30, `-300` for UTC-5).
- `workStart`, `workEnd`: working hours in **local** minutes of the day, `[workStart, workEnd)`, the same every day. Local days that only partly overlap the window count for the part inside it.
- `busy`: busy blocks `[start, end)` in **UTC** minutes, in any order, possibly overlapping or nested, possibly spanning several days.

An attendee is free at a minute when it falls inside their working hours and outside all their busy blocks. Working hours of consecutive days that touch (e.g. `0`–`1440`) join up, so a meeting can run across local midnight.

## Example

```
days = 1, duration = 60, quorum = 2
A: offset 0,    work 540-1020 (09:00-17:00), busy [540,610), [660,720)
B: offset 60,   work 540-1020 local = UTC 480-960, busy [500,630)
C: offset -120, work 480-720  local = UTC 600-840, busy none
-> 630
```
A is free from 610 but only for 50 minutes before 660, then again from 720. C can start any time in 600–780 and B any time in 630–900, so 630 is the first minute where two attendees can each hold the full hour.

## Constraints

- `1 <= attendees.length <= 1000`, `1 <= days <= 30`, `1 <= duration <= days * 1440`, `1 <= quorum` (it may exceed the number of attendees)
- `-720 <= offset <= 840`, `0 <= workStart < workEnd <= 1440`
- `0 <= start < end <= days * 1440`; at most 2·10^5 busy blocks in total

## Checking your work

- **Run** runs `main.ts`, which reads a request from stdin (format at the top of the file) and prints the answer.
- **My tests** runs your `*.test.ts` files; `example.test.ts` is one to copy.
- **Submit** runs the hidden tests.
