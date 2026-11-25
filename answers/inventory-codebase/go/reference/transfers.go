package inventory

import "fmt"

// StartTransfer ships qty units of sku from one warehouse to another. The units are
// picked from the source's bins now and count as inbound at the destination until
// ReceiveTransfer puts them away.
func (s *Service) StartTransfer(id, from, to, sku string, qty int, now int64) (Transfer, error) {
	for _, w := range []string{from, to} {
		if err := s.checkWarehouse(w); err != nil {
			return Transfer{}, err
		}
	}
	if id == "" || from == to || qty <= 0 {
		return Transfer{}, fmt.Errorf("%w: transfer needs an id, two warehouses and a positive quantity", ErrInvalid)
	}
	if _, dup := s.store.transfers[id]; dup {
		return Transfer{}, fmt.Errorf("%w: transfer %q", ErrDuplicate, id)
	}
	if err := s.advance(now); err != nil {
		return Transfer{}, err
	}
	src := stockKey{from, sku}
	if avail := s.available(src); avail < qty {
		return Transfer{}, fmt.Errorf("%w: %d available at %s, %d requested", ErrInsufficientStock, avail, from, qty)
	}
	if err := s.store.pick(src, qty); err != nil {
		return Transfer{}, err
	}
	t := &Transfer{ID: id, From: from, To: to, SKU: sku, Qty: qty, Status: InTransit, ShippedAt: now}
	s.store.transfers[id] = t
	s.store.inbound[stockKey{to, sku}] += qty
	return *t, nil
}

// ReceiveTransfer puts an arrived transfer away into a bin at its destination.
func (s *Service) ReceiveTransfer(id, bin string, now int64) error {
	if bin == "" {
		return fmt.Errorf("%w: empty bin", ErrInvalid)
	}
	if err := s.advance(now); err != nil {
		return err
	}
	t, ok := s.store.transfers[id]
	if !ok {
		return fmt.Errorf("%w: transfer %q", ErrNotFound, id)
	}
	if t.Status != InTransit {
		return ErrTransferState
	}
	s.store.inbound[stockKey{t.To, t.SKU}] -= t.Qty
	s.store.putAway(binKey{t.To, bin, t.SKU}, t.Qty)
	t.Status, t.ReceivedAt, t.Bin = Received, now, bin
	return nil
}

// Inbound is the quantity of sku in transit toward warehouse.
func (s *Service) Inbound(warehouse, sku string) int {
	return s.store.inbound[stockKey{warehouse, sku}]
}

// Transfer returns a copy of a transfer.
func (s *Service) Transfer(id string) (Transfer, bool) {
	t, ok := s.store.transfers[id]
	if !ok {
		return Transfer{}, false
	}
	return *t, true
}
