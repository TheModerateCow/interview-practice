package jobqueue

import "fmt"

// Code says why a call failed. Callers branch on it (see QueueError).
type Code string

const (
	// NotFound: no live job has that id (it never existed, or it completed or was cancelled).
	NotFound Code = "NOT_FOUND"
	// LeaseLost: the caller's lease is no longer the job's current lease: it ran out, or someone else holds it now.
	LeaseLost Code = "LEASE_LOST"
	// Invalid: a bad argument, or an operation that doesn't apply to the job's state.
	Invalid Code = "INVALID"
	// Backdated: a timestamp older than the queue clock.
	Backdated Code = "BACKDATED"
)

// QueueError is every error the job queue reports.
type QueueError struct {
	Code Code
	Msg  string
}

func (e *QueueError) Error() string { return string(e.Code) + ": " + e.Msg }

func newErr(c Code, format string, a ...any) error {
	return &QueueError{c, fmt.Sprintf(format, a...)}
}

// Status is where a job is in its life:
// SCHEDULED -> READY -> LEASED -> (COMPLETED | SCHEDULED for a retry | DEAD).
type Status string

const (
	Scheduled Status = "SCHEDULED"
	Ready     Status = "READY"
	Leased    Status = "LEASED"
	Completed Status = "COMPLETED"
	Dead      Status = "DEAD"
	Cancelled Status = "CANCELLED"
)

// Lease is what a worker gets from JobQueue.Lease: the token to ack, fail or extend with.
type Lease struct {
	JobID   string
	Token   string
	Payload string
	Attempt int
	Until   int64
}

// Job is one unit of background work and where it is in its life. The queue owns
// these values; callers only ever see copies (see JobQueue.Job).
type Job struct {
	ID          string
	Queue       string
	Payload     string
	Priority    int
	MaxAttempts int
	Status      Status
	// Attempts is the number of leases handed out so far; a lease that runs
	// out without an ack counts as an attempt.
	Attempts  int
	LastError string

	seq        int // enqueue order
	enqueuedAt int64
	// availableAt is when a SCHEDULED job may run (its run time, or the end of its retry backoff).
	availableAt int64
	// readyAt is when the job last became READY. Jobs of equal priority are leased oldest-ready first.
	readyAt    int64
	leaseUntil int64
	leaseToken string
	deadAt     int64
}

func (j Job) String() string {
	err := ""
	if j.LastError != "" {
		err = " lastError=" + j.LastError
	}
	return fmt.Sprintf("%s %s attempts=%d%s", j.ID, j.Status, j.Attempts, err)
}
