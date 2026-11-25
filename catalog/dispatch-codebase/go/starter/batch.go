package dispatch

// DispatchWindow is how many minutes before its food is ready an order may
// be handed to a courier by DispatchPending.
const DispatchWindow = 10

// Assignment records one order handed to one courier.
type Assignment struct {
	OrderID   string
	CourierID string
}

// DispatchPending is the dispatch loop's tick: it hands out the waiting
// orders that are due at minute now. See problem.md for the rules.
func (d *Dispatcher) DispatchPending(now int) []Assignment {
	panic("not implemented")
}
