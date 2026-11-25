package jobqueue

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
	"testing"
	"time"
)

// The app compiles one phase's tests at a time: keep every import used outside them.
var (
	_ = errors.Is
	_ = fmt.Sprint
	_ = strconv.Itoa
	_ = strings.Join
	_ = time.Second
)

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

// hiddenCode is "ok" for nil, else the error's code.
func hiddenCode(err error) string {
	if err == nil {
		return "ok"
	}
	var qe *QueueError
	if errors.As(err, &qe) {
		return string(qe.Code)
	}
	return "other: " + err.Error()
}

func hiddenQueue(t *testing.T, visibility, baseDelay, maxDelay int64, maxAttempts int) *JobQueue {
	t.Helper()
	q, err := NewWith(Options{visibility, baseDelay, maxDelay, maxAttempts, 3600})
	if err != nil {
		t.Fatalf("NewWith: %v", err)
	}
	return q
}

func hiddenEnqueue(t *testing.T, q *JobQueue, queue, payload string, now int64, o EnqueueOptions) string {
	t.Helper()
	id, err := q.Enqueue(queue, payload, now, o)
	if err != nil {
		t.Fatalf("Enqueue(%s, %s, %d): %v", queue, payload, now, err)
	}
	return id
}

func hiddenTake(t *testing.T, q *JobQueue, queue string, now int64) *Lease {
	t.Helper()
	l, err := q.Lease(queue, now)
	if err != nil {
		t.Fatalf("Lease(%s, %d): %v", queue, now, err)
	}
	return l
}

func hiddenLease(l *Lease) string {
	if l == nil {
		return "empty"
	}
	return fmt.Sprintf("%s#%d@%d", l.JobID, l.Attempt, l.Until)
}

func hiddenMust(t *testing.T, what string, err error) {
	t.Helper()
	if err != nil {
		t.Fatalf("%s: %v", what, err)
	}
}

// hiddenDrain leases and acks every job that is ready at now; it returns their payloads in lease order.
func hiddenDrain(t *testing.T, q *JobQueue, queue string, now int64) string {
	t.Helper()
	var out []string
	for l := hiddenTake(t, q, queue, now); l != nil; l = hiddenTake(t, q, queue, now) {
		out = append(out, l.Payload)
		hiddenMust(t, "Ack", q.Ack(l.JobID, l.Token, now))
	}
	return strings.Join(out, ",")
}

func hiddenStatus(q *JobQueue, id string) string {
	j, ok := q.Job(id)
	if !ok {
		return "gone"
	}
	return fmt.Sprintf("%s/%d", j.Status, j.Attempts)
}

func hiddenStats(t *testing.T, q *JobQueue, queue string, now int64) string {
	t.Helper()
	s, err := q.Stats(queue, now)
	if err != nil {
		t.Fatalf("Stats(%s, %d): %v", queue, now, err)
	}
	return s.String()
}

// ---------------------------------------------------------------- phase 1

func Test_p1_heartbeat_keeps_the_lease(t *testing.T) {
	q := New()
	id := hiddenEnqueue(t, q, "payments", "capture-981", 100, EnqueueOptions{})
	a := hiddenTake(t, q, "payments", 100)
	hiddenMust(t, "Extend", q.Extend(id, a.Token, 60, 120))
	hiddenEq(t, "lease at 135", hiddenLease(hiddenTake(t, q, "payments", 135)), "empty")
	hiddenMust(t, "Extend", q.Extend(id, a.Token, 30, 170))
	hiddenEq(t, "lease at 185", hiddenLease(hiddenTake(t, q, "payments", 185)), "empty")
	hiddenEq(t, "ack", hiddenCode(q.Ack(id, a.Token, 195)), "ok")
	hiddenEq(t, "status", hiddenStatus(q, id), "gone")
}

func Test_p1_quick_retry_keeps_the_new_lease(t *testing.T) {
	q := hiddenQueue(t, 30, 5, 600, 3)
	id := hiddenEnqueue(t, q, "payments", "capture-982", 0, EnqueueOptions{})
	a := hiddenTake(t, q, "payments", 0)
	hiddenMust(t, "Fail", q.Fail(id, a.Token, "gateway 503", 2))
	b := hiddenTake(t, q, "payments", 10)
	hiddenEq(t, "second lease", hiddenLease(b), id+"#2@40")
	hiddenEq(t, "lease at 35", hiddenLease(hiddenTake(t, q, "payments", 35)), "empty")
	hiddenEq(t, "ack", hiddenCode(q.Ack(id, b.Token, 38)), "ok")
}

