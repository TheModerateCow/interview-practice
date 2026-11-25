package dispatch

import "errors"

var (
	ErrNoCourier      = errors.New("no courier available")
	ErrBadTransition  = errors.New("order cannot move to that state")
	ErrInvalidCourier = errors.New("courier capacity must be at least 1")
)

// MaxPickupDistance is the furthest, in metres, a courier may be from the
// restaurant to be offered an order.
const MaxPickupDistance = 4000

// Dispatcher runs dispatch for one delivery zone.
type Dispatcher struct {
	store *Store
}

// New returns a dispatcher for an empty zone.
func New() *Dispatcher { return &Dispatcher{store: NewStore()} }

// AddCourier puts a courier on shift at a location.
func (d *Dispatcher) AddCourier(id string, at Point, capacity int) error {
	if capacity < 1 {
		return ErrInvalidCourier
	}
	return d.store.AddCourier(&Courier{ID: id, Location: at, Capacity: capacity})
}

// PlaceOrder records a new order, waiting for a courier.
func (d *Dispatcher) PlaceOrder(id string, restaurant, customer Point, placedAt, prepMinutes int) error {
	return d.store.AddOrder(&Order{
		ID: id, Restaurant: restaurant, Customer: customer,
		PlacedAt: placedAt, PrepMinutes: prepMinutes, State: Placed,
	})
}

// Order returns a copy of an order.
func (d *Dispatcher) Order(id string) (Order, error) {
	o, err := d.store.Order(id)
	if err != nil {
		return Order{}, err
	}
	return *o, nil
}

// Assign hands a waiting order to the nearest courier with room, right away.
func (d *Dispatcher) Assign(orderID string) (string, error) {
	o, err := d.store.Order(orderID)
	if err != nil {
		return "", err
	}
	if o.State != Placed {
		return "", ErrBadTransition
	}
	c := d.nearestCourier(o.Restaurant)
	if c == nil {
		return "", ErrNoCourier
	}
	d.assign(o, c)
	return c.ID, nil
}

// Advance moves an order along its lifecycle: picked_up, delivered or
// cancelled. Orders become assigned only through Assign or DispatchPending.
func (d *Dispatcher) Advance(orderID string, to State) error {
	o, err := d.store.Order(orderID)
	if err != nil {
		return err
	}
	if to == Assigned || !o.State.CanMoveTo(to) {
		return ErrBadTransition
	}
	o.State = to
	if o.CourierID == "" {
		return nil
	}
	c, err := d.store.Courier(o.CourierID)
	if err != nil {
		return err
	}
	switch to {
	case PickedUp:
		c.Location = o.Restaurant
	case Delivered:
		c.Location = o.Customer
	}
	if to.Terminal() {
		c.Active--
	}
	return nil
}

// CourierOrders lists the ids of the unfinished orders a courier holds.
func (d *Dispatcher) CourierOrders(courierID string) ([]string, error) {
	if _, err := d.store.Courier(courierID); err != nil {
		return nil, err
	}
	var ids []string
	for _, o := range d.store.ActiveOrdersOf(courierID) {
		ids = append(ids, o.ID)
	}
	return ids, nil
}

// nearestCourier picks the courier closest to a restaurant who has room for
// another order and is within MaxPickupDistance. Ties go to the lower id.
func (d *Dispatcher) nearestCourier(restaurant Point) *Courier {
	var best *Courier
	bestDist := 0
	for _, c := range d.store.Couriers() {
		if len(d.store.ActiveOrdersOf(c.ID)) >= c.Capacity {
			continue
		}
		dist := Distance(c.Location, restaurant)
		if dist > MaxPickupDistance {
			continue
		}
		if best == nil || dist < bestDist || (dist == bestDist && c.ID < best.ID) {
			best, bestDist = c, dist
		}
	}
	return best
}

func (d *Dispatcher) assign(o *Order, c *Courier) {
	o.State = Assigned
	o.CourierID = c.ID
	c.Active++
}
