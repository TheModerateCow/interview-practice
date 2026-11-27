// Package dispatch is the in-memory dispatch core of a ride-sharing service on one highway corridor.
package dispatch

// Dispatcher holds drivers and riders by id. Timestamps passed to its methods only ever increase.
type Dispatcher struct {
	// your state here
}

// NewDispatcher returns a dispatcher with nobody on the corridor.
func NewDispatcher() *Dispatcher {
	return &Dispatcher{}
}

// AddDriver puts a driver on shift, idle at marker km. False if the id is already on shift.
func (d *Dispatcher) AddDriver(ts int, id string, km int) bool {
	panic("not implemented")
}

// AddRider starts a rider waiting at marker km. False if the id is already waiting.
func (d *Dispatcher) AddRider(ts int, id string, km int) bool {
	panic("not implemented")
}

// MoveDriver moves an idle driver to marker km.
func (d *Dispatcher) MoveDriver(ts int, id string, km int) bool {
	panic("not implemented")
}

// RemoveDriver takes a driver off shift.
func (d *Dispatcher) RemoveDriver(ts int, id string) bool {
	panic("not implemented")
}

// CancelRider stops a rider waiting.
func (d *Dispatcher) CancelRider(ts int, id string) bool {
	panic("not implemented")
}

// NearestDriver returns the idle driver closest to the waiting rider.
func (d *Dispatcher) NearestDriver(ts int, rider string) (string, bool) {
	panic("not implemented")
}