func Test_p1_expired_lease_moves_to_the_next_worker(t *testing.T) {
	q := New()
	id := hiddenEnqueue(t, q, "webhooks", "deliver-7", 0, EnqueueOptions{})
	a := hiddenTake(t, q, "webhooks", 0)
	hiddenEq(t, "lease at 29", hiddenLease(hiddenTake(t, q, "webhooks", 29)), "empty")
	b := hiddenTake(t, q, "webhooks", 30)
	hiddenEq(t, "second lease", hiddenLease(b), id+"#2@60")
	hiddenEq(t, "stale ack", hiddenCode(q.Ack(id, a.Token, 31)), "LEASE_LOST")
	hiddenEq(t, "stale extend", hiddenCode(q.Extend(id, a.Token, 30, 31)), "LEASE_LOST")
	hiddenEq(t, "stale fail", hiddenCode(q.Fail(id, a.Token, "late", 31)), "LEASE_LOST")
	hiddenMust(t, "Extend", q.Extend(id, b.Token, 10, 40))
	hiddenEq(t, "lease at 49", hiddenLease(hiddenTake(t, q, "webhooks", 49)), "empty")
	c := hiddenTake(t, q, "webhooks", 50)
	hiddenEq(t, "third lease", hiddenLease(c), id+"#3@80")
	hiddenEq(t, "stale ack b", hiddenCode(q.Ack(id, b.Token, 51)), "LEASE_LOST")
	hiddenEq(t, "ack c", hiddenCode(q.Ack(id, c.Token, 52)), "ok")
}

func Test_p1_crashing_job_is_dead_lettered(t *testing.T) {
	q := hiddenQueue(t, 30, 10, 600, 2)
	a := hiddenEnqueue(t, q, "imports", "csv-1", 0, EnqueueOptions{})
	hiddenEq(t, "lease 0", hiddenLease(hiddenTake(t, q, "imports", 0)), a+"#1@30")
	hiddenEq(t, "lease 29", hiddenLease(hiddenTake(t, q, "imports", 29)), "empty")
	hiddenEq(t, "lease 30", hiddenLease(hiddenTake(t, q, "imports", 30)), a+"#2@60")
	hiddenEq(t, "lease 60", hiddenLease(hiddenTake(t, q, "imports", 60)), "empty")
	hiddenEq(t, "status", hiddenStatus(q, a), "DEAD/2")
	ja, _ := q.Job(a)
	hiddenEq(t, "lastError", ja.LastError, "lease expired")
	b := hiddenEnqueue(t, q, "imports", "csv-2", 61, EnqueueOptions{})
	hiddenMust(t, "Fail", q.Fail(b, hiddenTake(t, q, "imports", 61).Token, "parse error", 62))
	hiddenMust(t, "Fail", q.Fail(b, hiddenTake(t, q, "imports", 72).Token, "parse error", 73))
	var dead []string
	for _, j := range q.DeadLetters("imports") {
		dead = append(dead, j.String())
	}
	hiddenEq(t, "dead letters", strings.Join(dead, "|"),
		a+" DEAD attempts=2 lastError=lease expired|"+b+" DEAD attempts=2 lastError=parse error")
	hiddenEq(t, "lease 500", hiddenLease(hiddenTake(t, q, "imports", 500)), "empty")
}

func Test_p1_redriven_job_gets_fresh_attempts(t *testing.T) {
	q := hiddenQueue(t, 30, 10, 600, 2)
	id := hiddenEnqueue(t, q, "exports", "report-31", 0, EnqueueOptions{})
	hiddenMust(t, "Fail", q.Fail(id, hiddenTake(t, q, "exports", 0).Token, "disk full", 1))
	hiddenMust(t, "Fail", q.Fail(id, hiddenTake(t, q, "exports", 11).Token, "disk full", 12))
	hiddenEq(t, "status", hiddenStatus(q, id), "DEAD/2")
	hiddenMust(t, "Redrive", q.Redrive(id, 100))
	hiddenEq(t, "dead letters", len(q.DeadLetters("exports")), 0)
	l := hiddenTake(t, q, "exports", 100)
	hiddenEq(t, "lease", hiddenLease(l), id+"#1@130")
	hiddenMust(t, "Fail", q.Fail(id, l.Token, "disk full", 101))
	hiddenEq(t, "status after fail", hiddenStatus(q, id), "SCHEDULED/1")
	hiddenEq(t, "retry lease", hiddenLease(hiddenTake(t, q, "exports", 111)), id+"#2@141")
}

