package jobqueue

import "fmt"

// Stats is a point-in-time view of one named queue, for the ops dashboard and
// the worker autoscaler.
type Stats struct {
	Ready          int    // jobs a lease would hand out now
	Scheduled      int    // jobs waiting for their first run time
	Retrying       int    // jobs waiting out a retry backoff
	InFlight       int    // jobs under a lease
	Dead           int    // jobs in the dead-letter queue
	Completed      int    // jobs acked in this queue, ever
	OldestReadyAge int64  // how long the longest-waiting READY job has been ready, 0 if none
	NextRunAt      *int64 // the earliest time a scheduled or retrying job becomes ready, nil if none
}

func (s Stats) String() string {
	next := "null"
	if s.NextRunAt != nil {
		next = fmt.Sprint(*s.NextRunAt)
	}
	return fmt.Sprintf("Stats[ready=%d, scheduled=%d, retrying=%d, inFlight=%d, dead=%d, completed=%d, oldestReadyAge=%d, nextRunAt=%s]",
		s.Ready, s.Scheduled, s.Retrying, s.InFlight, s.Dead, s.Completed, s.OldestReadyAge, next)
}

// statsOf computes the stats of queue at time now. See problem.md for the rules.
func statsOf(st *store, queue string, now int64) (Stats, error) {
	panic("not implemented")
}
