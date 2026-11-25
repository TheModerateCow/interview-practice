# Home feed service

You've joined the team behind the home feed of a social app. This Python package (`feed`) is the in-memory core of one feed region: people sign up, follow each other, publish posts and like them, mute accounts they're tired of, and open their home feed, which is ranked and served a page at a time with an opaque cursor for infinite scroll.

The feed rules, as the product spec states them:

- A viewer's home feed at time `now` holds their own posts and posts by the accounts they follow, minus accounts they have muted at `now`. Only posts published in the last 7 days count: `now - 7 days <= created_at <= now`.
- Ranking: `score = log2(1 + likes) + created_at / 21600`, so each doubling of a post's likes is worth 6 hours of recency. Highest score first; equal scores go in post-id order.
- `home_feed(viewer, now, limit=10, cursor=None)` returns a `Page(post_ids, next_cursor)`. Passing `next_cursor` back returns the next page; it is `None` when there is nothing after this page.
- A like counts once per user per post.
- `mute(viewer, target, now, hours=None)` hides the target from the viewer from `now` until exactly `hours` hours later, or for good when `hours` is `None`. Muting again replaces the earlier mute.

Times are whole seconds since the epoch.

The round has three phases: fix the bugs, build the missing feature, then (revealed later) make the hot path fast. Read around before you change anything: the code is small, and the causes are rarely where the symptom shows.

## Phase 1: bug report

> **FEED-2291: feed quality complaints after the 4.12 app release**
>
> 1. **Likes counted twice.** The new app retries a like when the request times out. Posts liked once by a user show 2 or 3 likes, and those posts climb the feed above posts that really are more popular.
> 2. **Scrolling repeats and skips posts.** When someone posts a burst (a thread, a photo dump) within a few seconds, scrolling the feed sometimes shows a post from the previous page again, and sometimes a post never appears at all. Small pages make it worse.
> 3. **24-hour mutes wear off early.** People who mute an account "for 24 hours" see it back in their feed within the hour.
>
> Expected: a user's like counts once however often it arrives; paging through the feed shows every post exactly once, in ranking order; a mute for `h` hours lasts exactly `h` hours.

This test reproduces item 3 and fails today:

```python
def test_day_mute_holds_all_day():
    svc = FeedService()
    for user in ("ana", "ben"):
        svc.add_user(user)
    svc.follow("ana", "ben")
    svc.publish("b1", "ben", 1_000)
    svc.mute("ana", "ben", now=2_000, hours=24)
    assert svc.home_feed("ana", now=2_000 + 3 * 3600).post_ids == []
```

## Phase 2: "while you were away"

`FeedService.catch_up(viewer, since, now, limit=5) -> list[str]` powers the carousel shown when someone opens the app after a break (`since` is when they last opened it). It is not implemented yet. It must:

1. Consider only posts by accounts the viewer follows. The viewer's own posts never appear, and accounts muted at `now` are skipped.
2. Consider only posts published after `since` (strictly) and no later than `now`, and never older than the home feed's window (`now - 7 days`, inclusive), however old `since` is.
3. Rank them exactly like the home feed.
4. Take at most 2 posts per account: that account's two highest-ranked qualifying posts.
5. Return the first `limit` post ids in rank order, or an empty list if nothing qualifies.
6. Raise `UnknownUser` for an unknown viewer and `ValueError` if `limit < 1`.

Example:

```python
# ana follows ben and cy
svc.publish("b1", "ben", 1_000)
svc.publish("c1", "cy", 1_500)
svc.publish("b2", "ben", 2_000)
svc.publish("a1", "ana", 2_500)
svc.publish("b3", "ben", 3_000)
svc.publish("b4", "ben", 3_500)
svc.catch_up("ana", since=1_000, now=4_000)           # ["b4", "b3", "c1"]
svc.catch_up("ana", since=1_000, now=4_000, limit=2)  # ["b4", "b3"]
```

## Checking your work

- **Run** runs `main.py`, a small program that reads commands from stdin (`user`, `follow`, `unfollow`, `mute`, `post`, `like`, `feed`, `more`, `catchup`; see the top of the file).
- **My tests** runs your own `test_*.py` files with pytest. `test_example.py` is an example to copy; the test above is a good first one to add.
- **Submit** runs the hidden tests for the phases you've unlocked. Phase 3 opens once phase 2 passes, or with 15 minutes left.