func Test_p1_idempotency_keys_belong_to_their_queue(t *testing.T) {
	q := New()
	e1 := hiddenEnqueue(t, q, "emails", "welcome-42", 100, EnqueueOptions{Key: "signup-42"})
	b1 := hiddenEnqueue(t, q, "billing", "trial-42", 100, EnqueueOptions{Key: "signup-42"})
	if e1 == b1 {
		t.Fatalf("billing reused the emails job %s", e1)
	}
	hiddenEq(t, "emails again", hiddenEnqueue(t, q, "emails", "welcome-42", 105, EnqueueOptions{Key: "signup-42"}), e1)
	hiddenEq(t, "billing again", hiddenEnqueue(t, q, "billing", "trial-42", 105, EnqueueOptions{Key: "signup-42"}), b1)
	hiddenEq(t, "billing drain", hiddenDrain(t, q, "billing", 110), "trial-42")
	hiddenEq(t, "emails drain", hiddenDrain(t, q, "emails", 110), "welcome-42")
}

func Test_p1_idempotency_window(t *testing.T) {
	q := New()
	k := EnqueueOptions{Key: "evt-1"}
	a := hiddenEnqueue(t, q, "webhooks", "evt-1", 100, k)
	l := hiddenTake(t, q, "webhooks", 200)
	hiddenMust(t, "Ack", q.Ack(a, l.Token, 201))
	hiddenEq(t, "inside the window", hiddenEnqueue(t, q, "webhooks", "evt-1", 3699, k), a)
	hiddenEq(t, "drain inside", hiddenDrain(t, q, "webhooks", 3699), "")
	b := hiddenEnqueue(t, q, "webhooks", "evt-1", 3700, k)
	if a == b {
		t.Fatal("key should have lapsed at 3700")
	}
	hiddenEq(t, "again", hiddenEnqueue(t, q, "webhooks", "evt-1", 3800, k), b)
	hiddenEq(t, "drain after", hiddenDrain(t, q, "webhooks", 3800), "evt-1")
}

func Test_p1_retry_backoff_doubles_up_to_the_cap(t *testing.T) {
	q := hiddenQueue(t, 30, 10, 25, 5)
	id := hiddenEnqueue(t, q, "reports", "weekly", 0, EnqueueOptions{})
	var seen []string
	for _, p := range [][2]int64{{0, 0}, {9, 10}, {29, 30}, {54, 55}, {79, 80}} {
		before, at := p[0], p[1]
		if before != at {
			seen = append(seen, hiddenLease(hiddenTake(t, q, "reports", before)))
		}
		l := hiddenTake(t, q, "reports", at)
		seen = append(seen, hiddenLease(l))
		hiddenMust(t, "Fail", q.Fail(id, l.Token, "timeout", at))
	}
	hiddenEq(t, "leases", strings.Join(seen, ","),
		"job-1#1@30,empty,job-1#2@40,empty,job-1#3@60,empty,job-1#4@85,empty,job-1#5@110")
	hiddenEq(t, "status", hiddenStatus(q, id), "DEAD/5")
	j, _ := q.Job(id)
	hiddenEq(t, "lastError", j.LastError, "timeout")
}

func Test_p1_lease_order(t *testing.T) {
	q := New()
	hiddenEnqueue(t, q, "jobs", "a", 0, EnqueueOptions{RunAt: 50})
	hiddenEnqueue(t, q, "jobs", "b", 10, EnqueueOptions{})
	hiddenEnqueue(t, q, "jobs", "c", 20, EnqueueOptions{Priority: 5})
	hiddenEnqueue(t, q, "jobs", "d", 30, EnqueueOptions{Priority: 5, RunAt: 40})
	hiddenEnqueue(t, q, "jobs", "e", 30, EnqueueOptions{})
	hiddenEnqueue(t, q, "jobs", "f", 30, EnqueueOptions{Priority: -1})
	hiddenEq(t, "first drain", hiddenDrain(t, q, "jobs", 30), "c,b,e,f")
	hiddenEnqueue(t, q, "jobs", "g", 45, EnqueueOptions{})
	hiddenEnqueue(t, q, "jobs", "h", 45, EnqueueOptions{RunAt: 5})
	hiddenEq(t, "second drain", hiddenDrain(t, q, "jobs", 60), "d,g,h,a")
}

