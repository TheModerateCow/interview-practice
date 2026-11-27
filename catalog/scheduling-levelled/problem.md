# Team calendar

You're building the core of a team calendar's **find a time** feature for a company whose people work in many time zones. Each **attendee** has a fixed UTC offset and local working hours; their meetings and leave are **busy blocks** stored in UTC. The calendar later grows profile changes and agendas, then searches for the earliest slot everyone can make, and finally for slots that only need a quorum. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Keep building on the same `{{TeamCalendar}}` type: later levels add methods to it.

**Time.** All times are whole **minutes since the calendar's start**, in UTC; minute `0` is midnight UTC on day 0, minute `1440` midnight UTC on day 1. Every time passed in is between `0` and `1,000,000`.

**Intervals.** A busy block `[{{start}}, {{end}})` covers minute `{{start}}` up to, but not including, `{{end}}`: a block `600-660` makes minute 600 busy and minute 660 free.

## Level 1: attendees, busy blocks and free minutes

| Method | Behaviour |
|---|---|
| `{{add_attendee}}({{id}}, {{offset}}, {{work_start}}, {{work_end}}) → bool` | Adds an attendee. `{{offset}}` is their time zone in minutes: **local time = UTC + offset** (`330` for UTC+5:30, `-300` for UTC-5; always between `-720` and `840`). `{{work_start}}` and `{{work_end}}` are their working hours as local minutes of the day (below). Returns `false`, changing nothing, if the id is taken. Ids are case-sensitive. |
| `{{add_busy}}({{id}}, {{start}}, {{end}}) → busy id or none` | Marks `[{{start}}, {{end}})` busy for the attendee. Returns the block's id: `"busy1"`, `"busy2"`, … numbered across the whole calendar. Returns *none* if the attendee doesn't exist or `{{start}} >= {{end}}`; a failed call uses up no id. Blocks may overlap, nest, or span several days. |
| `{{remove_busy}}({{id}}, {{busy_id}}) → bool` | Deletes one of the attendee's busy blocks. `false`, changing nothing, if the attendee doesn't exist or has no block with that id (never issued, already removed, or someone else's). |
| `{{is_free}}({{id}}, {{minute}}) → bool` | `true` if the attendee is working at that minute and no busy block of theirs covers it. `false` for an unknown attendee. |

**Working hours** repeat every local day. Both values are local minutes of the day, `0 <= {{work_start}} < 1440`, `0 <= {{work_end}} <= 1440`, and they differ.

- If `{{work_start}} < {{work_end}}` the attendee works `[{{work_start}}, {{work_end}})` of each local day: `540, 1020` is 09:00 to 17:00, and `0, 1440` is all day.
- If `{{work_start}} > {{work_end}}` it's an overnight shift: from `{{work_start}}` to midnight, then from midnight to `{{work_end}}`. `1320, 360` is 22:00 to 06:00.

A minute's local time of day is `(minute + offset)` wrapped into `0`–`1439`, so a minute near the start of a UTC day can fall on the previous local day.

### Example

```
{{add_attendee}}("ana", 0, 540, 1020)         → true     (UTC, 09:00-17:00)
{{add_attendee}}("raj", 330, 540, 1080)       → true     (UTC+5:30, 09:00-18:00 local = UTC 210-750)
{{add_attendee}}("ana", 60, 0, 1440)          → false
{{add_busy}}("ana", 600, 660)                 → "busy1"
{{add_busy}}("raj", 700, 650)                 → none
{{add_busy}}("zoe", 600, 660)                 → none
{{is_free}}("ana", 599)                       → true
{{is_free}}("ana", 600)                       → false
{{is_free}}("ana", 660)                       → true
{{is_free}}("raj", 209)                       → false    (08:59 in UTC+5:30)
{{is_free}}("raj", 210)                       → true
{{remove_busy}}("raj", "busy1")               → false    (it's ana's)
{{remove_busy}}("ana", "busy1")               → true
{{is_free}}("ana", 600)                       → true
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
