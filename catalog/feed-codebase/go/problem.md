# Home feed service

You've joined the team behind the home feed of a social app. This Go package (`feed`) is the in-memory core of one feed region: people sign up, follow each other, publish posts and like them, mute accounts they're tired of, and open their home feed, which is ranked and served a page at a time with an opaque cursor for infinite scroll.

The feed rules, as the product spec states them:

- A viewer's home feed at time `now` holds their own posts and posts by the accounts they follow, minus accounts they have muted at `now`. Only posts published in the last 7 days count: `now - 7 days <= CreatedAt <= now`.
- Ranking: `score = log2(1 + likes) + CreatedAt / 21600`, so each doubling of a post's likes is worth 6 hours of recency. Highest score first; equal scores go in post-id order.
- `HomeFeed(viewer, now, limit, cursor)` returns a `Page{PostIDs, NextCursor}`. An empty `cursor` asks for the first page; passing `NextCursor` back returns the next page; it is `""` when there is nothing after this page.
- A like counts once per user per post.
- `MuteFor(viewer, target, now, hours)` hides the target from the viewer from `now` until exactly `hours` hours later; `Mute(viewer, target, now)` hides them for good. Muting again replaces the earlier mute.

Times are whole seconds since the epoch. Errors are sentinel values (`ErrUnknownUser`, `ErrBadCursor`, `ErrBadLimit`, ...) that wrap with `%w`; test them with `errors.Is`.

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

```go
func TestDayMuteHoldsAllDay(t *testing.T) {
	s := New()
	for _, u := range []string{"ana", "ben"} {
		s.AddUser(u)
	}
	s.Follow("ana", "ben")
	s.Publish("b1", "ben", 1_000, "")
	s.MuteFor("ana", "ben", 2_000, 24)
	page, _ := s.HomeFeed("ana", 2_000+3*3600, 10, "")
	if len(page.PostIDs) != 0 {
		t.Fatalf("muted account is back: %v", page.PostIDs)
	}
}
```

## Phase 2: "while you were away"

`(*Service).CatchUp(viewer string, since, now int64, limit int) ([]string, error)` powers the carousel shown when someone opens the app after a break (`since` is when they last opened it; the app asks for `limit` 5). It is not implemented yet. It must:

1. Consider only posts by accounts the viewer follows. The viewer's own posts never appear, and accounts muted at `now` are skipped.
2. Consider only posts published after `since` (strictly) and no later than `now`, and never older than the home feed's window (`now - 7 days`, inclusive), however old `since` is.
3. Rank them exactly like the home feed.
4. Take at most 2 posts per account: that account's two highest-ranked qualifying posts.
5. Return the first `limit` post ids in rank order, or an empty list if nothing qualifies.
6. Return `ErrUnknownUser` for an unknown viewer and `ErrBadLimit` if `limit < 1`.

Example:

```go
// ana follows ben and cy
s.Publish("b1", "ben", 1_000, "")
s.Publish("c1", "cy", 1_500, "")
s.Publish("b2", "ben", 2_000, "")
s.Publish("a1", "ana", 2_500, "")
s.Publish("b3", "ben", 3_000, "")
s.Publish("b4", "ben", 3_500, "")
s.CatchUp("ana", 1_000, 4_000, 5) // [b4 b3 c1]
s.CatchUp("ana", 1_000, 4_000, 2) // [b4 b3]
```

## Checking your work

- **Run** runs `cmd/run/main.go`, a small program that reads commands from stdin (`user`, `follow`, `unfollow`, `mute`, `post`, `like`, `feed`, `more`, `catchup`; see the top of the file).
- **My tests** runs your own `*_test.go` files with `go test`. `feed_example_test.go` is an example to copy; the test above is a good first one to add.
- **Submit** runs the hidden tests for the phases you've unlocked. Phase 3 opens once phase 2 passes, or with 15 minutes left.