func Test_p1_cancel_errors_and_clock(t *testing.T) {
	q := New()
	a := hiddenEnqueue(t, q, "jobs", "a", 10, EnqueueOptions{})
	b := hiddenEnqueue(t, q, "jobs", "b", 10, EnqueueOptions{RunAt: 100})
	c := hiddenEnqueue(t, q, "jobs", "c", 10, EnqueueOptions{})
	hiddenMust(t, "Cancel a", q.Cancel(a, 11))
	hiddenMust(t, "Cancel b", q.Cancel(b, 12))
	l := hiddenTake(t, q, "jobs", 13)
	hiddenEq(t, "leased", l.JobID, c)
	hiddenEq(t, "cancel leased", hiddenCode(q.Cancel(c, 14)), "INVALID")
	hiddenEq(t, "cancel gone", hiddenCode(q.Cancel(a, 14)), "NOT_FOUND")
	hiddenEq(t, "ack bad token", hiddenCode(q.Ack(c, "lease-999", 14)), "LEASE_LOST")
	hiddenEq(t, "redrive leased", hiddenCode(q.Redrive(c, 14)), "INVALID")
	_, err := q.Enqueue("", "x", 14, EnqueueOptions{})
	hiddenEq(t, "empty queue name", hiddenCode(err), "INVALID")
	_, err = q.Enqueue("jobs", "x", 14, EnqueueOptions{MaxAttempts: -1})
	hiddenEq(t, "negative attempts", hiddenCode(err), "INVALID")
	_, err = q.LeaseFor("jobs", 14, 0)
	hiddenEq(t, "zero visibility", hiddenCode(err), "INVALID")
	hiddenEq(t, "zero extend", hiddenCode(q.Extend(c, l.Token, 0, 14)), "INVALID")
	_, err = q.Lease("jobs", 13)
	hiddenEq(t, "backdated", hiddenCode(err), "BACKDATED")
	hiddenEq(t, "ack", hiddenCode(q.Ack(c, l.Token, 15)), "ok")
	hiddenEq(t, "ack again", hiddenCode(q.Ack(c, l.Token, 15)), "NOT_FOUND")
	hiddenEq(t, "drain", hiddenDrain(t, q, "jobs", 200), "")
	hiddenEq(t, "status", hiddenStatus(q, a), "gone")
}

func Test_p1_bad_options(t *testing.T) {
	for _, o := range []Options{
		{0, 10, 600, 3, 3600},
		{30, -1, 600, 3, 3600},
		{30, 10, 5, 3, 3600},
		{30, 10, 600, 0, 3600},
		{30, 10, 600, 3, -1},
	} {
		_, err := NewWith(o)
		hiddenEq(t, fmt.Sprintf("NewWith(%+v)", o), hiddenCode(err), "INVALID")
	}
}

// ---------------------------------------------------------------- phase 2

func Test_p2_counts_jobs_by_state(t *testing.T) {
	q := hiddenQueue(t, 30, 100, 600, 2)
	hiddenEnqueue(t, q, "emails", "a", 10, EnqueueOptions{})
	hiddenEnqueue(t, q, "emails", "b", 12, EnqueueOptions{})
	hiddenEnqueue(t, q, "emails", "c", 12, EnqueueOptions{RunAt: 500})
	hiddenEnqueue(t, q, "emails", "d", 13, EnqueueOptions{Priority: 9})
	e := hiddenEnqueue(t, q, "emails", "e", 14, EnqueueOptions{Priority: 8})
	f := hiddenEnqueue(t, q, "emails", "f", 15, EnqueueOptions{Priority: 7, MaxAttempts: 1})
	g := hiddenEnqueue(t, q, "emails", "g", 16, EnqueueOptions{Priority: 6})
	h := hiddenEnqueue(t, q, "emails", "h", 17, EnqueueOptions{})
	hiddenEnqueue(t, q, "billing", "x", 17, EnqueueOptions{})
	hiddenTake(t, q, "emails", 20)
	le := hiddenTake(t, q, "emails", 20)
	lf := hiddenTake(t, q, "emails", 20)
	lg := hiddenTake(t, q, "emails", 20)
	hiddenMust(t, "Fail e", q.Fail(e, le.Token, "500", 21))
	hiddenMust(t, "Fail f", q.Fail(f, lf.Token, "400", 21))
	hiddenMust(t, "Ack g", q.Ack(g, lg.Token, 22))
	hiddenMust(t, "Cancel h", q.Cancel(h, 23))
	hiddenEq(t, "emails", hiddenStats(t, q, "emails", 40),
		"Stats[ready=2, scheduled=1, retrying=1, inFlight=1, dead=1, completed=1, oldestReadyAge=30, nextRunAt=121]")
	hiddenEq(t, "billing", hiddenStats(t, q, "billing", 40),
		"Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=23, nextRunAt=null]")
}

