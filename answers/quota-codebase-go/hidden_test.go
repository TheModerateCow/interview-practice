package quota

import (
	"errors"
	"fmt"
	"strconv"
	"testing"
	"time"
)

// The app compiles one phase's tests at a time: keep every import used outside them.
var (
	_ = errors.Is
	_ = fmt.Sprint
	_ = strconv.Itoa
	_ = time.Second
)

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenErr(t *testing.T, what string, got, want error) {
	t.Helper()
	if !errors.Is(got, want) {
		t.Fatalf("%s: got error %v want %v", what, got, want)
	}
}

// hiddenService returns a service with plans basic (10/min, burst 4),
// strict (10/min, no burst) and pro (50/min, burst 20).
func hiddenService(t *testing.T) *Service {
	t.Helper()
	s := New()
	for _, p := range []Plan{
		{Name: "basic", Limit: 10, Window: 60, Burst: 4},
		{Name: "strict", Limit: 10, Window: 60, Burst: 0},
		{Name: "pro", Limit: 50, Window: 60, Burst: 20},
	} {
		if err := s.AddPlan(p); err != nil {
			t.Fatalf("AddPlan(%s): %v", p.Name, err)
		}
	}
	return s
}

func hiddenKey(t *testing.T, s *Service, id, org, plan string) {
	t.Helper()
	if err := s.IssueKey(id, org, plan); err != nil {
		t.Fatalf("IssueKey(%s): %v", id, err)
	}
}

// hiddenAllow runs one request and renders the decision as "ok R" or "no R +S".
func hiddenAllow(t *testing.T, s *Service, id string, now int64, cost int) string {
	t.Helper()
	d, err := s.Allow(id, now, cost)
	if err != nil {
		t.Fatalf("Allow(%s, %d, %d): %v", id, now, cost, err)
	}
	if d.Allowed {
		return fmt.Sprintf("ok %d", d.Remaining)
	}
	return fmt.Sprintf("no %d +%d", d.Remaining, d.RetryAfter)
}

func hiddenUsage(t *testing.T, s *Service, id string, now int64) string {
	t.Helper()
	used, limit, err := s.Usage(id, now)
	if err != nil {
		t.Fatalf("Usage(%s, %d): %v", id, now, err)
	}
	return fmt.Sprintf("%d/%d", used, limit)
}

func hiddenLines(lines []UsageLine) string {
	var out []string
	for _, l := range lines {
		out = append(out, fmt.Sprintf("%s:%s:%d/%d/%d", l.KeyID, l.Plan, l.Requests, l.Units, l.Denied))
	}
	return fmt.Sprint(out)
}

func hiddenReport(t *testing.T, s *Service, org string, from, to int64) string {
	t.Helper()
	lines, err := s.Report(org, from, to)
	if err != nil {
		t.Fatalf("Report(%s, %d, %d): %v", org, from, to, err)
	}
	return hiddenLines(lines)
}

// ---------------------------------------------------------------- phase 1

func Test_p1_allow_until_limit(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "strict")
	hiddenEq(t, "first", hiddenAllow(t, s, "k1", 0, 4), "ok 6")
	hiddenEq(t, "second", hiddenAllow(t, s, "k1", 10, 6), "ok 0")
	hiddenEq(t, "over the limit", hiddenAllow(t, s, "k1", 45, 1), "no 0 +15")
	hiddenEq(t, "usage", hiddenUsage(t, s, "k1", 59), "10/10")
	hiddenEq(t, "next window", hiddenAllow(t, s, "k1", 60, 10), "ok 0")
}

func Test_p1_window_edges(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "strict")
	hiddenEq(t, "last second of a window", hiddenAllow(t, s, "k1", 119, 10), "ok 0")
	hiddenEq(t, "first second of the next", hiddenAllow(t, s, "k1", 120, 10), "ok 0")
	hiddenEq(t, "denied at the window start", hiddenAllow(t, s, "k1", 120, 1), "no 0 +60")
	hiddenEq(t, "usage at 179", hiddenUsage(t, s, "k1", 179), "10/10")
	hiddenEq(t, "usage at 180", hiddenUsage(t, s, "k1", 180), "0/10")
}

func Test_p1_burst_from_quiet_window(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "basic")
	hiddenEq(t, "idle before: full burst", hiddenUsage(t, s, "k1", 0), "0/14")
	hiddenEq(t, "spend 7", hiddenAllow(t, s, "k1", 5, 7), "ok 7")
	hiddenEq(t, "3 unused roll over", hiddenUsage(t, s, "k1", 60), "0/13")
	hiddenEq(t, "only the window before counts", hiddenUsage(t, s, "k1", 120), "0/14")
}

