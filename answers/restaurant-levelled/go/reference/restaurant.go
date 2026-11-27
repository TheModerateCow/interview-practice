// Package restaurant is the reservation book for a restaurant: tables with seat counts, reservations per seating
// slot, a walk-in waitlist, joined tables for large parties, and no-shows with a booking ban for repeat offenders.
package restaurant

import (
	"fmt"
	"sort"
	"strings"
)

const (
	grace = 15   // minutes after its slot an unseated reservation is still held
	ban   = 1440 // minutes a repeat no-show can't book ahead
)

type reservation struct {
	name   string
	size   int
	slot   int
	tables []string
	status string // booked, cancelled, seated
}

type party struct {
	name string
	size int
}

// Restaurant: every method takes ts first, the time of the call in minutes. Times only ever increase.
type Restaurant struct {
	tables  map[string]int
	links   map[[2]string]bool // {lower id, higher id}
	res     map[string]*reservation
	waiting map[int][]party
	nextID  int
}

// NewRestaurant returns an empty reservation book.
func NewRestaurant() *Restaurant {
	return &Restaurant{tables: map[string]int{}, links: map[[2]string]bool{}, res: map[string]*reservation{},
		waiting: map[int][]party{}}
}

// live reports whether r still holds its tables: not cancelled and not a no-show.
func live(ts int, r *reservation) bool {
	if r.status == "cancelled" {
		return false
	}
	return !(r.status == "booked" && ts >= r.slot+grace)
}

func (rt *Restaurant) taken(ts, slot int) map[string]bool {
	out := map[string]bool{}
	for _, r := range rt.res {
		if r.slot == slot && live(ts, r) {
			for _, t := range r.tables {
				out[t] = true
			}
		}
	}
	return out
}

// fit returns the tables the booking rule gives a party of size at slot, or nil.
func (rt *Restaurant) fit(ts, size, slot int) []string {
	taken := rt.taken(ts, slot)
	best := ""
	for t, seats := range rt.tables {
		if !taken[t] && seats >= size {
			if best == "" || seats < rt.tables[best] || seats == rt.tables[best] && t < best {
				best = t
			}
		}
	}
	if best != "" {
		return []string{best}
	}
	var bp [2]string
	bs := -1
	for p := range rt.links {
		s := rt.tables[p[0]] + rt.tables[p[1]]
		if !taken[p[0]] && !taken[p[1]] && s >= size {
			if bs < 0 || s < bs || s == bs && (p[0] < bp[0] || p[0] == bp[0] && p[1] < bp[1]) {
				bp, bs = p, s
			}
		}
	}
	if bs >= 0 {
		return []string{bp[0], bp[1]}
	}
	return nil
}

func (rt *Restaurant) add(name string, size, slot int, tables []string) string {
	rt.nextID++
	id := fmt.Sprintf("r%d", rt.nextID)
	rt.res[id] = &reservation{name: name, size: size, slot: slot, tables: tables, status: "booked"}
	return id
}

// walk books every waiting party at slot that now fits, front first.
func (rt *Restaurant) walk(ts, slot int) {
	keep := []party{}
	for _, p := range rt.waiting[slot] {
		if tables := rt.fit(ts, p.size, slot); tables != nil {
			rt.add(p.name, p.size, slot, tables)
		} else {
			keep = append(keep, p)
		}
	}
	rt.waiting[slot] = keep
}

func (rt *Restaurant) noShowTimes(ts int, name string) []int {
	out := []int{}
	for _, r := range rt.res {
		if r.name == name && r.status == "booked" && ts >= r.slot+grace {
			out = append(out, r.slot+grace)
		}
	}
	return out
}

// ---------------------------------------------------------------- level 1

func (rt *Restaurant) AddTable(ts int, tableID string, seats int) bool {
	if _, ok := rt.tables[tableID]; ok || seats <= 0 {
		return false
	}
	rt.tables[tableID] = seats
	return true
}

func (rt *Restaurant) Book(ts int, name string, size int, slot int) string {
	if size <= 0 || ts >= slot+grace {
		return ""
	}
	times := rt.noShowTimes(ts, name)
	if len(times) >= 2 && ts < maxOf(times)+ban {
		return ""
	}
	if tables := rt.fit(ts, size, slot); tables != nil {
		return rt.add(name, size, slot, tables)
	}
	return ""
}

func maxOf(xs []int) int {
	m := xs[0]
	for _, x := range xs {
		m = max(m, x)
	}
	return m
}

func (rt *Restaurant) Cancel(ts int, reservationID string) bool {
	r := rt.res[reservationID]
	if r == nil || r.status != "booked" || !live(ts, r) {
		return false
	}
	r.status = "cancelled"
	rt.walk(ts, r.slot)
	return true
}

func (rt *Restaurant) TableOf(ts int, reservationID string) string {
	r := rt.res[reservationID]
	if r == nil || !live(ts, r) {
		return ""
	}
	return strings.Join(r.tables, "+")
}

func (rt *Restaurant) PartyAt(ts int, tableID string, slot int) string {
	for _, r := range rt.res {
		if r.slot == slot && live(ts, r) {
			for _, t := range r.tables {
				if t == tableID {
					return r.name
				}
			}
		}
	}
	return ""
}

// ---------------------------------------------------------------- level 2

func (rt *Restaurant) JoinWaitlist(ts int, name string, size int, slot int) bool {
	if size <= 0 || ts >= slot+grace {
		return false
	}
	for _, p := range rt.waiting[slot] {
		if p.name == name {
			return false
		}
	}
	if tables := rt.fit(ts, size, slot); tables != nil {
		rt.add(name, size, slot, tables)
	} else {
		rt.waiting[slot] = append(rt.waiting[slot], party{name, size})
	}
	return true
}

func (rt *Restaurant) Waitlist(ts int, slot int) []string {
	out := []string{}
	for _, p := range rt.waiting[slot] {
		out = append(out, fmt.Sprintf("%s(%d)", p.name, p.size))
	}
	return out
}

func (rt *Restaurant) FreeTables(ts int, slot int) []string {
	taken := rt.taken(ts, slot)
	out := []string{}
	for t := range rt.tables {
		if !taken[t] {
			out = append(out, t)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		si, sj := rt.tables[out[i]], rt.tables[out[j]]
		if si != sj {
			return si < sj
		}
		return out[i] < out[j]
	})
	return out
}

// ---------------------------------------------------------------- level 3

func (rt *Restaurant) LinkTables(ts int, tableA string, tableB string) bool {
	pair := [2]string{min(tableA, tableB), max(tableA, tableB)}
	_, okA := rt.tables[tableA]
	_, okB := rt.tables[tableB]
	if !okA || !okB || tableA == tableB || rt.links[pair] {
		return false
	}
	rt.links[pair] = true
	return true
}

// ---------------------------------------------------------------- level 4

func (rt *Restaurant) Seat(ts int, reservationID string) bool {
	r := rt.res[reservationID]
	if r == nil || r.status != "booked" || !live(ts, r) {
		return false
	}
	r.status = "seated"
	return true
}

func (rt *Restaurant) NoShows(ts int, name string) int {
	return len(rt.noShowTimes(ts, name))
}
