// Package parking runs a multi-storey garage: spots of three sizes, vehicles
// that park and leave, short reservations, and the stay history behind billing.
package parking

import (
	"sort"
	"strconv"
)

// Spot and vehicle sizes, smallest first. A vehicle fits a spot of its size or larger.
var sizes = map[string]int{"small": 0, "medium": 1, "large": 2}

// Cents per started hour, by the size of the spot used.
var rates = []int{200, 300, 500}

// stay is one visit of a plate to a spot; to is -1 while the vehicle is still there.
type stay struct {
	plate    string
	from, to int
}

type spot struct {
	id    string
	size  int
	plate string
	stays []stay
}

type reservation struct {
	spotID    string
	expiresAt int
}

// Garage holds every spot. Timestamps passed to its methods only ever increase.
type Garage struct {
	spots    map[string]*spot
	parked   map[string]string
	visits   map[string]int
	reserved map[string]reservation
}

// NewGarage returns an empty garage.
func NewGarage() *Garage {
	return &Garage{spots: map[string]*spot{}, parked: map[string]string{}, visits: map[string]int{}, reserved: map[string]reservation{}}
}

// free reports whether nobody is parked in s and no live reservation holds it at ts.
func (g *Garage) free(ts int, s *spot) bool {
	if s.plate != "" {
		return false
	}
	for _, r := range g.reserved {
		if r.spotID == s.id && ts < r.expiresAt {
			return false
		}
	}
	return true
}

// pick is the free spot a vehicle of size would get: smallest fitting size, then lowest id.
func (g *Garage) pick(ts int, size int) *spot {
	var best *spot
	for _, s := range g.spots {
		if s.size < size || !g.free(ts, s) {
			continue
		}
		if best == nil || s.size < best.size || (s.size == best.size && s.id < best.id) {
			best = s
		}
	}
	return best
}

// AddSpot adds a spot. False if the id exists or size isn't small, medium or large.
func (g *Garage) AddSpot(ts int, spotID, size string) bool {
	n, ok := sizes[size]
	if _, dup := g.spots[spotID]; dup || !ok {
		return false
	}
	g.spots[spotID] = &spot{id: spotID, size: n}
	return true
}

// Park puts the vehicle in the smallest free spot that fits it (lowest id on ties) and returns
// the spot id, or "" if the size is invalid, the plate is already parked or nothing fits.
func (g *Garage) Park(ts int, plate, size string) string {
	n, ok := sizes[size]
	if !ok || g.parked[plate] != "" {
		return ""
	}
	var s *spot
	if r, ok := g.reserved[plate]; ok && ts < r.expiresAt {
		s = g.spots[r.spotID]
	} else {
		s = g.pick(ts, n)
	}
	if s == nil {
		return ""
	}
	delete(g.reserved, plate)
	s.plate = plate
	s.stays = append(s.stays, stay{plate, ts, -1})
	g.parked[plate] = s.id
	g.visits[plate]++
	return s.id
}

// Leave frees the plate's spot. False if the plate isn't parked.
func (g *Garage) Leave(ts int, plate string) bool {
	id, ok := g.parked[plate]
	if !ok {
		return false
	}
	s := g.spots[id]
	s.stays[len(s.stays)-1].to = ts
	s.plate = ""
	delete(g.parked, plate)
	return true
}

// SpotOf is the spot the plate is parked in, or "".
func (g *Garage) SpotOf(ts int, plate string) string {
	return g.parked[plate]
}

// FreeSpots counts free spots of exactly size, or -1 for an invalid size.
func (g *Garage) FreeSpots(ts int, size string) int {
	n, ok := sizes[size]
	if !ok {
		return -1
	}
	c := 0
	for _, s := range g.spots {
		if s.size == n && g.free(ts, s) {
			c++
		}
	}
	return c
}

// TopVisitors lists up to n plates as "plate(visits)", most visits first, ties by plate.
func (g *Garage) TopVisitors(ts int, n int) []string {
	plates := []string{}
	for p := range g.visits {
		plates = append(plates, p)
	}
	sort.Slice(plates, func(i, j int) bool {
		a, b := g.visits[plates[i]], g.visits[plates[j]]
		if a != b {
			return a > b
		}
		return plates[i] < plates[j]
	})
	out := []string{}
	for i := 0; i < len(plates) && i < n; i++ {
		out = append(out, plates[i]+"("+strconv.Itoa(g.visits[plates[i]])+")")
	}
	return out
}

// Reserve holds the spot Park would pick for plate until ts+ttl and returns its id, or "" if the
// size is invalid, ttl <= 0, the plate is parked or already has a live reservation, or nothing fits.
func (g *Garage) Reserve(ts int, plate, size string, ttl int) string {
	n, ok := sizes[size]
	if r, has := g.reserved[plate]; !ok || ttl <= 0 || g.parked[plate] != "" || (has && ts < r.expiresAt) {
		return ""
	}
	s := g.pick(ts, n)
	if s == nil {
		return ""
	}
	g.reserved[plate] = reservation{s.id, ts + ttl}
	return s.id
}

// Cancel drops the plate's live reservation. False if it has none.
func (g *Garage) Cancel(ts int, plate string) bool {
	r, ok := g.reserved[plate]
	if !ok || ts >= r.expiresAt {
		return false
	}
	delete(g.reserved, plate)
	return true
}

// OccupantAt is the plate in spotID after every operation at or before atTs, or "".
func (g *Garage) OccupantAt(ts int, spotID string, atTs int) string {
	s, ok := g.spots[spotID]
	if !ok {
		return ""
	}
	for _, st := range s.stays {
		if st.from <= atTs && (st.to == -1 || atTs < st.to) {
			return st.plate
		}
	}
	return ""
}

// Charges is what plate owes in cents for its finished stays: the spot's hourly rate
// for every started hour (60 time units) of each stay.
func (g *Garage) Charges(ts int, plate string) int {
	total := 0
	for _, s := range g.spots {
		for _, st := range s.stays {
			if st.plate == plate && st.to != -1 {
				total += rates[s.size] * ((st.to - st.from + 59) / 60)
			}
		}
	}
	return total
}
