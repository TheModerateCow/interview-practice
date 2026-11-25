package jobqueue

import "sort"

// Package jobqueue is the background job queue of the web platform. Producers
// enqueue jobs into named queues ("emails", "webhooks", ...); workers lease the
// next job, then ack it or report a failure. A lease is a visibility timeout: if
// it runs out without an ack the job goes back to READY for another worker.
// Failed jobs are retried with exponential backoff until they run out of
// attempts, then they move to the dead-letter queue, where an operator can
// redrive them.
//
// Not safe for concurrent use: the API layer serialises calls. Times are
// caller-supplied Unix seconds. Every call that takes now moves the queue clock
// forward first (starting due jobs and taking back expired leases); now may
// never go backwards.

// Options are the queue's settings.
type Options struct {
	Visibility     int64 // default lease length, seconds
	BaseDelay      int64 // backoff after the first failed attempt, seconds; doubles each attempt
	MaxDelay       int64 // cap on the backoff, seconds
	MaxAttempts    int   // default attempts per job
	IdempotencyTTL int64 // how long an idempotency key keeps returning its first job, seconds
}

// DefaultOptions are the settings New uses.
func DefaultOptions() Options {
	return Options{Visibility: 30, BaseDelay: 10, MaxDelay: 600, MaxAttempts: 3, IdempotencyTTL: 3600}
}

// EnqueueOptions are the optional parts of Enqueue; the zero value means none.
type EnqueueOptions struct {
	Priority    int    // higher runs first
	RunAt       int64  // don't start before this time (0 = no delay)
	MaxAttempts int    // overrides the default (0 = default)
	Key         string // idempotency key, scoped to the named queue ("" = none)
}

// JobQueue is the queue API.
type JobQueue struct {
	st  *store
	opt Options
}

// New returns an empty queue with the default options.
func New() *JobQueue {
	return &JobQueue{st: newStore(), opt: DefaultOptions()}
}

// NewWith returns an empty queue with the given options, or an Invalid error if they make no sense.
func NewWith(o Options) (*JobQueue, error) {
	if o.Visibility <= 0 || o.BaseDelay < 0 || o.MaxDelay < o.BaseDelay || o.MaxAttempts < 1 || o.IdempotencyTTL < 0 {
		return nil, newErr(Invalid, "bad options")
	}
	return &JobQueue{st: newStore(), opt: o}, nil
}

// Enqueue adds a job and returns its id. If o.Key was used in this queue less
// than IdempotencyTTL seconds ago, nothing is added and the first job's id is returned.
func (q *JobQueue) Enqueue(queue, payload string, now int64, o EnqueueOptions) (string, error) {
	if err := advance(q.st, now); err != nil {
		return "", err
	}
	if queue == "" {
		return "", newErr(Invalid, "empty queue name")
	}
	limit := q.opt.MaxAttempts
	if o.MaxAttempts != 0 {
		limit = o.MaxAttempts
	}
	if limit < 1 {
		return "", newErr(Invalid, "max attempts must be at least 1")
	}
	if o.Key != "" {
		if first := q.st.findKey(queue, o.Key, now); first != "" {
			return first, nil
		}
	}
	j := q.st.add(queue, payload, o.Priority, limit, now)
	if o.Key != "" {
		q.st.rememberKey(queue, o.Key, j.ID, now+q.opt.IdempotencyTTL)
	}
	if o.RunAt > now {
		q.st.schedule(j, o.RunAt)
	} else {
		q.st.makeReady(j, now)
	}
	return j.ID, nil
}

// Lease leases the next READY job of a queue for the default visibility, or
// returns nil if there is none.
func (q *JobQueue) Lease(queue string, now int64) (*Lease, error) {
	return q.LeaseFor(queue, now, q.opt.Visibility)
}

