// Package dispatch is the in-memory dispatch core of a ride-sharing service on one highway corridor.
package dispatch

import (
	"sort"
	"strconv"
)

// Dispatcher holds drivers and riders by id. Timestamps passed to its methods only ever increase.
type Dispatcher struct {
	idle      map[string]int // idle driver id -> km
	busy      map[string]bool
	riders    map[string]int // waiting rider id -> km
	radius    int
	hasRadius bool
}

// NewDispatcher returns a dispatcher with nobody on the corridor.
func NewDispatcher() *Dispatcher {
	return &Dispatcher{idle: map[string]int{}, busy: map[string]bool{}, riders: map[string]int{}}
}

// Level 1

func (d *Dispatcher) AddDriver(ts int, id string, km int) bool {
	if _, ok := d.idle[id]; ok || d.busy[id] {
		return false
	}
	d.idle[id] = km
	return true
}

func (d *Dispatcher) AddRider(ts int, id string, km int) bool {
	if _, ok := d.riders[id]; ok {
		return false
	}
	d.riders[id] = km
	return true
}

func (d *Dispatcher) MoveDriver(ts int, id string, km int) bool {
	if _, ok := d.idle[id]; !ok {
		return false
	}
	d.idle[id] = km
	return true
}

func (d *Dispatcher) RemoveDriver(ts int, id string) bool {
	if _, ok := d.idle[id]; !ok {
		return false
	}
	delete(d.idle, id)
	return true
}

func (d *Dispatcher) CancelRider(ts int, id string) bool {
	if _, ok := d.riders[id]; !ok {
		return false
	}
	delete(d.riders, id)
	return true
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func (d *Dispatcher) NearestDriver(ts int, rider string) (string, bool) {
	x, ok := d.riders[rider]
	if !ok {
		return "", false
	}
	best, bestKm, found := "", 0, false
	for id, km := range d.idle {
		dist := abs(km - x)
		if d.hasRadius && dist > d.radius {
			continue
		}
		if !found || dist < abs(bestKm-x) || (dist == abs(bestKm-x) && (km < bestKm || (km == bestKm && id < best))) {
			best, bestKm, found = id, km, true
		}
	}
	return best, found
}

// Level 2

func (d *Dispatcher) Dispatch(ts int, rider string) (string, bool) {
	id, ok := d.NearestDriver(ts, rider)
	if !ok {
		return "", false
	}
	delete(d.riders, rider)
	delete(d.idle, id)
	d.busy[id] = true
	return id, true
}

func (d *Dispatcher) CompleteTrip(ts int, driver string, km int) bool {
	if !d.busy[driver] {
		return false
	}
	delete(d.busy, driver)
	d.idle[driver] = km
	return true
}

func (d *Dispatcher) IdleBetween(ts int, lo int, hi int) []string {
	type hit struct {
		id string
		km int
	}
	var hits []hit
	for id, km := range d.idle {
		if lo <= km && km <= hi {
			hits = append(hits, hit{id, km})
		}
	}
	sort.Slice(hits, func(i, j int) bool {
		if hits[i].km != hits[j].km {
			return hits[i].km < hits[j].km
		}
		return hits[i].id < hits[j].id
	})
	out := []string{}
	for _, h := range hits {
		out = append(out, h.id+":"+strconv.Itoa(h.km))
	}
	return out
}

// Level 3

func (d *Dispatcher) SetRadius(ts int, radius int) {
	d.radius, d.hasRadius = radius, true
}

func (d *Dispatcher) positions() ([]int, []int) {
	r := make([]int, 0, len(d.riders))
	for _, km := range d.riders {
		r = append(r, km)
	}
	dr := make([]int, 0, len(d.idle))
	for _, km := range d.idle {
		dr = append(dr, km)
	}
	sort.Ints(r)
	sort.Ints(dr)
	return r, dr
}

func (d *Dispatcher) MaxServed(ts int) int {
	r, dr := d.positions()
	if !d.hasRadius {
		return min(len(r), len(dr))
	}
	return served(r, dr, d.radius)
}

// served: most riders picked up at once, every pickup within radius. Both slices sorted; each rider, left to right,
// takes the leftmost free driver in reach (drivers too far left are skipped for good).
func served(r, dr []int, radius int) int {
	count, j := 0, 0
	for _, x := range r {
		for j < len(dr) && dr[j] < x-radius {
			j++
		}
		if j == len(dr) {
			break
		}
		if dr[j] <= x+radius {
			count++
			j++
		}
	}
	return count
}

// Level 4

func (d *Dispatcher) MinRadius(ts int, need int) int {
	if need <= 0 {
		return 0
	}
	if need > len(d.riders) || need > len(d.idle) {
		return -1
	}
	r, dr := d.positions()
	lo, hi := 0, max(r[len(r)-1], dr[len(dr)-1])-min(r[0], dr[0])
	for lo < hi {
		mid := (lo + hi) / 2
		if served(r, dr, mid) >= need {
			hi = mid
		} else {
			lo = mid + 1
		}
	}
	return lo
}