func Test_p1_no_burst_after_burst_window(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "basic")
	hiddenEq(t, "spend limit + burst", hiddenAllow(t, s, "k1", 10, 14), "ok 0")
	hiddenEq(t, "next window has the plain limit", hiddenUsage(t, s, "k1", 60), "0/10")
	hiddenEq(t, "spend it all", hiddenAllow(t, s, "k1", 61, 10), "ok 0")
	hiddenEq(t, "then denied", hiddenAllow(t, s, "k1", 62, 1), "no 0 +58")
	hiddenEq(t, "window after", hiddenUsage(t, s, "k1", 120), "0/10")
}

func Test_p1_pro_burst_window(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "pro")
	hiddenEq(t, "first window", hiddenAllow(t, s, "k1", 0, 65), "ok 5")
	hiddenEq(t, "second window", hiddenAllow(t, s, "k1", 60, 50), "ok 0")
	hiddenEq(t, "second window full", hiddenAllow(t, s, "k1", 61, 1), "no 0 +59")
}

func Test_p1_denied_request_spends_nothing(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "strict")
	hiddenEq(t, "spend 8", hiddenAllow(t, s, "k1", 0, 8), "ok 2")
	hiddenEq(t, "batch call too big", hiddenAllow(t, s, "k1", 1, 5), "no 2 +59")
	hiddenEq(t, "small call still fits", hiddenAllow(t, s, "k1", 2, 2), "ok 0")
	hiddenEq(t, "usage", hiddenUsage(t, s, "k1", 3), "10/10")
}

func Test_p1_denied_requests_keep_burst(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "pro")
	hiddenEq(t, "spend 40", hiddenAllow(t, s, "k1", 0, 40), "ok 30")
	for i := int64(1); i <= 5; i++ {
		hiddenEq(t, "retry storm", hiddenAllow(t, s, "k1", i, 50), "no 30 +"+strconv.Itoa(int(60-i)))
	}
	hiddenEq(t, "10 unused roll over", hiddenUsage(t, s, "k1", 60), "0/60")
}

func Test_p1_errors(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "basic")
	_, err := s.Allow("nope", 0, 1)
	hiddenErr(t, "unknown key", err, ErrUnknownKey)
	_, err = s.Allow("k1", 0, 0)
	hiddenErr(t, "zero cost", err, ErrBadCost)
	hiddenErr(t, "duplicate key", s.IssueKey("k1", "org-b", "pro"), ErrDuplicateKey)
	hiddenErr(t, "key on unknown plan", s.IssueKey("k2", "org-a", "gold"), ErrUnknownPlan)
	hiddenErr(t, "duplicate plan", s.AddPlan(Plan{Name: "pro", Limit: 1, Window: 1}), ErrDuplicatePlan)
	hiddenErr(t, "zero limit", s.AddPlan(Plan{Name: "x", Limit: 0, Window: 60}), ErrInvalidPlan)
	hiddenErr(t, "zero window", s.AddPlan(Plan{Name: "x", Limit: 5, Window: 0}), ErrInvalidPlan)
	hiddenErr(t, "negative burst", s.AddPlan(Plan{Name: "x", Limit: 5, Window: 60, Burst: -1}), ErrInvalidPlan)
	hiddenErr(t, "ChangePlan unknown plan", s.ChangePlan("k1", "gold"), ErrUnknownPlan)
	hiddenErr(t, "ChangePlan unknown key", s.ChangePlan("nope", "pro"), ErrUnknownKey)
	hiddenErr(t, "Revoke unknown key", s.Revoke("nope"), ErrUnknownKey)
	k, _ := s.Key("k1")
	hiddenEq(t, "k1 after failed calls", k, Key{ID: "k1", Org: "org-a", Plan: "basic"})
}

func Test_p1_revoked_key_rejected(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "pro")
	hiddenEq(t, "before revoke", hiddenAllow(t, s, "k1", 0, 1), "ok 69")
	hiddenEq(t, "revoke", s.Revoke("k1"), nil)
	_, err := s.Allow("k1", 1, 1)
	hiddenErr(t, "after revoke", err, ErrRevoked)
	hiddenEq(t, "usage of a revoked key", hiddenUsage(t, s, "k1", 2), "1/70")
}

