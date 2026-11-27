// Package gym is the class booking desk of a gym: classes with a fixed number of
// spots, members who book them, waitlists, class credits and weekly series.
package gym

import (
	"sort"
	"strconv"
)

const (
	refundWindow = 60 // minutes before the start a cancellation still gets its credits back
	week         = 7 * 24 * 60
)

type class struct {
	start     int
	capacity  int
	price     int
	booked    map[string]int // member -> credits paid
	waiting   []string
	cancelled bool
}

// Studio holds every class. Timestamps (minutes) passed to its methods only ever increase.
type Studio struct {
	classes map[string]*class
	credits map[string]int
	series  map[string][]string
}

// NewStudio returns an empty studio.
func NewStudio() *Studio {
	return &Studio{classes: map[string]*class{}, credits: map[string]int{}, series: map[string][]string{}}
}

func newClass(start, capacity int) *class {
	return &class{start: start, capacity: capacity, booked: map[string]int{}}
}

// open is the class if it exists, isn't cancelled and hasn't started.
func (s *Studio) open(ts int, classID string) *class {
	c, ok := s.classes[classID]
	if !ok || c.cancelled || ts >= c.start {
		return nil
	}
	return c
}

func (s *Studio) promote(c *class) {
	for len(c.waiting) > 0 && len(c.booked) < c.capacity {
		m := c.waiting[0]
		c.waiting = c.waiting[1:]
		if s.credits[m] >= c.price {
			s.credits[m] -= c.price
			c.booked[m] = c.price
		}
	}
}

func indexOf(xs []string, x string) int {
	for i, v := range xs {
		if v == x {
			return i
		}
	}
	return -1
}

func (s *Studio) memberClasses(member string, keep func(*class) bool) []string {
	ids := []string{}
	for id, c := range s.classes {
		if _, ok := c.booked[member]; ok && !c.cancelled && keep(c) {
			ids = append(ids, id)
		}
	}
	sort.Slice(ids, func(i, j int) bool {
		a, b := s.classes[ids[i]], s.classes[ids[j]]
		if a.start != b.start {
			return a.start < b.start
		}
		return ids[i] < ids[j]
	})
	return ids
}

// AddClass schedules a class with capacity spots starting at start. False if the id exists, capacity <= 0 or start <= ts.
func (s *Studio) AddClass(ts int, classID string, start int, capacity int) bool {
	if _, ok := s.classes[classID]; ok || capacity <= 0 || start <= ts {
		return false
	}
	s.classes[classID] = newClass(start, capacity)
	return true
}

// Book books one spot for member, paying the class's price.
func (s *Studio) Book(ts int, classID string, member string) bool {
	c := s.open(ts, classID)
	if c == nil || len(c.booked) >= c.capacity {
		return false
	}
	if _, ok := c.booked[member]; ok {
		return false
	}
	if s.credits[member] < c.price {
		return false
	}
	s.credits[member] -= c.price
	c.booked[member] = c.price
	return true
}

// Cancel gives up member's spot (or waitlist place), refunding it early enough and promoting the next in line.
func (s *Studio) Cancel(ts int, classID string, member string) bool {
	c := s.open(ts, classID)
	if c == nil {
		return false
	}
	if i := indexOf(c.waiting, member); i >= 0 {
		c.waiting = append(c.waiting[:i], c.waiting[i+1:]...)
		return true
	}
	paid, ok := c.booked[member]
	if !ok {
		return false
	}
	delete(c.booked, member)
	if c.start-ts >= refundWindow {
		s.credits[member] += paid
	}
	s.promote(c)
	return true
}

// SpotsLeft is the number of spots not yet booked, or -1 for an unknown or called-off class.
func (s *Studio) SpotsLeft(ts int, classID string) int {
	c, ok := s.classes[classID]
	if !ok || c.cancelled {
		return -1
	}
	return c.capacity - len(c.booked)
}

// Upcoming lists the classes member has a spot in that haven't started: earliest start first, ties by id.
func (s *Studio) Upcoming(ts int, member string) []string {
	return s.memberClasses(member, func(c *class) bool { return c.start > ts })
}

// JoinWaitlist puts member at the back of a full class's waitlist and returns their position, or -1.
func (s *Studio) JoinWaitlist(ts int, classID string, member string) int {
	c := s.open(ts, classID)
	if c == nil || len(c.booked) < c.capacity {
		return -1
	}
	if _, ok := c.booked[member]; ok || indexOf(c.waiting, member) >= 0 {
		return -1
	}
	c.waiting = append(c.waiting, member)
	return len(c.waiting)
}

// Waitlist is the waiting members, next in line first.
func (s *Studio) Waitlist(ts int, classID string) []string {
	c, ok := s.classes[classID]
	if !ok || c.cancelled {
		return []string{}
	}
	return append([]string{}, c.waiting...)
}

// AddCredits adds n credits to member's balance and returns it, or -1 if n <= 0.
func (s *Studio) AddCredits(ts int, member string, n int) int {
	if n <= 0 {
		return -1
	}
	s.credits[member] += n
	return s.credits[member]
}

// Credits is member's balance.
func (s *Studio) Credits(ts int, member string) int {
	return s.credits[member]
}

// SetPrice sets what a spot in the class costs from now on.
func (s *Studio) SetPrice(ts int, classID string, price int) bool {
	c := s.open(ts, classID)
	if c == nil || price < 0 {
		return false
	}
	c.price = price
	return true
}

// AddSeries schedules weeks weekly classes "<seriesID>-1", "<seriesID>-2", ...
func (s *Studio) AddSeries(ts int, seriesID string, firstStart int, capacity int, weeks int) bool {
	if _, ok := s.series[seriesID]; ok || weeks <= 0 || capacity <= 0 || firstStart <= ts {
		return false
	}
	ids := make([]string, weeks)
	for k := range ids {
		ids[k] = seriesID + "-" + strconv.Itoa(k+1)
		if _, ok := s.classes[ids[k]]; ok {
			return false
		}
	}
	for k, id := range ids {
		s.classes[id] = newClass(firstStart+k*week, capacity)
	}
	s.series[seriesID] = ids
	return true
}

// CancelClass calls off a class, refunding everyone with a spot and clearing the waitlist.
func (s *Studio) CancelClass(ts int, classID string) bool {
	c := s.open(ts, classID)
	if c == nil {
		return false
	}
	for m, paid := range c.booked {
		s.credits[m] += paid
	}
	c.booked = map[string]int{}
	c.waiting = nil
	c.cancelled = true
	return true
}

// CancelSeries calls off every class of the series that hasn't started; returns how many, or -1 for an unknown series.
func (s *Studio) CancelSeries(ts int, seriesID string) int {
	ids, ok := s.series[seriesID]
	if !ok {
		return -1
	}
	n := 0
	for _, id := range ids {
		if s.CancelClass(ts, id) {
			n++
		}
	}
	return n
}

// History lists the classes member had a spot in when they started: earliest start first, ties by id.
func (s *Studio) History(ts int, member string) []string {
	return s.memberClasses(member, func(c *class) bool { return c.start <= ts })
}
