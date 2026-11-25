package inventory

import "container/heap"

// holdQueue is a min-heap of reservations ordered by when their hold runs out, then by
// placement order. Released and committed holds stay in it until their time comes.
type holdQueue []*Reservation

func (q holdQueue) Len() int { return len(q) }
func (q holdQueue) Less(i, j int) bool {
	if q[i].ExpiresAt != q[j].ExpiresAt {
		return q[i].ExpiresAt < q[j].ExpiresAt
	}
	return q[i].seq < q[j].seq
}
func (q holdQueue) Swap(i, j int) { q[i], q[j] = q[j], q[i] }
func (q *holdQueue) Push(x any)   { *q = append(*q, x.(*Reservation)) }
func (q *holdQueue) Pop() any {
	old := *q
	r := old[len(old)-1]
	*q = old[:len(old)-1]
	return r
}

// track registers a newly placed reservation for expiry.
func (s *store) track(r *Reservation) { heap.Push(&s.holds, r) }

// expire ends every active reservation whose hold has run out by now (ExpiresAt <= now)
// and returns its stock to available.
func (s *store) expire(now int64) {
	for len(s.holds) > 0 && s.holds[0].ExpiresAt <= now {
		r := heap.Pop(&s.holds).(*Reservation)
		if r.Status == Active {
			s.endHold(r, Expired, r.ExpiresAt)
		}
	}
}
