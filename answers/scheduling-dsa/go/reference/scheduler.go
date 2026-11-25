package scheduler

import "sort"

const day = 1440

// Attendee: Offset is minutes east of UTC (local = UTC + Offset). WorkStart and WorkEnd are local minutes of
// the day, [WorkStart, WorkEnd), the same every day. Busy holds UTC blocks {start, end}, [start, end), in any
// order; they may overlap.
type Attendee struct {
	Offset    int
	WorkStart int
	WorkEnd   int
	Busy      [][]int
}

// EarliestQuorumSlot returns the earliest UTC start t with t + duration <= days * 1440 such that at least
// quorum attendees are free for the whole of [t, t + duration); -1 if there is none.
func EarliestQuorumSlot(attendees []Attendee, days int, duration int, quorum int) int {
	horizon := days * day
	type event struct{ t, delta int }
	var events []event
	for _, a := range attendees {
		for _, f := range freeIntervals(a, horizon) {
			s, e := f[0], f[1]
			// a meeting fits for this attendee iff it starts in [s, e - duration]
			if e-s >= duration {
				events = append(events, event{s, 1}, event{e - duration + 1, -1})
			}
		}
	}
	sort.Slice(events, func(i, j int) bool { return events[i].t < events[j].t })
	count := 0
	for i := 0; i < len(events); {
		t := events[i].t
		for ; i < len(events) && events[i].t == t; i++ {
			count += events[i].delta
		}
		if count >= quorum {
			return t
		}
	}
	return -1
}

// freeIntervals returns the disjoint, non-touching free intervals in UTC, sorted, inside [0, horizon).
func freeIntervals(a Attendee, horizon int) [][2]int {
	var work [][2]int
	for d := -1; d <= horizon/day; d++ {
		base := d*day - a.Offset
		s := max(0, base+a.WorkStart)
		e := min(horizon, base+a.WorkEnd)
		if s >= e {
			continue
		}
		if n := len(work); n > 0 && s <= work[n-1][1] {
			work[n-1][1] = max(work[n-1][1], e)
		} else {
			work = append(work, [2]int{s, e})
		}
	}
	busy := append([][]int(nil), a.Busy...)
	sort.Slice(busy, func(i, j int) bool { return busy[i][0] < busy[j][0] })
	var free [][2]int
	lo := 0
	for _, w := range work {
		ws, we := w[0], w[1]
		for lo < len(busy) && busy[lo][1] <= ws {
			lo++
		}
		cur := ws
		for i := lo; i < len(busy) && busy[i][0] < we; i++ {
			if busy[i][0] > cur {
				free = append(free, [2]int{cur, busy[i][0]})
			}
			cur = max(cur, busy[i][1])
		}
		if cur < we {
			free = append(free, [2]int{cur, we})
		}
	}
	return free
}
