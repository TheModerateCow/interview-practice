// Package dispatch assigns food-delivery orders to couriers and estimates
// when each order will reach the customer.
package dispatch

// Point is a position on the city grid, in metres east (X) and north (Y)
// of the zone's origin.
type Point struct{ X, Y int }

// State is where an order is in its lifecycle.
type State int

const (
	Placed    State = iota // waiting for a courier
	Assigned               // a courier is riding to the restaurant
	PickedUp               // the courier has the food
	Delivered              // handed to the customer
	Cancelled              // cancelled by the customer or support
)

var stateNames = [...]string{"placed", "assigned", "picked_up", "delivered", "cancelled"}

func (s State) String() string {
	if s < 0 || int(s) >= len(stateNames) {
		return "unknown"
	}
	return stateNames[s]
}

// ParseState turns a name such as "picked_up" back into a State.
func ParseState(name string) (State, bool) {
	for i, n := range stateNames {
		if n == name {
			return State(i), true
		}
	}
	return 0, false
}

// transitions lists the states each state may move to.
var transitions = map[State][]State{
	Placed:   {Assigned, Cancelled},
	Assigned: {PickedUp, Cancelled},
	PickedUp: {Delivered},
}

// CanMoveTo reports whether an order in state s may move to next.
func (s State) CanMoveTo(next State) bool {
	for _, n := range transitions[s] {
		if n == next {
			return true
		}
	}
	return false
}

// Terminal reports whether the order is finished: the courier no longer
// carries it.
func (s State) Terminal() bool { return s == Delivered || s == Cancelled }

// Order is one customer order from one restaurant.
type Order struct {
	ID          string
	Restaurant  Point
	Customer    Point
	PlacedAt    int // minute of the shift the order was placed
	PrepMinutes int // kitchen's estimate until the food is ready
	State       State
	CourierID   string // set once assigned
}

// ReadyAt is the minute of the shift the kitchen expects the food to be ready.
func (o *Order) ReadyAt() int { return o.PlacedAt + o.PrepMinutes }

// Courier is a rider on shift.
type Courier struct {
	ID       string
	Location Point
	Capacity int // most orders carried at once
	Active   int // orders currently assigned to or carried by the courier
}
