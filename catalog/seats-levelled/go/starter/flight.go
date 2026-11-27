// Package flight is the in-memory core of an airline's business-class desk for one multi-stop flight.
package flight

// Flight holds the desk's business seats on each leg of the route.
type Flight struct {
	// your state here
}

// NewFlight returns a flight whose leg k has seats[k] seats.
func NewFlight(seats []int) *Flight {
	panic("not implemented")
}

// Book gives the passenger a seat on every leg from board to alight.
func (f *Flight) Book(passenger string, board int, alight int) bool {
	panic("not implemented")
}

// Cancel frees the passenger's seat.
func (f *Flight) Cancel(passenger string) bool {
	panic("not implemented")
}

// FreeSeats returns how many seats on the leg nobody holds.
func (f *Flight) FreeSeats(leg int) (int, bool) {
	panic("not implemented")
}
