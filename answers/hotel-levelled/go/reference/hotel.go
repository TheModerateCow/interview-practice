// Package hotel is the front desk for a small hotel: rooms with nightly rates, bookings for
// ranges of nights, check-in and check-out, and the history of every room's rate.
package hotel

import (
	"fmt"
	"sort"
)

type rateChange struct{ day, rate int }

type room struct {
	typ   string
	rate  int
	rates []rateChange
}

type booking struct {
	guest, room string
	start, end  int
	rate        int
	status      string // booked, cancelled, in, out
}

// Hotel: every method takes day first, today's date as an integer. Days only ever increase.
type Hotel struct {
	rooms    map[string]*room
	bookings map[string]*booking
	nextID   int
}

// NewHotel returns an empty hotel.
func NewHotel() *Hotel {
	return &Hotel{rooms: map[string]*room{}, bookings: map[string]*booking{}}
}

// live reports whether b still holds its nights: not cancelled and not a no-show.
func live(day int, b *booking) bool {
	if b.status == "cancelled" {
		return false
	}
	return !(b.status == "booked" && day > b.start)
}

func (h *Hotel) free(day int, roomID string, checkIn, checkOut int) bool {
	for _, b := range h.bookings {
		if b.room == roomID && live(day, b) && checkIn < b.end && b.start < checkOut {
			return false
		}
	}
	return true
}

func (h *Hotel) bookable(day int, roomID string, checkIn, checkOut int) bool {
	_, ok := h.rooms[roomID]
	return ok && checkIn < checkOut && checkIn >= day && h.free(day, roomID, checkIn, checkOut)
}

// ---------------------------------------------------------------- level 1

func (h *Hotel) AddRoom(day int, roomID string, roomType string, rate int) bool {
	if _, ok := h.rooms[roomID]; ok || rate <= 0 {
		return false
	}
	h.rooms[roomID] = &room{typ: roomType, rate: rate, rates: []rateChange{{day, rate}}}
	return true
}

func (h *Hotel) Book(day int, guest string, roomID string, checkIn int, checkOut int) string {
	if !h.bookable(day, roomID, checkIn, checkOut) {
		return ""
	}
	h.nextID++
	id := fmt.Sprintf("b%d", h.nextID)
	h.bookings[id] = &booking{guest: guest, room: roomID, start: checkIn, end: checkOut,
		rate: h.rooms[roomID].rate, status: "booked"}
	return id
}

func (h *Hotel) Cancel(day int, bookingID string) bool {
	b := h.bookings[bookingID]
	if b == nil || b.status != "booked" || !live(day, b) {
		return false
	}
	b.status = "cancelled"
	return true
}

func (h *Hotel) Cost(day int, bookingID string) int {
	b := h.bookings[bookingID]
	if b == nil || !live(day, b) {
		return -1
	}
	return (b.end - b.start) * b.rate
}

// ---------------------------------------------------------------- level 2

func (h *Hotel) AvailableRooms(day int, roomType string, checkIn int, checkOut int) []string {
	ids := []string{}
	for id, r := range h.rooms {
		if r.typ == roomType && h.bookable(day, id, checkIn, checkOut) {
			ids = append(ids, id)
		}
	}
	sort.Slice(ids, func(i, j int) bool {
		ri, rj := h.rooms[ids[i]].rate, h.rooms[ids[j]].rate
		if ri != rj {
			return ri < rj
		}
		return ids[i] < ids[j]
	})
	return ids
}

func (h *Hotel) TopGuests(day int, n int) []string {
	nights := map[string]int{}
	for _, b := range h.bookings {
		if live(day, b) {
			nights[b.guest] += b.end - b.start
		}
	}
	order := make([]string, 0, len(nights))
	for g := range nights {
		order = append(order, g)
	}
	sort.Slice(order, func(i, j int) bool {
		if nights[order[i]] != nights[order[j]] {
			return nights[order[i]] > nights[order[j]]
		}
		return order[i] < order[j]
	})
	if n < len(order) {
		order = order[:max(n, 0)]
	}
	out := make([]string, len(order))
	for i, g := range order {
		out[i] = fmt.Sprintf("%s(%d)", g, nights[g])
	}
	return out
}

// ---------------------------------------------------------------- level 3

func (h *Hotel) CheckIn(day int, bookingID string) bool {
	b := h.bookings[bookingID]
	if b == nil || b.status != "booked" || day != b.start {
		return false
	}
	b.status = "in"
	return true
}

func (h *Hotel) CheckOut(day int, bookingID string) int {
	b := h.bookings[bookingID]
	if b == nil || b.status != "in" {
		return -1
	}
	b.end = b.start + max(1, min(day, b.end)-b.start)
	b.status = "out"
	return (b.end - b.start) * b.rate
}

// ---------------------------------------------------------------- level 4

func (h *Hotel) SetRate(day int, roomID string, rate int) bool {
	r := h.rooms[roomID]
	if r == nil || rate <= 0 {
		return false
	}
	r.rate = rate
	r.rates = append(r.rates, rateChange{day, rate})
	return true
}

func (h *Hotel) RateAt(day int, roomID string, atDay int) int {
	r := h.rooms[roomID]
	if r == nil {
		return -1
	}
	rate := -1
	for _, c := range r.rates {
		if c.day <= atDay {
			rate = c.rate
		}
	}
	return rate
}
