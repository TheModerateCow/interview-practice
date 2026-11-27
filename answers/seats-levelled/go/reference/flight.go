// Package flight is the in-memory core of an airline's business-class desk for one multi-stop flight:
// bookings, the upgrade waitlist, busiest-leg queries and the best possible upgrade plan.
package flight

import "container/heap"

const far = 1 << 62

type entry struct {
	passenger string
	seq       int
}

type trip struct {
	board, alight int
	status        string
	seq           int // order of the request, for the waitlist
}

// Flight: stops 0..n; leg k flies stop k -> k+1 and has seats[k] seats.
type Flight struct {
	n, size, h int
	seats      []int
	// Segment tree over legs. Node p covers a run of legs: hi[p] is the most seats taken on one of them,
	// lo[p] the fewest free seats. add[p] (internal nodes) counts seats taken on every leg under p that
	// p's children don't show yet.
	hi, lo, add []int
	trips       map[string]*trip
	waiting     []entry // waitlist, oldest request first; entries of cancelled requests are skipped
	seq         int
}

// NewFlight returns a flight whose leg k has seats[k] seats.
func NewFlight(seats []int) *Flight {
	n := len(seats)
	size, h := 1, 0
	for size < n {
		size, h = size*2, h+1
	}
	f := &Flight{n: n, size: size, h: h, seats: append([]int(nil), seats...),
		hi: make([]int, 2*size), lo: make([]int, 2*size), add: make([]int, size), trips: map[string]*trip{}}
	copy(f.lo[size:], seats)
	for p := size - 1; p > 0; p-- {
		f.hi[p] = max(f.hi[2*p], f.hi[2*p+1])
		f.lo[p] = min(f.lo[2*p], f.lo[2*p+1])
	}
	return f
}

// ---- segment tree: add seats taken on legs [l, r), read (most taken, fewest free) on legs [l, r)

func (f *Flight) apply(p, v int) {
	f.hi[p] += v
	f.lo[p] -= v
	if p < f.size {
		f.add[p] += v
	}
}

func (f *Flight) pull(p int) {
	for p > 1 {
		p >>= 1
		a := f.add[p]
		f.hi[p] = max(f.hi[2*p], f.hi[2*p+1]) + a
		f.lo[p] = min(f.lo[2*p], f.lo[2*p+1]) - a
	}
}

func (f *Flight) push(p int) {
	for s := f.h; s > 0; s-- {
		i := p >> s
		if a := f.add[i]; a != 0 {
			f.apply(2*i, a)
			f.apply(2*i+1, a)
			f.add[i] = 0
		}
	}
}

func (f *Flight) take(l, r, v int) {
	l += f.size
	r += f.size
	l0, r0 := l, r-1
	for l < r {
		if l&1 == 1 {
			f.apply(l, v)
			l++
		}
		if r&1 == 1 {
			r--
			f.apply(r, v)
		}
		l >>= 1
		r >>= 1
	}
	f.pull(l0)
	f.pull(r0)
}

func (f *Flight) rng(l, r int) (int, int) {
	l += f.size
	r += f.size
	f.push(l)
	f.push(r - 1)
	hi, lo := 0, far
	for l < r {
		if l&1 == 1 {
			hi = max(hi, f.hi[l])
			lo = min(lo, f.lo[l])
			l++
		}
		if r&1 == 1 {
			r--
			hi = max(hi, f.hi[r])
			lo = min(lo, f.lo[r])
		}
		l >>= 1
		r >>= 1
	}
	return hi, lo
}

func (f *Flight) valid(board, alight int) bool { return 0 <= board && board < alight && alight <= f.n }

func (f *Flight) fits(board, alight int) bool {
	_, lo := f.rng(board, alight)
	return lo >= 1
}

// ---- level 1

// Book gives the passenger a seat on every leg from board to alight.
func (f *Flight) Book(passenger string, board int, alight int) bool {
	if _, ok := f.trips[passenger]; ok || !f.valid(board, alight) || !f.fits(board, alight) {
		return false
	}
	f.take(board, alight, 1)
	f.trips[passenger] = &trip{board: board, alight: alight, status: "booked"}
	return true
}

