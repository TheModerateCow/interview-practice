package jobqueue

type readyQueue struct{ jobs []*Job }

func order(a, b *Job) bool {
	if a.Priority != b.Priority {
		return a.Priority > b.Priority
	}
	if a.readyAt != b.readyAt {
		return a.readyAt < b.readyAt
	}
	return a.seq < b.seq
}

func (q *readyQueue) add(j *Job) { q.jobs = append(q.jobs, j) }

// poll removes and returns the best job that is still READY, or nil.
func (q *readyQueue) poll() *Job {
	live := q.jobs[:0:0]
	for _, j := range q.jobs {
		if j.Status == Ready {
			live = append(live, j)
		}
	}
	q.jobs = live
	if len(live) == 0 {
		return nil
	}
	type key struct {
		prio  int
		ready int64
		seq   int
	}
	ranked := make([]key, len(live))
	for i, j := range live {
		ranked[i] = key{-j.Priority, j.readyAt, j.seq}
	}
	bi := 0
	for i, k := range ranked {
		b := ranked[bi]
		if k.prio < b.prio || k.prio == b.prio && (k.ready < b.ready || k.ready == b.ready && k.seq < b.seq) {
			bi = i
		}
	}
	best := live[bi]
	q.jobs = append(live[:bi], live[bi+1:]...)
	return best
}
