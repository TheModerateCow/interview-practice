package jobqueue

import "container/heap"

// The transitions driven by time and failures: the clock sweep that starts
// scheduled jobs and takes back leases that ran out, retry backoff, and the
// dead-letter queue.

// advance moves the queue clock to now and fires every timer due by then, in
// time order.
//
// Scheduled jobs whose time has come become READY as of their run time. A
// lease that ran out without an ack is taken back as of its deadline: the job
// is READY again, or DEAD if that lease was its last attempt.
func advance(st *store, now int64) error {
	if now < st.clock {
		return newErr(Backdated, "now %d is before the queue clock %d", now, st.clock)
	}
	st.clock = now
	for len(st.timers) > 0 && st.timers[0].at <= now {
		t := heap.Pop(&st.timers).(timer)
		j := st.get(t.jobID)
		if j == nil {
			continue
		}
		if !t.isLease {
			if j.Status == Scheduled && j.availableAt <= now {
				st.makeReady(j, j.availableAt)
			}
		} else if j.Status == Leased {
			expireLease(st, j)
		}
	}
	return nil
}

func expireLease(st *store, j *Job) {
	j.LastError = "lease expired"
	if j.Attempts >= j.MaxAttempts {
		deadLetter(j, j.leaseUntil)
	} else {
		st.makeReady(j, j.leaseUntil)
	}
}

// retryDelay is the backoff before the retry that follows attempt number
// attempts: base, 2x base, 4x base ... capped at maxDelay.
func retryDelay(baseDelay, maxDelay int64, attempts int) int64 {
	d := baseDelay
	for i := 1; i < attempts; i++ {
		if d >= maxDelay {
			break
		}
		d *= 2
	}
	return min(d, maxDelay)
}

// recordFailure: a worker reported failure. Retry after the backoff, or
// dead-letter the job if it is out of attempts.
func recordFailure(st *store, baseDelay, maxDelay int64, j *Job, errMsg string, now int64) {
	j.LastError = errMsg
	if j.Attempts >= j.MaxAttempts {
		deadLetter(j, now)
	} else {
		st.schedule(j, now+retryDelay(baseDelay, maxDelay, j.Attempts))
	}
}

func deadLetter(j *Job, at int64) {
	j.Status = Dead
	j.deadAt = at
}
