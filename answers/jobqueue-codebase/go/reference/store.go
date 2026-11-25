package jobqueue

import (
	"container/heap"
	"fmt"
)

// timer is a wake-up: a run time comes, or a lease deadline passes.
type timer struct {
	at      int64
	seq     int
	jobID   string
	isLease bool
}

type timerHeap []timer

func (h timerHeap) Len() int { return len(h) }
func (h timerHeap) Less(i, j int) bool {
	if h[i].at != h[j].at {
		return h[i].at < h[j].at
	}
	return h[i].seq < h[j].seq
}
func (h timerHeap) Swap(i, j int) { h[i], h[j] = h[j], h[i] }
func (h *timerHeap) Push(x any)   { *h = append(*h, x.(timer)) }
func (h *timerHeap) Pop() any {
	old := *h
	x := old[len(old)-1]
	*h = old[:len(old)-1]
	return x
}

type keyID struct{ queue, key string }

type keyEntry struct {
	jobID string
	until int64
}

// store is the in-memory state: every live job (scheduled, ready, leased or
// dead), a ready heap per named queue, one timer heap for run times and lease
// deadlines, and the idempotency keys. Completed and cancelled jobs are
// dropped; only a per-queue count of completions is kept.
type store struct {
	// clock is the queue clock: the latest now any call has passed.
	clock  int64
	timers timerHeap

	jobSeq, timerSeq, leaseSeq int
	jobs                       map[string]*Job
	byQueue                    map[string]map[string]*Job
	ready                      map[string]*readyQueue
	keys                       map[keyID]keyEntry
	completed                  map[string]int
}

func newStore() *store {
	return &store{
		jobs:      map[string]*Job{},
		byQueue:   map[string]map[string]*Job{},
		ready:     map[string]*readyQueue{},
		keys:      map[keyID]keyEntry{},
		completed: map[string]int{},
	}
}

func (st *store) add(queue, payload string, priority, maxAttempts int, now int64) *Job {
	st.jobSeq++
	j := &Job{ID: fmt.Sprintf("job-%d", st.jobSeq), Queue: queue, Payload: payload, Priority: priority,
		MaxAttempts: maxAttempts, Status: Scheduled, seq: st.jobSeq, enqueuedAt: now}
	st.jobs[j.ID] = j
	if st.byQueue[queue] == nil {
		st.byQueue[queue] = map[string]*Job{}
	}
	st.byQueue[queue][j.ID] = j
	return j
}

func (st *store) get(id string) *Job { return st.jobs[id] }

// jobsIn returns the live jobs of a queue, in no particular order.
func (st *store) jobsIn(queue string) []*Job {
	out := make([]*Job, 0, len(st.byQueue[queue]))
	for _, j := range st.byQueue[queue] {
		out = append(out, j)
	}
	return out
}

// completedIn is the lifetime number of acked jobs in a queue.
func (st *store) completedIn(queue string) int { return st.completed[queue] }

// drop ends a job for good (Completed or Cancelled) and forgets it.
func (st *store) drop(j *Job, end Status) {
	j.Status = end
	delete(st.jobs, j.ID)
	delete(st.byQueue[j.Queue], j.ID)
	if end == Completed {
		st.completed[j.Queue]++
	}
}

// makeReady marks a job READY as of at and queues it for leasing.
func (st *store) makeReady(j *Job, at int64) {
	j.Status = Ready
	j.readyAt = at
	q := st.ready[j.Queue]
	if q == nil {
		q = &readyQueue{}
		st.ready[j.Queue] = q
	}
	q.add(j)
}

// nextReady removes and returns the next job to lease from a queue, or nil.
func (st *store) nextReady(queue string) *Job {
	if q := st.ready[queue]; q != nil {
		return q.poll()
	}
	return nil
}

// schedule parks a job until at.
func (st *store) schedule(j *Job, at int64) {
	j.Status = Scheduled
	j.availableAt = at
	st.pushTimer(at, j.ID, false)
}

// lease hands a job out under a fresh lease token until until.
func (st *store) lease(j *Job, until int64) {
	j.Status = Leased
	j.Attempts++
	st.leaseSeq++
	j.leaseToken = fmt.Sprintf("lease-%d", st.leaseSeq)
	st.setDeadline(j, until)
}

// setDeadline moves the current lease's deadline.
func (st *store) setDeadline(j *Job, until int64) {
	j.leaseUntil = until
	st.pushTimer(until, j.ID, true)
}

// findKey is the job an idempotency key still points at in this queue, or ""
// once the key has lapsed.
func (st *store) findKey(queue, key string, now int64) string {
	if k, ok := st.keys[keyOf(queue, key)]; ok && now < k.until {
		return k.jobID
	}
	return ""
}

func (st *store) rememberKey(queue, key, jobID string, until int64) {
	st.keys[keyOf(queue, key)] = keyEntry{jobID, until}
}

func (st *store) pushTimer(at int64, jobID string, lease bool) {
	st.timerSeq++
	heap.Push(&st.timers, timer{at, st.timerSeq, jobID, lease})
}

func keyOf(queue, key string) keyID {
	return keyID{queue, key}
}
