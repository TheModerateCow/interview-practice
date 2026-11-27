// Package meetings is the core of a team calendar's "find a time" feature: attendees in their own time
// zones, busy blocks in UTC, and searches for the earliest slot that everyone, or a quorum, can make.
package meetings

import (
	"fmt"
	"sort"
	"strconv"
)

const day = 1440

type block struct{ start, end, seq int }

type span struct{ s, e int }

type attendee struct {
	offset, workStart, workEnd int // local = UTC + offset
	busy                       map[string]block
}

func floorDiv(a, b int) int {
	q := a / b
	if a%b != 0 && a < 0 {
		q--
	}
	return q
}

func floorMod(a, b int) int { return a - floorDiv(a, b)*b }

func (a *attendee) working(minute int) bool {
	local := floorMod(minute+a.offset, day)
	if a.workStart < a.workEnd {
		return a.workStart <= local && local < a.workEnd
	}
	return local >= a.workStart || local < a.workEnd // overnight shift
}

// free returns sorted, disjoint, non-touching UTC intervals inside [lo, hi) where the attendee is free.
func (a *attendee) free(lo, hi int) []span {
	length := a.workEnd - a.workStart
	if a.workStart > a.workEnd {
		length = a.workEnd + day - a.workStart
	}
	var work []span
	d := floorDiv(lo+a.offset, day) - 1 // the local day before lo's: an overnight shift can run into lo
	for {
		s := d*day + a.workStart - a.offset
		if s >= hi {
			break
		}
		e := min(s+length, hi)
		s = max(s, lo)
		if s < e {
			if n := len(work); n > 0 && s <= work[n-1].e {
				work[n-1].e = max(work[n-1].e, e) // back-to-back working days join up
			} else {
				work = append(work, span{s, e})
			}
		}
		d++
	}
	var busy []span
	for _, b := range a.busy {
		if b.end > lo && b.start < hi {
			busy = append(busy, span{b.start, b.end})
		}
	}
	sort.Slice(busy, func(i, j int) bool {
		if busy[i].s != busy[j].s {
			return busy[i].s < busy[j].s
		}
		return busy[i].e < busy[j].e
	})
	var out []span
	i := 0
	for _, w := range work {
		for i < len(busy) && busy[i].e <= w.s {
			i++
		}
		cur := w.s
		for j := i; j < len(busy) && busy[j].s < w.e; j++ {
			if busy[j].s > cur {
				out = append(out, span{cur, busy[j].s})
			}
			cur = max(cur, busy[j].e)
		}
		if cur < w.e {
			out = append(out, span{cur, w.e})
		}
	}
	return out
}

func intersect(a, b []span) []span {
	var out []span
	i, j := 0, 0
	for i < len(a) && j < len(b) {
		s, e := max(a[i].s, b[j].s), min(a[i].e, b[j].e)
		if s < e {
			out = append(out, span{s, e})
		}
		if a[i].e < b[j].e {
			i++
		} else {
			j++
		}
	}
	return out
}

// TeamCalendar holds attendees by id. All times are integer minutes; busy blocks and searches are in UTC.
type TeamCalendar struct {
	people map[string]*attendee
	issued int
}

// NewTeamCalendar returns a calendar with no attendees.
func NewTeamCalendar() *TeamCalendar {
	return &TeamCalendar{people: map[string]*attendee{}}
}

func (t *TeamCalendar) AddAttendee(id string, offset int, workStart int, workEnd int) bool {
	if _, ok := t.people[id]; ok {
		return false
	}
	t.people[id] = &attendee{offset: offset, workStart: workStart, workEnd: workEnd, busy: map[string]block{}}
	return true
}

func (t *TeamCalendar) AddBusy(id string, start int, end int) (string, bool) {
	a := t.people[id]
	if a == nil || start >= end {
		return "", false
	}
	t.issued++
	bid := "busy" + strconv.Itoa(t.issued)
	a.busy[bid] = block{start, end, t.issued}
	return bid, true
}

func (t *TeamCalendar) RemoveBusy(id string, busyID string) bool {
	a := t.people[id]
	if a == nil {
		return false
	}
	if _, ok := a.busy[busyID]; !ok {
		return false
	}
	delete(a.busy, busyID)
	return true
}

func (t *TeamCalendar) IsFree(id string, minute int) bool {
	a := t.people[id]
	if a == nil || !a.working(minute) {
		return false
	}
	for _, b := range a.busy {
		if b.start <= minute && minute < b.end {
			return false
		}
	}
	return true
}

// level 2

func (t *TeamCalendar) SetOffset(id string, offset int) bool {
	a := t.people[id]
	if a == nil {
		return false
	}
	a.offset = offset
	return true
}

func (t *TeamCalendar) SetHours(id string, workStart int, workEnd int) bool {
	a := t.people[id]
	if a == nil {
		return false
	}
	a.workStart, a.workEnd = workStart, workEnd
	return true
}

func (t *TeamCalendar) Agenda(id string, from int, to int) []string {
	a := t.people[id]
	if a == nil {
		return []string{}
	}
	type hit struct {
		id string
		b  block
	}
	var hits []hit
	for bid, b := range a.busy {
		if b.start < to && b.end > from {
			hits = append(hits, hit{bid, b})
		}
	}
	sort.Slice(hits, func(i, j int) bool {
		x, y := hits[i].b, hits[j].b
		if x.start != y.start {
			return x.start < y.start
		}
		if x.end != y.end {
			return x.end < y.end
		}
		return x.seq < y.seq
	})
	out := []string{}
	for _, h := range hits {
		out = append(out, fmt.Sprintf("%s:%d-%d", h.id, h.b.start, h.b.end))
	}
	return out
}

func (t *TeamCalendar) lookup(ids []string) ([]*attendee, bool) {
	out := make([]*attendee, 0, len(ids))
	for _, id := range ids {
		a := t.people[id]
		if a == nil {
			return nil, false
		}
		out = append(out, a)
	}
	return out, true
}

// level 3

func (t *TeamCalendar) EarliestMeeting(ids []string, duration int, from int, to int) int {
	people, ok := t.lookup(ids)
	if !ok {
		return -1
	}
	common := []span{{from, to}}
	for _, p := range people {
		common = intersect(common, p.free(from, to))
	}
	for _, c := range common {
		if c.e-c.s >= duration {
			return c.s
		}
	}
	return -1
}

// level 4

func (t *TeamCalendar) EarliestQuorumMeeting(ids []string, quorum int, duration int, from int, to int) int {
	people, ok := t.lookup(ids)
	if !ok {
		return -1
	}
	type event struct{ at, delta int }
	var events []event
	for _, p := range people {
		for _, f := range p.free(from, to) {
			if f.e-f.s >= duration { // the meeting can start anywhere in [s, e - duration]
				events = append(events, event{f.s, 1}, event{f.e - duration + 1, -1})
			}
		}
	}
	sort.Slice(events, func(i, j int) bool { return events[i].at < events[j].at })
	count := 0
	for i := 0; i < len(events); {
		at := events[i].at
		for i < len(events) && events[i].at == at {
			count += events[i].delta
			i++
		}
		if count >= quorum {
			return at
		}
	}
	return -1
}

func (t *TeamCalendar) FreeFor(ids []string, start int, duration int) []string {
	end := start + duration
	out := []string{}
	for _, id := range ids {
		if a := t.people[id]; a != nil {
			if f := a.free(start, end); len(f) == 1 && f[0] == (span{start, end}) {
				out = append(out, id)
			}
		}
	}
	sort.Strings(out)
	return out
}
