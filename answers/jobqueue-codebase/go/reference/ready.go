package jobqueue

import "container/heap"

// readyQueue holds the jobs of one named queue that can be leased now.
type readyQueue struct{ h readyHeap }

// order reports whether a is leased before b: higher priority, then the job
// that has been ready longest, then the job enqueued first.
func order(a, b *Job) bool {
	if a.Priority != b.Priority {
		return a.Priority > b.Priority
	}
	if a.readyAt != b.readyAt {
		return a.readyAt < b.readyAt
	}
	return a.seq < b.seq
}

func (q *readyQueue) add(j *Job) { heap.Push(&q.h, j) }

// poll removes and returns the best job that is still READY, or nil. A job
// cancelled while it waits stays in the heap until it reaches the top, and is
// dropped then.
func (q *readyQueue) poll() *Job {
	for q.h.Len() > 0 {
		j := heap.Pop(&q.h).(*Job)
		if j.Status == Ready {
			return j
		}
	}
	return nil
}

type readyHeap []*Job

func (h readyHeap) Len() int           { return len(h) }
func (h readyHeap) Less(i, j int) bool { return order(h[i], h[j]) }
func (h readyHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *readyHeap) Push(x any)        { *h = append(*h, x.(*Job)) }
func (h *readyHeap) Pop() any {
	old := *h
	n := len(old)
	x := old[n-1]
	old[n-1] = nil
	*h = old[:n-1]
	return x
}
