# Notification fan-out

You've joined the team that owns the messaging platform's notification fan-out. Product teams (billing, security, social, marketing) hand it one notification per user; this Python package (`notify`) applies the user's preferences and limits, decides which channels the notification goes out on, and logs every decision. The daily digest email is built from the same log.

How a notification is handled, in order:

1. **Dedupe.** Senders retry, so each notification carries a dedupe key. If the same user already had a notification with that key accepted (sent or held) less than `DEDUPE_WINDOW` (3600) seconds earlier, the new one is a `duplicate`: dropped and logged. A duplicate doesn't restart the window.
2. **Quiet hours.** Each user has quiet hours `[quiet_from, quiet_to)` in **their local time** (a fixed `offset_min`, minutes east of UTC; `22 -> 7` wraps past midnight; equal hours mean none). A non-urgent notification in quiet hours is `held` for the digest. Urgent ones ignore quiet hours.
3. **Hourly caps.** A user gets at most 6 email, 4 push and 2 SMS deliveries in any 3600 seconds (a delivery at `t` stops counting at `t + 3600`). The notification goes out on each of the user's channels, in the user's order, that is under its cap. If no channel takes it, it is `held`.

Timestamps are whole seconds since the epoch (UTC) and never go backwards for a user. New users get email only and no quiet hours.

The round has three phases: fix the bugs, build the missing feature, then (revealed later) make the hot path fast. Read around before you change anything: the code is small, and causes are rarely in the file where the symptom shows.

## Phase 1: bug report

> **NTF-412: notification complaints from this week**
>
> 1. **Night pushes in Asia.** Users in Singapore and Tokyo with quiet hours 22:00-07:00 are woken up by promo pushes around 2 a.m. their time. Users in London with the same settings are fine.
> 2. **The launch announcement reached one person.** Marketing sent the product-launch notification to every user with the dedupe key `launch-2026`. The first user got it; everyone else's is logged as `duplicate`.
> 3. **Preferences import scrambled channels.** Ops bulk-imported channel preferences with a tool that calls `set_channels` once per CSV row. Afterwards, some users get notifications on channels they never chose, and the same users lost channels they had picked.
>
> Expected: quiet hours follow the user's own clock; dedupe keys only ever match the same user's notifications; a user's channels change only when `set_channels` is called for that user.

This test reproduces item 2 and fails today:

```python
def test_broadcast_reaches_everyone():
    s = Service()
    s.add_user("ana", 0)
    s.add_user("ben", 60)
    for id in ("ana", "ben"):
        res = s.send(Notification(user=id, topic="news", key="launch-2026", title="We launched", at=500))
        assert res.status == SENT, id
```

## Phase 2: daily digest

`Service.digest(id, now)` (it delegates to `build_digest` in `notify/digest.py`) builds the user's daily digest email. It is not implemented yet. It must:

1. Raise `UnknownUser` for an unknown user.
2. Cover the user's **held** notifications (not sent ones, not duplicates) from the user's **previous local day**: the local calendar day before the one containing `now`, using the user's `offset_min`. Local days run from local midnight to local midnight.
3. Produce one `DigestLine(topic, count, latest)` per topic: `count` is how many held notifications it has; `latest` is the `title` of the most recent one (for the same second, the one sent last).
4. Order lines by `count`, most first; equal counts go in topic order.
5. Return an empty list when there is nothing to show. Calling it again returns the same digest (it changes nothing).

Example (user `kai`, `offset_min` 540, so local midnight is 15:00 UTC; no channels, so everything is held):

```
held at day 1 14:00 UTC (news "a"), day 1 16:00 (news "b"), day 2 06:00 (promo "c")
digest("kai", day 2 + 16:00 UTC) -> [{news 1 b} {promo 1 c}]
digest("kai", day 2 + 10:00 UTC) -> [{news 1 a}]
```

## Checking your work

- **Run** runs `main.py`, a small program that reads commands from stdin (`user`, `channels`, `quiet`, `send`, `digest`; see the top of the file).
- **My tests** runs your own `test_*.py` files. `test_example.py` is an example to copy; the test above is a good first one to add.
- **Submit** runs the hidden tests for the phases you've unlocked. Phase 3 opens once phase 2 passes, or with 15 minutes left.