func Test_p2_moves_the_clock_first(t *testing.T) {
	q := New()
	hiddenEnqueue(t, q, "webhooks", "a", 0, EnqueueOptions{})
	hiddenEnqueue(t, q, "webhooks", "b", 0, EnqueueOptions{RunAt: 50})
	hiddenTake(t, q, "webhooks", 5)
	hiddenEq(t, "at 20", hiddenStats(t, q, "webhooks", 20),
		"Stats[ready=0, scheduled=1, retrying=0, inFlight=1, dead=0, completed=0, oldestReadyAge=0, nextRunAt=50]")
	hiddenEq(t, "at 60", hiddenStats(t, q, "webhooks", 60),
		"Stats[ready=2, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=25, nextRunAt=null]")
	_, err := q.Stats("webhooks", 59)
	hiddenEq(t, "backdated", hiddenCode(err), "BACKDATED")
}

func Test_p2_age_counts_from_when_the_job_became_ready(t *testing.T) {
	q := hiddenQueue(t, 30, 40, 600, 3)
	id := hiddenEnqueue(t, q, "reports", "monthly", 0, EnqueueOptions{RunAt: 100})
	hiddenEq(t, "at 150", hiddenStats(t, q, "reports", 150),
		"Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=50, nextRunAt=null]")
	hiddenMust(t, "Fail", q.Fail(id, hiddenTake(t, q, "reports", 150).Token, "timeout", 160))
	hiddenEq(t, "at 199", hiddenStats(t, q, "reports", 199),
		"Stats[ready=0, scheduled=0, retrying=1, inFlight=0, dead=0, completed=0, oldestReadyAge=0, nextRunAt=200]")
	hiddenEq(t, "at 230", hiddenStats(t, q, "reports", 230),
		"Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=30, nextRunAt=null]")
}

func Test_p2_dead_letters_and_redrive(t *testing.T) {
	q := hiddenQueue(t, 30, 10, 600, 1)
	a := hiddenEnqueue(t, q, "payments", "a", 0, EnqueueOptions{})
	hiddenEnqueue(t, q, "payments", "b", 0, EnqueueOptions{})
	la := hiddenTake(t, q, "payments", 0)
	hiddenTake(t, q, "payments", 0)
	hiddenMust(t, "Fail", q.Fail(a, la.Token, "card declined", 5))
	hiddenEq(t, "at 40", hiddenStats(t, q, "payments", 40),
		"Stats[ready=0, scheduled=0, retrying=0, inFlight=0, dead=2, completed=0, oldestReadyAge=0, nextRunAt=null]")
	hiddenMust(t, "Redrive", q.Redrive(a, 50))
	hiddenEq(t, "at 70", hiddenStats(t, q, "payments", 70),
		"Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=1, completed=0, oldestReadyAge=20, nextRunAt=null]")
}

