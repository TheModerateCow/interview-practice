package inventory

import "fmt"

// Reserve holds qty units of sku in warehouse for an order, for ttl seconds from now.
// The hold is active while the clock is before ExpiresAt = now + ttl.
func (s *Service) Reserve(id, warehouse, sku string, qty int, ttl, now int64) (Reservation, error) {
	if err := s.checkWarehouse(warehouse); err != nil {
		return Reservation{}, err
	}
	if id == "" || qty <= 0 || ttl <= 0 {
		return Reservation{}, fmt.Errorf("%w: reserve needs an id, a positive quantity and ttl", ErrInvalid)
	}
	if _, dup := s.store.reservations[id]; dup {
		return Reservation{}, fmt.Errorf("%w: reservation %q", ErrDuplicate, id)
	}
	if err := s.advance(now); err != nil {
		return Reservation{}, err
	}
	k := stockKey{warehouse, sku}
	if avail := s.available(k); avail < qty {
		return Reservation{}, fmt.Errorf("%w: %d available, %d requested", ErrInsufficientStock, avail, qty)
	}
	s.seq++
	r := &Reservation{ID: id, Warehouse: warehouse, SKU: sku, Qty: qty, CreatedAt: now,
		ExpiresAt: now + ttl, Status: Active, UpdatedAt: now, seq: s.seq}
	s.store.reservations[id] = r
	s.store.reserved[k] += qty
	s.store.track(r)
	return *r, nil
}

// Release cancels a reservation and returns its stock to available. Releasing a hold that
// is already released or has expired is a no-op, so order-service retries are safe.
func (s *Service) Release(id string, now int64) error {
	r, ok := s.store.reservations[id]
	if !ok {
		return fmt.Errorf("%w: reservation %q", ErrNotFound, id)
	}
	switch r.Status {
	case Committed:
		return fmt.Errorf("%w: %s", ErrNotActive, r.Status)
	case Released, Expired:
		return nil
	}
	if err := s.advance(now); err != nil {
		return err
	}
	s.store.endHold(r, Released, now)
	return nil
}

// Commit picks a reservation's quantity from the warehouse's bins for shipping and ends
// the hold. A hold that expired or was released can't be committed: place a new one.
func (s *Service) Commit(id string, now int64) error {
	if err := s.advance(now); err != nil {
		return err
	}
	r, ok := s.store.reservations[id]
	if !ok {
		return fmt.Errorf("%w: reservation %q", ErrNotFound, id)
	}
	if r.Status != Active {
		return fmt.Errorf("%w: %s", ErrNotActive, r.Status)
	}
	if err := s.store.pick(stockKey{r.Warehouse, r.SKU}, r.Qty); err != nil {
		return err
	}
	s.store.endHold(r, Committed, now)
	return nil
}

// Reservation returns a copy of a reservation.
func (s *Service) Reservation(id string) (Reservation, bool) {
	r, ok := s.store.reservations[id]
	if !ok {
		return Reservation{}, false
	}
	return *r, true
}
