package dispatch

import "errors"

var (
	ErrNotAssigned = errors.New("order has no courier yet")
	ErrOrderClosed = errors.New("order is already finished")
)

// ETA returns how many minutes from now the order should reach the customer.
//
// An assigned order: the courier rides to the restaurant, waits there if the
// food is not ready yet (see Order.ReadyAt), then rides to the customer.
// A picked-up order: the courier rides from where they are to the customer.
// Each leg's riding time counts in whole minutes, rounded up.
func (d *Dispatcher) ETA(orderID string, now int) (int, error) {
	o, err := d.store.Order(orderID)
	if err != nil {
		return 0, err
	}
	switch o.State {
	case Placed:
		return 0, ErrNotAssigned
	case Delivered, Cancelled:
		return 0, ErrOrderClosed
	}
	c, err := d.store.Courier(o.CourierID)
	if err != nil {
		return 0, err
	}
	if o.State == PickedUp {
		return TravelMinutes(Distance(c.Location, o.Customer)), nil
	}
	pickup := max(now+TravelMinutes(Distance(c.Location, o.Restaurant)), o.ReadyAt())
	return pickup + TravelMinutes(Distance(o.Restaurant, o.Customer)) - now, nil
}