func Test_p2_completed_per_queue_and_unknown_queue(t *testing.T) {
	q := New()
	for i := 0; i < 3; i++ {
		hiddenEnqueue(t, q, "emails", fmt.Sprintf("e%d", i), int64(i), EnqueueOptions{Key: fmt.Sprintf("k%d", i)})
	}
	hiddenEnqueue(t, q, "emails", "e0-again", 3, EnqueueOptions{Key: "k0"})
	hiddenEnqueue(t, q, "billing", "b0", 3, EnqueueOptions{})
	for i := 0; i < 2; i++ {
		l := hiddenTake(t, q, "emails", 10)
		hiddenMust(t, "Ack", q.Ack(l.JobID, l.Token, 10))
	}
	l := hiddenTake(t, q, "billing", 12)
	hiddenMust(t, "Ack", q.Ack(l.JobID, l.Token, 12))
	hiddenEq(t, "emails", hiddenStats(t, q, "emails", 20),
		"Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=2, oldestReadyAge=18, nextRunAt=null]")
	hiddenEq(t, "billing", hiddenStats(t, q, "billing", 20),
		"Stats[ready=0, scheduled=0, retrying=0, inFlight=0, dead=0, completed=1, oldestReadyAge=0, nextRunAt=null]")
	hiddenEq(t, "nope", hiddenStats(t, q, "nope", 20),
		"Stats[ready=0, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=0, nextRunAt=null]")
}

// ---------------------------------------------------------------- phase 3

func Test_p3_backlog_after_an_outage(t *testing.T) {
	const budget = 500 * time.Millisecond
	q := hiddenQueue(t, 30, 30, 600, 3)
	const backlog, steps = 16_000, 22_400
	// A partner endpoint was down for two hours: webhook events piled up, a few of them
	// delivered twice, some deferred by ten minutes, a quarter flagged urgent.
	for i := 0; i < backlog; i++ {
		o := EnqueueOptions{Key: fmt.Sprintf("evt-%d", i)}
		if i%25 == 24 {
			o.Key = fmt.Sprintf("evt-%d", i-1)
		}
		if i%4 == 0 {
			o.Priority = 1
		}
		if i%10 == 3 {
			o.RunAt = int64(i/10 + 600)
		}
		hiddenEnqueue(t, q, "webhooks", fmt.Sprintf("evt-%d", i), int64(i/10), o)
	}
	// It's back. Workers drain the backlog while live traffic keeps arriving.
	start := time.Now()
	var acked, failed, abandoned, cancelled, refused, idle int
	var checksum uint64 // reduced mod 2^61 by the mask, so the wrap-around of uint64 is harmless
	for s := 0; s < steps; s++ {
		now := int64(10_000 + s/20)
		if s%3 == 0 {
			o := EnqueueOptions{}
			if s%9 == 0 {
				o.Priority = 2
			}
			hiddenEnqueue(t, q, "webhooks", fmt.Sprintf("live-%d", s), now, o)
		}
		if s%97 == 0 {
			victim := fmt.Sprintf("job-%d", 1+(s*31)%backlog)
			if err := q.Cancel(victim, now); err == nil {
				cancelled++
			} else {
				refused++
			}
		}
		l := hiddenTake(t, q, "webhooks", now)
		if l == nil {
			idle++
		} else {
			n, _ := strconv.Atoi(l.JobID[4:])
			switch {
			case n%41 == 0:
				abandoned++
			case (n+l.Attempt)%7 == 0:
				hiddenMust(t, "Fail", q.Fail(l.JobID, l.Token, "502", now))
				failed++
			default:
				hiddenMust(t, "Ack", q.Ack(l.JobID, l.Token, now))
				acked++
			}
		}
		if s%500 == 499 {
			st, err := q.Stats("webhooks", now)
			hiddenMust(t, "Stats", err)
			checksum = (checksum*31 + uint64(st.Ready) + 7*uint64(st.Retrying) + 13*uint64(st.InFlight) +
				17*uint64(st.Dead) + uint64(st.OldestReadyAge)) & (1<<61 - 1)
			if time.Since(start) > 10*time.Second {
				t.Fatal("far too slow: giving up after 10 s (budget 0.5 s)")
			}
		}
	}
	elapsed := time.Since(start)
	final, err := q.Stats("webhooks", int64(10_000+steps/20+1000))
	hiddenMust(t, "Stats", err)
	got := fmt.Sprintf("acked=%d failed=%d abandoned=%d cancelled=%d refused=%d idle=%d checksum=%d %s",
		acked, failed, abandoned, cancelled, refused, idle, checksum, final)
	want := "acked=18632 failed=2840 abandoned=928 cancelled=113 refused=118 idle=0 checksum=1297322307213073607 " +
		"Stats[ready=3932, scheduled=0, retrying=0, inFlight=0, dead=150, completed=18632, oldestReadyAge=1529, nextRunAt=null]"
	hiddenEq(t, "outcome", got, want)
	if elapsed > budget {
		t.Fatalf("draining took %v, budget %v", elapsed, budget)
	}
}