// Cancel frees the passenger's seat, or takes them off the waitlist.
func (f *Flight) Cancel(passenger string) bool {
	t, ok := f.trips[passenger]
	if !ok {
		return false
	}
	delete(f.trips, passenger)
	if t.status != "waitlisted" {
		f.take(t.board, t.alight, -1)
	}
	return true
}

// FreeSeats returns how many seats on the leg nobody holds.
func (f *Flight) FreeSeats(leg int) (int, bool) {
	if leg < 0 || leg >= f.n {
		return 0, false
	}
	_, lo := f.rng(leg, leg+1)
	return lo, true
}

// ---- level 2

// RequestUpgrade seats the passenger if the whole trip fits, otherwise puts them on the waitlist.
func (f *Flight) RequestUpgrade(passenger string, board int, alight int) string {
	if _, ok := f.trips[passenger]; ok || !f.valid(board, alight) {
		return ""
	}
	f.seq++
	if f.fits(board, alight) {
		f.take(board, alight, 1)
		f.trips[passenger] = &trip{board: board, alight: alight, status: "upgraded", seq: f.seq}
		return "upgraded"
	}
	f.trips[passenger] = &trip{board: board, alight: alight, status: "waitlisted", seq: f.seq}
	f.waiting = append(f.waiting, entry{passenger, f.seq})
	return "waitlisted"
}

// Status is "booked", "upgraded", "waitlisted" or "".
func (f *Flight) Status(passenger string) string {
	if t, ok := f.trips[passenger]; ok {
		return t.status
	}
	return ""
}

// Promote seats waitlisted passengers whose trip now fits, oldest request first.
func (f *Flight) Promote() []string {
	done := []string{}
	keep := f.waiting[:0]
	for _, e := range f.waiting {
		t, ok := f.trips[e.passenger]
		if !ok || t.status != "waitlisted" || t.seq != e.seq {
			continue // that request was cancelled
		}
		if f.fits(t.board, t.alight) {
			f.take(t.board, t.alight, 1)
			t.status = "upgraded"
			done = append(done, e.passenger)
			continue
		}
		keep = append(keep, e)
	}
	f.waiting = keep
	return done
}

// ---- level 3

// Busiest returns the most seats held on one leg from fromStop to toStop.
func (f *Flight) Busiest(fromStop int, toStop int) (int, bool) {
	if !f.valid(fromStop, toStop) {
		return 0, false
	}
	hi, _ := f.rng(fromStop, toStop)
	return hi, true
}

// ---- level 4

type maxHeap []int

func (h maxHeap) Len() int           { return len(h) }
func (h maxHeap) Less(i, j int) bool { return h[i] > h[j] }
func (h maxHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *maxHeap) Push(x any)        { *h = append(*h, x.(int)) }
func (h *maxHeap) Pop() any {
	old := *h
	x := old[len(old)-1]
	*h = old[:len(old)-1]
	return x
}

// BestPlan returns how many current upgrade requests could all be seated together.
func (f *Flight) BestPlan() int {
	n := f.n
	diff := make([]int, n+1)
	starts := make([][]int, n)
	m := 0
	for _, t := range f.trips {
		if t.status == "booked" {
			diff[t.board]++
			diff[t.alight]--
		} else {
			starts[t.board] = append(starts[t.board], t.alight)
			m++
		}
	}
	// Sweep the legs left to right, taking each request as its boarding leg comes up. When a leg is over its
	// seats, drop the taken request that alights latest: it blocks the most legs still to come.
	ends := make([]int, n+1)
	taken := &maxHeap{}
	active, paid, dropped := 0, 0, 0
	for k := 0; k < n; k++ {
		paid += diff[k]
		active -= ends[k]
		for _, alight := range starts[k] {
			heap.Push(taken, alight)
			ends[alight]++
			active++
		}
		for active > f.seats[k]-paid {
			alight := heap.Pop(taken).(int)
			ends[alight]--
			active--
			dropped++
		}
	}
	return m - dropped
}
