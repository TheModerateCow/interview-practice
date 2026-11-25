// Package tickets is the box office for a concert promoter: events with a fixed
// number of seats, buyers who own tickets, and short seat holds at checkout.
package tickets

import (
	"fmt"
	"sort"
	"strconv"
)

// change is one movement of owned tickets, kept for the history queries.
type change struct {
	ts    int
	buyer string
	delta int
}

type hold struct {
	eventID   string
	buyer     string
	qty       int
	expiresAt int
	confirmed bool
}

type event struct {
	capacity int
	owned    map[string]int
	sold     int
	log      []change
}

// Office holds every event. Timestamps passed to its methods only ever increase.
type Office struct {
	events map[string]*event
	holds  map[string]*hold
	nextID int
}

// NewOffice returns an empty office.
func NewOffice() *Office {
	return &Office{events: map[string]*event{}, holds: map[string]*hold{}}
}

func (o *Office) own(ts int, e *event, buyer string, delta int) {
	e.owned[buyer] += delta
	e.sold += delta
	e.log = append(e.log, change{ts, buyer, delta})
}

// held is the number of seats of eventID under a live hold at ts.
func (o *Office) held(ts int, eventID string) int {
	n := 0
	for _, h := range o.holds {
		if h.eventID == eventID && !h.confirmed && ts < h.expiresAt {
			n += h.qty
		}
	}
	return n
}

// CreateEvent adds an event with capacity seats. False if the id exists or capacity <= 0.
func (o *Office) CreateEvent(ts int, eventID string, capacity int) bool {
	if _, ok := o.events[eventID]; ok || capacity <= 0 {
		return false
	}
	o.events[eventID] = &event{capacity: capacity, owned: map[string]int{}}
	return true
}

// Buy gives buyer qty tickets. False if the event is unknown, qty <= 0 or fewer than qty seats are available.
func (o *Office) Buy(ts int, eventID, buyer string, qty int) bool {
	e, ok := o.events[eventID]
	if !ok || qty <= 0 || qty > o.Available(ts, eventID) {
		return false
	}
	o.own(ts, e, buyer, qty)
	return true
}

// Refund returns qty of buyer's tickets to the event. False if the event is unknown, qty <= 0 or buyer owns fewer.
func (o *Office) Refund(ts int, eventID, buyer string, qty int) bool {
	e, ok := o.events[eventID]
	if !ok || qty <= 0 || e.owned[buyer] < qty {
		return false
	}
	o.own(ts, e, buyer, -qty)
	return true
}

// Available is the number of seats that can still be bought, or -1 for an unknown event.
func (o *Office) Available(ts int, eventID string) int {
	e, ok := o.events[eventID]
	if !ok {
		return -1
	}
	return e.capacity - e.sold - o.held(ts, eventID)
}

// TopBuyers lists up to n buyers of eventID as "buyer(qty)", most tickets first, ties by name.
func (o *Office) TopBuyers(ts int, eventID string, n int) []string {
	out := []string{}
	e, ok := o.events[eventID]
	if !ok {
		return out
	}
	names := []string{}
	for b, q := range e.owned {
		if q > 0 {
			names = append(names, b)
		}
	}
	sort.Slice(names, func(i, j int) bool {
		if e.owned[names[i]] != e.owned[names[j]] {
			return e.owned[names[i]] > e.owned[names[j]]
		}
		return names[i] < names[j]
	})
	for i := 0; i < len(names) && i < n; i++ {
		out = append(out, fmt.Sprintf("%s(%d)", names[i], e.owned[names[i]]))
	}
	return out
}

// BusiestEvents lists up to n events as "event(sold)", most tickets sold first, ties by id.
func (o *Office) BusiestEvents(ts int, n int) []string {
	ids := []string{}
	for id := range o.events {
		ids = append(ids, id)
	}
	sort.Slice(ids, func(i, j int) bool {
		a, b := o.events[ids[i]].sold, o.events[ids[j]].sold
		if a != b {
			return a > b
		}
		return ids[i] < ids[j]
	})
	out := []string{}
	for i := 0; i < len(ids) && i < n; i++ {
		out = append(out, fmt.Sprintf("%s(%d)", ids[i], o.events[ids[i]].sold))
	}
	return out
}

// Hold reserves qty seats for buyer until ts+ttl and returns its id ("h1", "h2", ...),
// or "" if the event is unknown, qty <= 0, ttl <= 0 or fewer than qty seats are available.
func (o *Office) Hold(ts int, eventID, buyer string, qty, ttl int) string {
	if _, ok := o.events[eventID]; !ok || qty <= 0 || ttl <= 0 || qty > o.Available(ts, eventID) {
		return ""
	}
	o.nextID++
	id := "h" + strconv.Itoa(o.nextID)
	o.holds[id] = &hold{eventID: eventID, buyer: buyer, qty: qty, expiresAt: ts + ttl}
	return id
}

// Confirm turns a live hold into tickets owned by its buyer. False if the hold is unknown,
// already confirmed, or expired (ts >= ts of the hold + ttl).
func (o *Office) Confirm(ts int, holdID string) bool {
	h, ok := o.holds[holdID]
	if !ok || h.confirmed || ts >= h.expiresAt {
		return false
	}
	h.confirmed = true
	o.own(ts, o.events[h.eventID], h.buyer, h.qty)
	return true
}

// OwnedAt is how many tickets buyer owned for eventID after every operation at or before atTs.
// -1 for an unknown event; 0 for a time before the event existed.
func (o *Office) OwnedAt(ts int, eventID, buyer string, atTs int) int {
	e, ok := o.events[eventID]
	if !ok {
		return -1
	}
	n := 0
	for _, c := range e.log {
		if c.ts <= atTs && c.buyer == buyer {
			n += c.delta
		}
	}
	return n
}

// SoldAt is how many tickets of eventID were owned, by anyone, after every operation at or before atTs.
// -1 for an unknown event; 0 for a time before the event existed.
func (o *Office) SoldAt(ts int, eventID string, atTs int) int {
	e, ok := o.events[eventID]
	if !ok {
		return -1
	}
	n := 0
	for _, c := range e.log {
		if c.ts <= atTs {
			n += c.delta
		}
	}
	return n
}