// LeaseFor is Lease with an explicit lease length in seconds.
func (q *JobQueue) LeaseFor(queue string, now, visibility int64) (*Lease, error) {
	if visibility <= 0 {
		return nil, newErr(Invalid, "visibility must be positive")
	}
	if err := advance(q.st, now); err != nil {
		return nil, err
	}
	j := q.st.nextReady(queue)
	if j == nil {
		return nil, nil
	}
	q.st.lease(j, now+visibility)
	return &Lease{j.ID, j.leaseToken, j.Payload, j.Attempts, j.leaseUntil}, nil
}

// Ack says the job is done: it is dropped and counted as completed.
func (q *JobQueue) Ack(jobID, token string, now int64) error {
	j, err := q.held(jobID, token, now)
	if err != nil {
		return err
	}
	q.st.drop(j, Completed)
	return nil
}

// Fail says the attempt failed: the job is retried after the backoff, or
// dead-lettered if it is out of attempts.
func (q *JobQueue) Fail(jobID, token, errMsg string, now int64) error {
	j, err := q.held(jobID, token, now)
	if err != nil {
		return err
	}
	recordFailure(q.st, q.opt.BaseDelay, q.opt.MaxDelay, j, errMsg, now)
	return nil
}

// Extend is the heartbeat: the lease now runs until now+seconds.
func (q *JobQueue) Extend(jobID, token string, seconds, now int64) error {
	if seconds <= 0 {
		return newErr(Invalid, "seconds must be positive")
	}
	j, err := q.held(jobID, token, now)
	if err != nil {
		return err
	}
	q.st.setDeadline(j, now+seconds)
	return nil
}

// Cancel cancels a job that hasn't started (SCHEDULED or READY).
func (q *JobQueue) Cancel(jobID string, now int64) error {
	if err := advance(q.st, now); err != nil {
		return err
	}
	j, err := q.find(jobID)
	if err != nil {
		return err
	}
	if j.Status != Scheduled && j.Status != Ready {
		return newErr(Invalid, "%s is %s", jobID, j.Status)
	}
	q.st.drop(j, Cancelled)
	return nil
}

// Redrive moves a dead job back to READY with a fresh set of attempts.
func (q *JobQueue) Redrive(jobID string, now int64) error {
	if err := advance(q.st, now); err != nil {
		return err
	}
	j, err := q.find(jobID)
	if err != nil {
		return err
	}
	if j.Status != Dead {
		return newErr(Invalid, "%s is %s", jobID, j.Status)
	}
	q.st.makeReady(j, now)
	return nil
}

// DeadLetters is the dead-letter queue of a named queue, oldest death first.
func (q *JobQueue) DeadLetters(queue string) []Job {
	var dead []*Job
	for _, j := range q.st.jobsIn(queue) {
		if j.Status == Dead {
			dead = append(dead, j)
		}
	}
	sort.Slice(dead, func(a, b int) bool {
		if dead[a].deadAt != dead[b].deadAt {
			return dead[a].deadAt < dead[b].deadAt
		}
		return dead[a].seq < dead[b].seq
	})
	out := make([]Job, len(dead))
	for i, j := range dead {
		out[i] = *j
	}
	return out
}

// Job returns a copy of a live job; ok is false if there is none with that id.
func (q *JobQueue) Job(jobID string) (Job, bool) {
	if j := q.st.get(jobID); j != nil {
		return *j, true
	}
	return Job{}, false
}

// Stats is the stats of a named queue at time now (an unknown queue has all zeros).
func (q *JobQueue) Stats(queue string, now int64) (Stats, error) {
	return statsOf(q.st, queue, now)
}

// held returns the job, if token is its current lease.
func (q *JobQueue) held(jobID, token string, now int64) (*Job, error) {
	if err := advance(q.st, now); err != nil {
		return nil, err
	}
	j, err := q.find(jobID)
	if err != nil {
		return nil, err
	}
	if j.Status != Leased || j.leaseToken != token {
		return nil, newErr(LeaseLost, "%s: %s is not the current lease", jobID, token)
	}
	return j, nil
}

func (q *JobQueue) find(jobID string) (*Job, error) {
	if j := q.st.get(jobID); j != nil {
		return j, nil
	}
	return nil, newErr(NotFound, "no live job %s", jobID)
}