func Test_p1_revoked_key_stays_revoked_after_plan_change(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "leaked", "org-a", "basic")
	s.Revoke("leaked")
	hiddenEq(t, "plan change", s.ChangePlan("leaked", "pro"), nil)
	_, err := s.Allow("leaked", 100, 1)
	hiddenErr(t, "revoked key after upgrade", err, ErrRevoked)
	k, _ := s.Key("leaked")
	hiddenEq(t, "key record", k, Key{ID: "leaked", Org: "org-a", Plan: "pro", Revoked: true})
}

func Test_p1_plan_change_applies_to_next_request(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "strict")
	hiddenEq(t, "on strict", hiddenAllow(t, s, "k1", 0, 10), "ok 0")
	hiddenEq(t, "strict is full", hiddenAllow(t, s, "k1", 1, 5), "no 0 +59")
	hiddenEq(t, "upgrade", s.ChangePlan("k1", "pro"), nil)
	hiddenEq(t, "on pro, same window", hiddenAllow(t, s, "k1", 2, 5), "ok 55")
	hiddenEq(t, "usage on pro", hiddenUsage(t, s, "k1", 3), "15/70")
}

func Test_p1_keys_are_independent(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "a", "org-a", "strict")
	hiddenKey(t, s, "b", "org-a", "strict")
	hiddenEq(t, "a spends all", hiddenAllow(t, s, "a", 0, 10), "ok 0")
	hiddenEq(t, "b untouched", hiddenAllow(t, s, "b", 1, 3), "ok 7")
	hiddenEq(t, "a denied", hiddenAllow(t, s, "a", 2, 1), "no 0 +58")
	hiddenEq(t, "b usage", hiddenUsage(t, s, "b", 2), "3/10")
}

// ---------------------------------------------------------------- phase 2

func Test_p2_report_counts(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "strict")
	s.Allow("k1", 0, 4)
	s.Allow("k1", 10, 3)
	s.Allow("k1", 20, 2)
	s.Allow("k1", 30, 5)
	s.Allow("k1", 70, 6)
	hiddenEq(t, "report", hiddenReport(t, s, "org-a", 0, 120), "[k1:strict:4/15/1]")
}

func Test_p2_report_order(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "mid", "org-a", "pro")
	hiddenKey(t, s, "big", "org-a", "pro")
	hiddenKey(t, s, "tie-b", "org-a", "basic")
	hiddenKey(t, s, "tie-a", "org-a", "strict")
	s.Allow("mid", 0, 20)
	s.Allow("big", 0, 30)
	s.Allow("big", 1, 1)
	s.Allow("tie-b", 2, 5)
	s.Allow("tie-a", 3, 2)
	s.Allow("tie-a", 4, 3)
	hiddenEq(t, "most units first, ties by key id", hiddenReport(t, s, "org-a", 0, 60),
		"[big:pro:2/31/0 mid:pro:1/20/0 tie-a:strict:2/5/0 tie-b:basic:1/5/0]")
}

func Test_p2_report_range_is_half_open(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "pro")
	for _, at := range []int64{99, 100, 150, 199, 200} {
		s.Allow("k1", at, 1)
	}
	hiddenEq(t, "[100, 200)", hiddenReport(t, s, "org-a", 100, 200), "[k1:pro:3/3/0]")
	hiddenEq(t, "[200, 201)", hiddenReport(t, s, "org-a", 200, 201), "[k1:pro:1/1/0]")
	hiddenEq(t, "[0, 99)", hiddenReport(t, s, "org-a", 0, 99), "[]")
}

func Test_p2_report_only_active_keys_of_the_org(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "a1", "org-a", "pro")
	hiddenKey(t, s, "a2", "org-a", "pro")
	hiddenKey(t, s, "b1", "org-b", "pro")
	s.Allow("a1", 10, 2)
	s.Allow("a2", 500, 2)
	s.Allow("b1", 10, 9)
	hiddenEq(t, "org-a, first minute", hiddenReport(t, s, "org-a", 0, 60), "[a1:pro:1/2/0]")
	hiddenEq(t, "org-b", hiddenReport(t, s, "org-b", 0, 1000), "[b1:pro:1/9/0]")
}

