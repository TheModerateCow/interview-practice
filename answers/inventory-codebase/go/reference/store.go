package inventory

import "sort"

type stockKey struct{ warehouse, sku string }

type binKey struct{ warehouse, bin, sku string }

func (k binKey) stock() stockKey { return stockKey{k.warehouse, k.sku} }

// store is the in-memory state. Per-SKU counters are kept alongside the bins so
// availability checks never walk the shelves.
type store struct {
	bins     map[binKey]int
	pickPath map[stockKey][]string // cached bins per SKU in pick order, built on first pick
	onHand   map[stockKey]int      // sum of the SKU's bins
	reserved map[stockKey]int      // held by active reservations
	inbound  map[stockKey]int      // in transit toward the warehouse
	rules    map[stockKey]Rule

	reservations map[string]*Reservation
	holds        holdQueue
	transfers    map[string]*Transfer
}

func newStore() *store {
	return &store{
		bins:         map[binKey]int{},
		pickPath:     map[stockKey][]string{},
		onHand:       map[stockKey]int{},
		reserved:     map[stockKey]int{},
		inbound:      map[stockKey]int{},
		rules:        map[stockKey]Rule{},
		reservations: map[string]*Reservation{},
		transfers:    map[string]*Transfer{},
	}
}

// putAway adds qty of a SKU to a bin.
func (s *store) putAway(k binKey, qty int) {
	if _, ok := s.bins[k]; !ok {
		delete(s.pickPath, k.stock())
	}
	s.bins[k] += qty
	s.onHand[k.stock()] += qty
}

// path returns the bins that hold (or held) the SKU, sorted by bin code, which is the
// order pickers walk the aisles.
func (s *store) path(k stockKey) []string {
	if p, ok := s.pickPath[k]; ok {
		return p
	}
	var p []string
	for b := range s.bins {
		if b.stock() == k {
			p = append(p, b.bin)
		}
	}
	sort.Strings(p)
	s.pickPath[k] = p
	return p
}

// pick takes qty of a SKU off the shelves, emptying bins in pick order. If the bins hold
// less than qty it changes nothing and returns ErrShortPick.
func (s *store) pick(k stockKey, qty int) error {
	path := s.path(k)
	total := 0
	for _, b := range path {
		total += s.bins[binKey{k.warehouse, b, k.sku}]
	}
	if total < qty {
		return ErrShortPick
	}
	for _, b := range path {
		bk := binKey{k.warehouse, b, k.sku}
		take := min(qty, s.bins[bk])
		s.bins[bk] -= take
		s.onHand[k] -= take
		qty -= take
		if qty == 0 {
			break
		}
	}
	return nil
}

// endHold closes an active reservation and gives its quantity back to available stock.
func (s *store) endHold(r *Reservation, st HoldStatus, at int64) {
	s.reserved[stockKey{r.Warehouse, r.SKU}] -= r.Qty
	r.Status = st
	r.UpdatedAt = at
}
