package inventory

import (
	"fmt"
	"sort"
)

// Service is the inventory service for a network of warehouses. It is not safe for
// concurrent use: the API layer serialises calls. Every call that takes now moves the
// service clock forward (and expires holds that ran out); now may not go backwards.
type Service struct {
	store      *store
	warehouses map[string]bool
	now        int64
	seq        int
}

// New returns an empty service.
func New() *Service {
	return &Service{store: newStore(), warehouses: map[string]bool{}}
}

// AddWarehouse registers a warehouse.
func (s *Service) AddWarehouse(id string) error {
	if id == "" {
		return fmt.Errorf("%w: empty warehouse id", ErrInvalid)
	}
	if s.warehouses[id] {
		return fmt.Errorf("%w: warehouse %q", ErrDuplicate, id)
	}
	s.warehouses[id] = true
	return nil
}

func (s *Service) checkWarehouse(id string) error {
	if !s.warehouses[id] {
		return fmt.Errorf("%w: %q", ErrUnknownWarehouse, id)
	}
	return nil
}

// warehouseIDs returns every warehouse, sorted.
func (s *Service) warehouseIDs() []string {
	ids := make([]string, 0, len(s.warehouses))
	for id := range s.warehouses {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

// advance moves the clock to now and expires the holds that ran out.
func (s *Service) advance(now int64) error {
	if now < s.now {
		return ErrBackdated
	}
	s.now = now
	s.store.expire(now)
	return nil
}

// SetRule sets (or replaces) the replenishment rule for sku in warehouse.
func (s *Service) SetRule(warehouse, sku string, r Rule) error {
	if err := s.checkWarehouse(warehouse); err != nil {
		return err
	}
	if sku == "" || r.Min < 0 || r.Max <= r.Min || r.Pack < 0 {
		return fmt.Errorf("%w: rule needs 0 <= Min < Max and Pack >= 0", ErrInvalid)
	}
	s.store.rules[stockKey{warehouse, sku}] = r
	return nil
}

// Receive puts qty units of sku from a supplier delivery away into a bin.
func (s *Service) Receive(warehouse, bin, sku string, qty int, now int64) error {
	if err := s.checkWarehouse(warehouse); err != nil {
		return err
	}
	if bin == "" || sku == "" || qty <= 0 {
		return fmt.Errorf("%w: receive needs a bin, a SKU and a positive quantity", ErrInvalid)
	}
	if err := s.advance(now); err != nil {
		return err
	}
	s.store.putAway(binKey{warehouse, bin, sku}, qty)
	return nil
}

// OnHand is the physical quantity of sku on the warehouse's shelves.
func (s *Service) OnHand(warehouse, sku string) int {
	return s.store.onHand[stockKey{warehouse, sku}]
}

// BinQty is the quantity of sku in one bin.
func (s *Service) BinQty(warehouse, bin, sku string) int {
	return s.store.bins[binKey{warehouse, bin, sku}]
}

// Available is what can still be promised: on hand minus active reservations, at now.
func (s *Service) Available(warehouse, sku string, now int64) (int, error) {
	if err := s.checkWarehouse(warehouse); err != nil {
		return 0, err
	}
	if err := s.advance(now); err != nil {
		return 0, err
	}
	return s.available(stockKey{warehouse, sku}), nil
}

func (s *Service) available(k stockKey) int {
	return s.store.onHand[k] - s.store.reserved[k]
}
