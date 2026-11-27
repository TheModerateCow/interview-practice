// Package rental is the fleet desk for a car-rental company: cars by class and branch, rentals
// with daily rates and late fees, one-way drop-offs, and reservations made ahead of time.
package rental

import (
	"fmt"
	"sort"
)

var rates = map[string]int{"economy": 3000, "compact": 4500, "suv": 7000} // cents per day

const dropFee = 5000
const day = 24 // hours

// days is whole days started: 1 to 24 hours is 1 day, 25 is 2.
func days(hours int) int { return (hours + day - 1) / day }

type rental struct {
	customer   string
	start, due int
}

type car struct {
	class, branch string
	out           *rental
}

type reservation struct {
	customer, branch, class string
	start, end              int
	used                    bool
}

// RentalDesk: every method takes ts first, the time of the call in hours. Timestamps only ever increase.
type RentalDesk struct {
	cars         map[string]*car
	branches     map[string]bool
	paid         map[string]int
	reservations map[string]*reservation
	nextRes      int
}

// NewRentalDesk returns an empty desk.
func NewRentalDesk() *RentalDesk {
	return &RentalDesk{cars: map[string]*car{}, branches: map[string]bool{}, paid: map[string]int{},
		reservations: map[string]*reservation{}}
}

// free returns the ids of the cars of class parked at branch, lowest first.
func (d *RentalDesk) free(branch, class string) []string {
	ids := []string{}
	for id, c := range d.cars {
		if c.out == nil && c.branch == branch && c.class == class {
			ids = append(ids, id)
		}
	}
	sort.Strings(ids)
	return ids
}

func (d *RentalDesk) hasCar(customer string) bool {
	for _, c := range d.cars {
		if c.out != nil && c.out.customer == customer {
			return true
		}
	}
	return false
}

// pending counts reservations not yet picked up that overlap [start, end); start >= ts, so a lapsed one never does.
func (d *RentalDesk) pending(branch, class string, start, end int) int {
	n := 0
	for _, r := range d.reservations {
		if !r.used && r.branch == branch && r.class == class && r.start < end && start < r.end {
			n++
		}
	}
	return n
}

// ---------------------------------------------------------------- level 1

func (d *RentalDesk) AddCar(ts int, carID string, carClass string, branch string) bool {
	if _, ok := d.cars[carID]; ok {
		return false
	}
	if _, ok := rates[carClass]; !ok {
		return false
	}
	d.cars[carID] = &car{class: carClass, branch: branch}
	d.branches[branch] = true
	return true
}

func (d *RentalDesk) Rent(ts int, customer string, branch string, carClass string, days int) string {
	if _, ok := rates[carClass]; !ok || days <= 0 || d.hasCar(customer) {
		return ""
	}
	due := ts + day*days
	free := d.free(branch, carClass)
	if len(free) <= d.pending(branch, carClass, ts, due) {
		return ""
	}
	d.cars[free[0]].out = &rental{customer: customer, start: ts, due: due}
	return free[0]
}

func (d *RentalDesk) ReturnCar(ts int, carID string) bool {
	c := d.cars[carID]
	if c == nil || c.out == nil {
		return false
	}
	return d.DropOff(ts, carID, c.branch)
}

func (d *RentalDesk) Status(ts int, carID string) string {
	c := d.cars[carID]
	if c == nil {
		return ""
	}
	if c.out != nil {
		return "rented:" + c.out.customer
	}
	return "available:" + c.branch
}

// ---------------------------------------------------------------- level 2

func (d *RentalDesk) Charges(ts int, customer string) int {
	return d.paid[customer]
}

func (d *RentalDesk) Overdue(ts int) []string {
	ids := []string{}
	for id, c := range d.cars {
		if c.out != nil && c.out.due < ts {
			ids = append(ids, id)
		}
	}
	sort.Slice(ids, func(i, j int) bool {
		di, dj := d.cars[ids[i]].out.due, d.cars[ids[j]].out.due
		if di != dj {
			return di < dj
		}
		return ids[i] < ids[j]
	})
	out := make([]string, len(ids))
	for i, id := range ids {
		out[i] = fmt.Sprintf("%s(%s)", id, d.cars[id].out.customer)
	}
	return out
}

// ---------------------------------------------------------------- level 3

func (d *RentalDesk) DropOff(ts int, carID string, branch string) bool {
	c := d.cars[carID]
	if c == nil || c.out == nil || !d.branches[branch] {
		return false
	}
	out := c.out
	n := max(1, days(ts-out.start)) + days(max(0, ts-out.due))
	fee := n * rates[c.class]
	if branch != c.branch {
		fee += dropFee
	}
	d.paid[out.customer] += fee
	c.branch = branch
	c.out = nil
	return true
}

func (d *RentalDesk) Available(ts int, branch string) []string {
	counts := map[string]int{}
	for _, c := range d.cars {
		if c.out == nil && c.branch == branch {
			counts[c.class]++
		}
	}
	classes := make([]string, 0, len(counts))
	for k := range counts {
		classes = append(classes, k)
	}
	sort.Strings(classes)
	out := make([]string, len(classes))
	for i, k := range classes {
		out[i] = fmt.Sprintf("%s(%d)", k, counts[k])
	}
	return out
}

// ---------------------------------------------------------------- level 4

func (d *RentalDesk) Reserve(ts int, customer string, branch string, carClass string, start int, days int) string {
	if _, ok := rates[carClass]; !ok || days <= 0 || start < ts {
		return ""
	}
	end := start + day*days
	fleet := 0
	for _, c := range d.cars {
		if c.branch == branch && c.class == carClass {
			fleet++
		}
	}
	if d.pending(branch, carClass, start, end) >= fleet {
		return ""
	}
	d.nextRes++
	id := fmt.Sprintf("r%d", d.nextRes)
	d.reservations[id] = &reservation{customer: customer, branch: branch, class: carClass, start: start, end: end}
	return id
}

func (d *RentalDesk) PickUp(ts int, reservationID string) string {
	r := d.reservations[reservationID]
	if r == nil || r.used || ts < r.start || ts >= r.end || d.hasCar(r.customer) {
		return ""
	}
	free := d.free(r.branch, r.class)
	if len(free) == 0 {
		return ""
	}
	r.used = true
	d.cars[free[0]].out = &rental{customer: r.customer, start: ts, due: r.end}
	return free[0]
}
