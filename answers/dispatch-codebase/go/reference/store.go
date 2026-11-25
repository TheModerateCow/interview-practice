package dispatch

import (
	"errors"
	"sort"
)

var (
	ErrDuplicateOrder   = errors.New("order already exists")
	ErrDuplicateCourier = errors.New("courier already exists")
	ErrUnknownOrder     = errors.New("unknown order")
	ErrUnknownCourier   = errors.New("unknown courier")
)

// Store holds orders and couriers in memory.
type Store struct {
	orders   map[string]*Order
	couriers map[string]*Courier
	roster   []*Courier // couriers in the order they joined the shift
}

// NewStore returns an empty store.
func NewStore() *Store {
	return &Store{orders: map[string]*Order{}, couriers: map[string]*Courier{}}
}

// AddOrder stores a new order.
func (s *Store) AddOrder(o *Order) error {
	if _, ok := s.orders[o.ID]; ok {
		return ErrDuplicateOrder
	}
	s.orders[o.ID] = o
	return nil
}

// AddCourier stores a courier joining the shift.
func (s *Store) AddCourier(c *Courier) error {
	if _, ok := s.couriers[c.ID]; ok {
		return ErrDuplicateCourier
	}
	s.couriers[c.ID] = c
	s.roster = append(s.roster, c)
	return nil
}

// Order looks up an order by id.
func (s *Store) Order(id string) (*Order, error) {
	if o, ok := s.orders[id]; ok {
		return o, nil
	}
	return nil, ErrUnknownOrder
}

// Courier looks up a courier by id.
func (s *Store) Courier(id string) (*Courier, error) {
	if c, ok := s.couriers[id]; ok {
		return c, nil
	}
	return nil, ErrUnknownCourier
}

// Couriers returns every courier on shift, in the order they joined.
func (s *Store) Couriers() []*Courier {
	return append([]*Courier(nil), s.roster...)
}

// PendingOrders returns the orders still waiting for a courier, oldest
// first; orders placed in the same minute are sorted by id.
func (s *Store) PendingOrders() []*Order {
	var out []*Order
	for _, o := range s.orders {
		if o.State == Placed {
			out = append(out, o)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].PlacedAt != out[j].PlacedAt {
			return out[i].PlacedAt < out[j].PlacedAt
		}
		return out[i].ID < out[j].ID
	})
	return out
}

// ActiveOrdersOf returns the unfinished orders assigned to a courier,
// sorted by id.
func (s *Store) ActiveOrdersOf(courierID string) []*Order {
	var out []*Order
	for _, o := range s.orders {
		if o.CourierID == courierID && !o.State.Terminal() {
			out = append(out, o)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}
