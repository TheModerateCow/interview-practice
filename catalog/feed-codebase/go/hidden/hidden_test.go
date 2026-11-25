package feed

import (
	"errors"
	"fmt"
	"math/rand"
	"reflect"
	"strings"
	"testing"
	"time"
)

// The app compiles one phase's tests at a time: keep every import used outside them.
var (
	_ = errors.Is
	_ = fmt.Sprint
	_ = rand.Intn
	_ = reflect.DeepEqual
	_ = strings.Join
	_ = time.Second
)

const (
	hiddenT0  int64 = 1_750_000_000
	hiddenH   int64 = 60 * 60
	hiddenDay int64 = 24 * hiddenH
)

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenIDs(t *testing.T, what string, got, want []string) {
	t.Helper()
	if strings.Join(got, ",") != strings.Join(want, ",") {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenErr(t *testing.T, what string, got, want error) {
	t.Helper()
	if !errors.Is(got, want) {
		t.Fatalf("%s: got error %v want %v", what, got, want)
	}
}

func hiddenSvc(users ...string) *Service {
	s := New()
	for _, u := range users {
		s.AddUser(u)
	}
	return s
}

func hiddenFollow(t *testing.T, s *Service, a, b string) {
	t.Helper()
	if err := s.Follow(a, b); err != nil {
		t.Fatalf("Follow(%s,%s): %v", a, b, err)
	}
}

func hiddenPub(t *testing.T, s *Service, id, author string, at int64) {
	t.Helper()
	if _, err := s.Publish(id, author, at, ""); err != nil {
		t.Fatalf("Publish(%s): %v", id, err)
	}
}

func hiddenLike(t *testing.T, s *Service, post, user string) int {
	t.Helper()
	n, err := s.Like(post, user)
	if err != nil {
		t.Fatalf("Like(%s,%s): %v", post, user, err)
	}
	return n
}

func hiddenMuteFor(t *testing.T, s *Service, viewer, target string, now int64, hours float64) {
	t.Helper()
	if err := s.MuteFor(viewer, target, now, hours); err != nil {
		t.Fatalf("MuteFor(%s,%s): %v", viewer, target, err)
	}
}

func hiddenPage(t *testing.T, s *Service, viewer string, now int64, limit int, cursor string) Page {
	t.Helper()
	p, err := s.HomeFeed(viewer, now, limit, cursor)
	if err != nil {
		t.Fatalf("HomeFeed(%s): %v", viewer, err)
	}
	return p
}

func hiddenFeed(t *testing.T, s *Service, viewer string, now int64) []string {
	t.Helper()
	return hiddenPage(t, s, viewer, now, 10, "").PostIDs
}

func hiddenAllPages(t *testing.T, s *Service, viewer string, now int64, limit int) ([]string, int) {
	t.Helper()
	var ids []string
	cursor, pages := "", 0
	for {
		p := hiddenPage(t, s, viewer, now, limit, cursor)
		ids = append(ids, p.PostIDs...)
		pages++
		if pages >= 100 {
			t.Fatalf("paging never ended")
		}
		if p.NextCursor == "" {
			return ids, pages
		}
		cursor = p.NextCursor
	}
}

func hiddenLikes(t *testing.T, s *Service, id string) int {
	t.Helper()
	p, err := s.Post(id)
	if err != nil {
		t.Fatalf("Post(%s): %v", id, err)
	}
	return p.Likes
}

// ---------------------------------------------------------------- phase 1

func Test_p1_feed_is_followed_and_own_posts_newest_first(t *testing.T) {
	s := hiddenSvc("ana", "ben", "cy", "dee")
	hiddenFollow(t, s, "ana", "ben")
	hiddenFollow(t, s, "ana", "dee")
	hiddenPub(t, s, "b1", "ben", hiddenT0)
	hiddenPub(t, s, "c1", "cy", hiddenT0+10)
	hiddenPub(t, s, "a1", "ana", hiddenT0+20)
	hiddenPub(t, s, "d1", "dee", hiddenT0+30)
	hiddenPub(t, s, "b2", "ben", hiddenT0+40)
	page := hiddenPage(t, s, "ana", hiddenT0+100, 10, "")
	hiddenIDs(t, "ana's feed", page.PostIDs, []string{"b2", "d1", "a1", "b1"})
	hiddenEq(t, "next cursor", page.NextCursor, "")
	hiddenIDs(t, "cy's feed", hiddenFeed(t, s, "cy", hiddenT0+100), []string{"c1"})
}

func Test_p1_likes_trade_against_recency(t *testing.T) {
	s := hiddenSvc("ana", "ben", "u1", "u2", "u3")
	hiddenFollow(t, s, "ana", "ben")
	hiddenPub(t, s, "old", "ben", hiddenT0)
	hiddenPub(t, s, "mid", "ben", hiddenT0+11*hiddenH)
	hiddenPub(t, s, "new", "ben", hiddenT0+13*hiddenH)
	for _, u := range []string{"u1", "u2", "u3"} {
		if n := hiddenLike(t, s, "old", u); n < 1 {
			t.Fatalf("like count %d", n)
		}
	}
	hiddenEq(t, "old likes", hiddenLikes(t, s, "old"), 3)
	hiddenIDs(t, "feed", hiddenFeed(t, s, "ana", hiddenT0+14*hiddenH), []string{"new", "old", "mid"})
}

func Test_p1_equal_scores_tie_on_post_id(t *testing.T) {
	s := hiddenSvc("ana", "ben", "cy")
	hiddenFollow(t, s, "ana", "ben")
	hiddenFollow(t, s, "ana", "cy")
	hiddenPub(t, s, "p-c", "cy", hiddenT0)
	hiddenPub(t, s, "p-a", "ben", hiddenT0)
	hiddenPub(t, s, "p-b", "ben", hiddenT0)
	hiddenIDs(t, "feed", hiddenFeed(t, s, "ana", hiddenT0+5), []string{"p-a", "p-b", "p-c"})
}

func Test_p1_retried_like_counts_once(t *testing.T) {
	s := hiddenSvc("ana", "ben", "cy")
	hiddenFollow(t, s, "ana", "ben")
	hiddenPub(t, s, "x", "ben", hiddenT0)
	hiddenPub(t, s, "y", "ben", hiddenT0+7*hiddenH)
	for i := 0; i < 3; i++ {
		hiddenEq(t, "like by cy", hiddenLike(t, s, "x", "cy"), 1)
	}
	hiddenEq(t, "x likes", hiddenLikes(t, s, "x"), 1)
	hiddenIDs(t, "feed", hiddenFeed(t, s, "ana", hiddenT0+8*hiddenH), []string{"y", "x"})
	hiddenEq(t, "like by ana", hiddenLike(t, s, "x", "ana"), 2)
	hiddenIDs(t, "feed after", hiddenFeed(t, s, "ana", hiddenT0+8*hiddenH), []string{"x", "y"})
}

func Test_p1_like_errors(t *testing.T) {
	s := hiddenSvc("ana", "ben")
	hiddenPub(t, s, "x", "ben", hiddenT0)
	_, err := s.Like("nope", "ana")
	hiddenErr(t, "unknown post", err, ErrUnknownPost)
	_, err = s.Like("x", "ghost")
	hiddenErr(t, "unknown user", err, ErrUnknownUser)
	hiddenEq(t, "x likes", hiddenLikes(t, s, "x"), 0)
}

func Test_p1_paging_a_thread_shows_each_post_once(t *testing.T) {
	s := hiddenSvc("ana", "ben")
	hiddenFollow(t, s, "ana", "ben")
	for i := 0; i < 14; i++ {
		hiddenPub(t, s, fmt.Sprintf("t%02d", i), "ben", hiddenT0+int64(i))
	}
	hiddenPub(t, s, "t06b", "ben", hiddenT0+6)
	now := hiddenT0 + 60
	everything := hiddenPage(t, s, "ana", now, 100, "").PostIDs
	hiddenIDs(t, "top of the feed", everything[:4], []string{"t13", "t12", "t11", "t10"})
	at := func(id string) int {
		for i, e := range everything {
			if e == id {
				return i
			}
		}
		return -1
	}
	hiddenEq(t, "t06b right after t06", at("t06b"), at("t06")+1)
	for _, limit := range []int{2, 3, 4} {
		ids, pages := hiddenAllPages(t, s, "ana", now, limit)
		hiddenIDs(t, fmt.Sprintf("limit %d", limit), ids, everything)
		hiddenEq(t, fmt.Sprintf("pages at limit %d", limit), pages, (len(everything)+limit-1)/limit)
	}
}

func Test_p1_paging_mixed_engagement(t *testing.T) {
	s := hiddenSvc("ana", "ben", "cy", "l0", "l1", "l2")
	hiddenFollow(t, s, "ana", "ben")
	hiddenFollow(t, s, "ana", "cy")
	for i := 0; i < 9; i++ {
		hiddenPub(t, s, fmt.Sprintf("b%d", i), "ben", hiddenT0+int64(3*i))
		hiddenPub(t, s, fmt.Sprintf("c%d", i), "cy", hiddenT0+int64(3*i+1))
	}
	for i, liker := range []string{"l0", "l1", "l2"} {
		hiddenLike(t, s, fmt.Sprintf("b%d", i), liker)
		hiddenLike(t, s, fmt.Sprintf("c%d", i+4), liker)
	}
	now := hiddenT0 + 100
	everything := hiddenPage(t, s, "ana", now, 50, "").PostIDs
	hiddenEq(t, "feed size", len(everything), 18)
	ids, _ := hiddenAllPages(t, s, "ana", now, 4)
	hiddenIDs(t, "paged feed", ids, everything)
}

func Test_p1_last_page_and_bad_cursor(t *testing.T) {
	s := hiddenSvc("ana")
	for i := 0; i < 4; i++ {
		hiddenPub(t, s, fmt.Sprintf("a%d", i), "ana", hiddenT0+int64(i*10))
	}
	now := hiddenT0 + 100
	first := hiddenPage(t, s, "ana", now, 2, "")
	hiddenIDs(t, "first page", first.PostIDs, []string{"a3", "a2"})
	if first.NextCursor == "" {
		t.Fatalf("first page has no next cursor")
	}
	second := hiddenPage(t, s, "ana", now, 2, first.NextCursor)
	hiddenIDs(t, "second page", second.PostIDs, []string{"a1", "a0"})
	hiddenEq(t, "second cursor", second.NextCursor, "")
	hiddenEq(t, "exactly full page cursor", hiddenPage(t, s, "ana", now, 4, "").NextCursor, "")
	_, err := s.HomeFeed("ana", now, 2, "not-a-cursor")
	hiddenErr(t, "bad cursor", err, ErrBadCursor)
	_, err = s.HomeFeed("ana", now, 0, "")
	hiddenErr(t, "limit 0", err, ErrBadLimit)
}

func Test_p1_feed_window_edges(t *testing.T) {
	s := hiddenSvc("ana", "ben")
	hiddenFollow(t, s, "ana", "ben")
	now := hiddenT0 + 30*hiddenDay
	hiddenPub(t, s, "too-old", "ben", now-7*hiddenDay-1)
	hiddenPub(t, s, "oldest", "ben", now-7*hiddenDay)
	hiddenPub(t, s, "mid", "ben", now-3*hiddenDay)
	hiddenPub(t, s, "now", "ben", now)
	hiddenPub(t, s, "scheduled", "ben", now+1)
	hiddenIDs(t, "at now", hiddenFeed(t, s, "ana", now), []string{"now", "mid", "oldest"})
	hiddenIDs(t, "one second later", hiddenFeed(t, s, "ana", now+1), []string{"scheduled", "now", "mid"})
}

func Test_p1_permanent_mute_is_per_viewer(t *testing.T) {
	s := hiddenSvc("ana", "ben", "cy")
	hiddenFollow(t, s, "ana", "ben")
	hiddenFollow(t, s, "ana", "cy")
	hiddenFollow(t, s, "cy", "ben")
	hiddenPub(t, s, "b1", "ben", hiddenT0)
	hiddenPub(t, s, "c1", "cy", hiddenT0+1)
	if err := s.Mute("ana", "ben", hiddenT0+2); err != nil {
		t.Fatal(err)
	}
	hiddenIDs(t, "ana soon", hiddenFeed(t, s, "ana", hiddenT0+3), []string{"c1"})
	hiddenIDs(t, "ana days later", hiddenFeed(t, s, "ana", hiddenT0+6*hiddenDay), []string{"c1"})
	hiddenIDs(t, "cy", hiddenFeed(t, s, "cy", hiddenT0+3), []string{"c1", "b1"})
}

func Test_p1_timed_mute_lasts_its_hours(t *testing.T) {
	s := hiddenSvc("ana", "ben")
	hiddenFollow(t, s, "ana", "ben")
	hiddenPub(t, s, "b1", "ben", hiddenT0)
	start := hiddenT0 + hiddenH
	hiddenMuteFor(t, s, "ana", "ben", start, 24)
	hiddenIDs(t, "2h in", hiddenFeed(t, s, "ana", start+2*hiddenH), []string{})
	hiddenIDs(t, "last second", hiddenFeed(t, s, "ana", start+24*hiddenH-1), []string{})
	hiddenIDs(t, "mute over", hiddenFeed(t, s, "ana", start+24*hiddenH), []string{"b1"})
}

func Test_p1_short_mute_and_remute(t *testing.T) {
	s := hiddenSvc("ana", "ben")
	hiddenFollow(t, s, "ana", "ben")
	hiddenPub(t, s, "b1", "ben", hiddenT0)
	hiddenMuteFor(t, s, "ana", "ben", hiddenT0, 1.5)
	hiddenIDs(t, "89 min", hiddenFeed(t, s, "ana", hiddenT0+89*60), []string{})
	hiddenIDs(t, "90 min", hiddenFeed(t, s, "ana", hiddenT0+90*60), []string{"b1"})
	hiddenMuteFor(t, s, "ana", "ben", hiddenT0+2*hiddenH, 3)
	hiddenIDs(t, "remuted", hiddenFeed(t, s, "ana", hiddenT0+4*hiddenH), []string{})
	hiddenIDs(t, "remute over", hiddenFeed(t, s, "ana", hiddenT0+5*hiddenH), []string{"b1"})
}

func Test_p1_unfollow_and_account_errors(t *testing.T) {
	s := hiddenSvc("ana", "ben")
	hiddenFollow(t, s, "ana", "ben")
	if _, err := s.Publish("b1", "ben", hiddenT0, "first"); err != nil {
		t.Fatal(err)
	}
	if err := s.Unfollow("ana", "ben"); err != nil {
		t.Fatal(err)
	}
	hiddenIDs(t, "after unfollow", hiddenFeed(t, s, "ana", hiddenT0+1), []string{})
	hiddenErr(t, "follow self", s.Follow("ana", "ana"), ErrSelfFollow)
	hiddenErr(t, "follow ghost", s.Follow("ana", "ghost"), ErrUnknownUser)
	_, err := s.HomeFeed("ghost", hiddenT0, 10, "")
	hiddenErr(t, "ghost feed", err, ErrUnknownUser)
	_, err = s.Publish("g1", "ghost", hiddenT0, "")
	hiddenErr(t, "ghost publish", err, ErrUnknownUser)
	hiddenLike(t, s, "b1", "ana")
	_, err = s.Publish("b1", "ben", hiddenT0+5, "retry")
	hiddenErr(t, "duplicate post", err, ErrDuplicatePost)
	p, _ := s.Post("b1")
	hiddenEq(t, "text", p.Text, "first")
	hiddenEq(t, "likes", p.Likes, 1)
}

// ---------------------------------------------------------------- phase 2

func hiddenAway(t *testing.T) (*Service, int64) {
	t.Helper()
	s := hiddenSvc("ana", "ben", "cy", "dee", "l1", "l2", "l3")
	for _, f := range []string{"ben", "cy", "dee"} {
		hiddenFollow(t, s, "ana", f)
	}
	since := hiddenT0 + 10*hiddenH
	hiddenPub(t, s, "a-own", "ana", since+50)
	hiddenPub(t, s, "b-before", "ben", since-100)
	hiddenPub(t, s, "b-at", "ben", since)
	hiddenPub(t, s, "b1", "ben", since+1)
	hiddenPub(t, s, "b2", "ben", since+2*hiddenH)
	hiddenPub(t, s, "b3", "ben", since+3*hiddenH)
	hiddenPub(t, s, "c1", "cy", since+30*60)
	hiddenPub(t, s, "d1", "dee", since+4*hiddenH)
	hiddenPub(t, s, "d2", "dee", since+5*hiddenH)
	return s, since
}

func hiddenCatchUp(t *testing.T, s *Service, viewer string, since, now int64, limit int) []string {
	t.Helper()
	ids, err := s.CatchUp(viewer, since, now, limit)
	if err != nil {
		t.Fatalf("CatchUp(%s): %v", viewer, err)
	}
	return ids
}

func Test_p2_catch_up_ranks_new_posts_from_followed_accounts(t *testing.T) {
	s, since := hiddenAway(t)
	now := since + 6*hiddenH
	hiddenIDs(t, "catch up", hiddenCatchUp(t, s, "ana", since, now, 10), []string{"d2", "d1", "b3", "b2", "c1"})
}

func Test_p2_catch_up_two_per_account_by_rank(t *testing.T) {
	s, since := hiddenAway(t)
	now := since + 6*hiddenH
	for _, liker := range []string{"l1", "l2", "l3"} {
		hiddenLike(t, s, "b1", liker)
	}
	want := []string{"b1", "d2", "d1", "b3", "c1"}
	hiddenIDs(t, "catch up", hiddenCatchUp(t, s, "ana", since, now, 10), want)
	hiddenIDs(t, "earlier since", hiddenCatchUp(t, s, "ana", since-200, now, 10), want)
}

func Test_p2_catch_up_limit_and_default(t *testing.T) {
	s, since := hiddenAway(t)
	now := since + 6*hiddenH
	hiddenPub(t, s, "c2", "cy", since+5*hiddenH+30*60)
	hiddenIDs(t, "limit 5", hiddenCatchUp(t, s, "ana", since, now, 5), []string{"c2", "d2", "d1", "b3", "b2"})
	hiddenIDs(t, "limit 2", hiddenCatchUp(t, s, "ana", since, now, 2), []string{"c2", "d2"})
	hiddenIDs(t, "limit 1", hiddenCatchUp(t, s, "ana", since, now, 1), []string{"c2"})
}

func Test_p2_catch_up_skips_muted_unfollowed_and_future(t *testing.T) {
	s, since := hiddenAway(t)
	now := since + 4*hiddenH
	if err := s.Mute("ana", "dee", since); err != nil {
		t.Fatal(err)
	}
	if err := s.Unfollow("ana", "cy"); err != nil {
		t.Fatal(err)
	}
	hiddenPub(t, s, "b-later", "ben", now+1)
	hiddenIDs(t, "catch up", hiddenCatchUp(t, s, "ana", since, now, 10), []string{"b3", "b2"})
}

func Test_p2_catch_up_never_reaches_past_the_feed_window(t *testing.T) {
	s := hiddenSvc("ana", "ben", "cy")
	hiddenFollow(t, s, "ana", "ben")
	hiddenFollow(t, s, "ana", "cy")
	now := hiddenT0 + 20*hiddenDay
	hiddenPub(t, s, "ancient", "cy", now-7*hiddenDay-1)
	hiddenPub(t, s, "edge", "ben", now-7*hiddenDay)
	hiddenPub(t, s, "recent", "ben", now-hiddenDay)
	hiddenIDs(t, "long absence", hiddenCatchUp(t, s, "ana", hiddenT0, now, 5), []string{"recent", "edge"})
	hiddenIDs(t, "since at the edge", hiddenCatchUp(t, s, "ana", now-7*hiddenDay, now, 5), []string{"recent"})
}

func Test_p2_catch_up_empty_and_errors(t *testing.T) {
	s, since := hiddenAway(t)
	late := since + 10*hiddenH
	hiddenIDs(t, "nothing new", hiddenCatchUp(t, s, "ana", late, late+hiddenH, 5), []string{})
	hiddenIDs(t, "cy follows nobody", hiddenCatchUp(t, s, "cy", since, late, 5), []string{})
	_, err := s.CatchUp("ghost", since, late, 5)
	hiddenErr(t, "ghost", err, ErrUnknownUser)
	_, err = s.CatchUp("ana", since, late, 0)
	hiddenErr(t, "limit 0", err, ErrBadLimit)
}

// ---------------------------------------------------------------- phase 3

func hiddenRush(t *testing.T) (*Service, []string, int64) {
	t.Helper()
	rng := rand.New(rand.NewSource(42))
	s := New()
	users := make([]string, 2000)
	for i := range users {
		users[i] = fmt.Sprintf("u%04d", i)
		s.AddUser(users[i])
	}
	n := 0
	for day := int64(0); day < 30; day++ {
		for _, u := range users {
			pid := fmt.Sprintf("p%06d", n)
			n++
			hiddenPub(t, s, pid, u, hiddenT0+day*hiddenDay+rng.Int63n(hiddenDay))
			for _, i := range rng.Perm(len(users))[:rng.Intn(6)] {
				hiddenLike(t, s, pid, users[i])
			}
		}
	}
	viewers := users[:40]
	for _, v := range viewers {
		for _, i := range rng.Perm(len(users) - 40)[:150] {
			hiddenFollow(t, s, v, users[40+i])
		}
	}
	return s, viewers, hiddenT0 + 30*hiddenDay
}

func Test_p3_morning_peak_home_feeds(t *testing.T) {
	s, viewers, now := hiddenRush(t)
	start := time.Now()
	pages := make([]Page, len(viewers))
	for i, v := range viewers {
		p, err := s.HomeFeed(v, now, 20, "")
		if err != nil {
			t.Fatal(err)
		}
		pages[i] = p
	}
	elapsed := time.Since(start)
	for i, p := range pages {
		hiddenEq(t, fmt.Sprintf("page %d size", i), len(p.PostIDs), 20)
	}
	hiddenIDs(t, "page 0", pages[0].PostIDs[:3], []string{"p059492", "p058840", "p059824"})
	hiddenEq(t, "page 21", pages[21].PostIDs[7], "p059485")
	hiddenEq(t, "page 39", pages[39].PostIDs[19], "p058641")
	if elapsed > 500*time.Millisecond {
		t.Fatalf("40 home feeds took %v, budget 500ms", elapsed)
	}
}

func Test_p3_morning_peak_catch_up(t *testing.T) {
	s, viewers, now := hiddenRush(t)
	start := time.Now()
	lists := make([][]string, len(viewers))
	for i, v := range viewers {
		ids, err := s.CatchUp(v, now-2*hiddenDay, now, 5)
		if err != nil {
			t.Fatal(err)
		}
		lists[i] = ids
	}
	elapsed := time.Since(start)
	hiddenIDs(t, "list 0", lists[0], []string{"p059492", "p058840", "p059824", "p058310", "p058176"})
	hiddenIDs(t, "list 17", lists[17], []string{"p058631", "p059459", "p058983", "p058338", "p058148"})
	hiddenIDs(t, "list 39", lists[39], []string{"p058497", "p059071", "p058322", "p059263", "p058614"})
	if elapsed > 500*time.Millisecond {
		t.Fatalf("40 catch-ups took %v, budget 500ms", elapsed)
	}
}
