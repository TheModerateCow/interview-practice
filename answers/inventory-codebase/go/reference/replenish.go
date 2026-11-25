package inventory

import "sort"

// Replenishment plans restocking for one warehouse at time now: one Suggestion for each
// SKU with a Rule there whose stock position has fallen to the rule's Min, sorted by SKU.
// It only plans; nothing is moved or ordered.
func (s *Service) Replenishment(warehouse string, now int64) ([]Suggestion, error) {
	if err := s.checkWarehouse(warehouse); err != nil {
		return nil, err
	}
	if err := s.advance(now); err != nil {
		return nil, err
	}
	var skus []string
	for k := range s.store.rules {
		if k.warehouse == warehouse {
			skus = append(skus, k.sku)
		}
	}
	sort.Strings(skus)
	var out []Suggestion
	for _, sku := range skus {
		k := stockKey{warehouse, sku}
		rule := s.store.rules[k]
		pos := s.available(k) + s.store.inbound[k]
		if pos > rule.Min {
			continue
		}
		qty := rule.Max - pos
		if rule.Pack > 1 {
			qty = (qty + rule.Pack - 1) / rule.Pack * rule.Pack
		}
		out = append(out, Suggestion{SKU: sku, Position: pos, Qty: qty, From: s.source(warehouse, sku, qty)})
	}
	return out, nil
}

// source picks the other warehouse that can best spare qty units of sku: the largest
// surplus (available minus its own rule's Min) that covers qty, lowest ID on a tie.
func (s *Service) source(dest, sku string, qty int) string {
	best, bestSurplus := "", 0
	for _, w := range s.warehouseIDs() {
		if w == dest {
			continue
		}
		k := stockKey{w, sku}
		surplus := s.available(k) - s.store.rules[k].Min
		if surplus >= qty && (best == "" || surplus > bestSurplus) {
			best, bestSurplus = w, surplus
		}
	}
	return best
}
