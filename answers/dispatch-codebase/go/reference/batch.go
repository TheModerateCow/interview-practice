package dispatch

import "sort"

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
	var due []*Order
	for _, o := range d.store.PendingOrders() {
		if o.ReadyAt()-now <= DispatchWindow {
			due = append(due, o)
		}
	}
	sort.Slice(due, func(i, j int) bool {
		if due[i].ReadyAt() != due[j].ReadyAt() {
			return due[i].ReadyAt() < due[j].ReadyAt()
		}
		return due[i].ID < due[j].ID
	})
	out := []Assignment{}
	for _, o := range due {
		if c := d.nearestCourier(o.Restaurant); c != nil {
			d.assign(o, c)
			out = append(out, Assignment{OrderID: o.ID, CourierID: c.ID})
		}
	}
	return out
}