func Test_p2_report_revoked_and_denied_only_keys(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "old", "org-a", "basic")
	hiddenKey(t, s, "noisy", "org-a", "strict")
	s.Allow("old", 0, 3)
	s.Revoke("old")
	s.Allow("old", 1, 3)
	s.Allow("noisy", 2, 11)
	s.Allow("noisy", 3, 12)
	s.ChangePlan("noisy", "pro")
	hiddenEq(t, "revoked key still billed; denied-only key listed with its current plan",
		hiddenReport(t, s, "org-a", 0, 60), "[old:basic:1/3/0 noisy:pro:0/0/2]")
}

func Test_p2_report_empty_and_bad_range(t *testing.T) {
	s := hiddenService(t)
	hiddenKey(t, s, "k1", "org-a", "pro")
	s.Allow("k1", 10, 1)
	got, err := s.Report("org-z", 0, 100)
	hiddenEq(t, "unknown org error", err, nil)
	if got == nil || len(got) != 0 {
		t.Fatalf("unknown org: got %#v want an empty slice", got)
	}
	_, err = s.Report("org-a", 50, 50)
	hiddenErr(t, "empty range", err, ErrBadRange)
	_, err = s.Report("org-a", 60, 0)
	hiddenErr(t, "backwards range", err, ErrBadRange)
}

// ---------------------------------------------------------------- phase 3

// hiddenBusyDay replays a busy day for one customer: n keys on "standard"
// sending one request a second, plus a "hog" key on "metered" that hammers
// its limit, for the given number of seconds. It returns allowed and denied
// counts and the sum of Remaining over the allowed decisions.
func hiddenBusyDay(t *testing.T, s *Service, n int, seconds int64) (allowed, denied, remaining int) {
	t.Helper()
	s.AddPlan(Plan{Name: "standard", Limit: 600, Window: 60, Burst: 100})
	s.AddPlan(Plan{Name: "metered", Limit: 100, Window: 60, Burst: 0})
	var ids []string
	for i := 0; i < n; i++ {
		ids = append(ids, "k"+strconv.Itoa(i))
		hiddenKey(t, s, ids[i], "org-big", "standard")
	}
	hiddenKey(t, s, "hog", "org-big", "metered")
	seed := uint32(2024)
	rnd := func(m int) int { seed = seed*1664525 + 1013904223; return int(seed>>8) % m }
	for now := int64(0); now < seconds; now++ {
		for _, id := range ids {
			d, err := s.Allow(id, now, 1+rnd(9))
			if err != nil {
				t.Fatalf("Allow(%s, %d): %v", id, now, err)
			}
			if d.Allowed {
				allowed++
				remaining += d.Remaining
			} else {
				denied++
			}
		}
		d, _ := s.Allow("hog", now, 7)
		if d.Allowed {
			allowed++
			remaining += d.Remaining
		} else {
			denied++
		}
	}
	return
}

func Test_p3_busy_day_traffic(t *testing.T) {
	s := New()
	start := time.Now()
	allowed, denied, remaining := hiddenBusyDay(t, s, 1, 80000)
	elapsed := time.Since(start)
	hiddenEq(t, "allowed", allowed, 98676)
	hiddenEq(t, "denied", denied, 61324)
	hiddenEq(t, "sum of Remaining over allowed calls", remaining, 44693184)
	hiddenEq(t, "k0 usage", hiddenUsage(t, s, "k0", 79999), "104/700")
	if elapsed > 500*time.Millisecond {
		t.Fatalf("160,000 Allow calls took %v, budget 500ms", elapsed)
	}
}

func Test_p3_hourly_reports(t *testing.T) {
	s := New()
	start := time.Now()
	hiddenBusyDay(t, s, 1, 57600)
	var hours []string
	for h := int64(0); h < 16; h++ {
		hours = append(hours, hiddenReport(t, s, "org-big", h*3600, (h+1)*3600))
	}
	day := hiddenReport(t, s, "org-big", 0, 57600)
	elapsed := time.Since(start)
	hiddenEq(t, "hour 0", hours[0], "[k0:standard:3600/18030/0 hog:metered:840/5880/2760]")
	hiddenEq(t, "hour 7", hours[7], "[k0:standard:3600/17858/0 hog:metered:840/5880/2760]")
	hiddenEq(t, "hour 15", hours[15], "[k0:standard:3600/17969/0 hog:metered:840/5880/2760]")
	hiddenEq(t, "whole day", day, "[k0:standard:57600/287856/0 hog:metered:13440/94080/44160]")
	if elapsed > 500*time.Millisecond {
		t.Fatalf("115,200 Allow calls plus 17 reports took %v, budget 500ms", elapsed)
	}
}
