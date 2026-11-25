package quota

import "sort"

// Report summarises an organisation's traffic with from <= At < to, one line
// per key that made a request in that range. See problem.md for the rules.
func (s *Service) Report(org string, from, to int64) ([]UsageLine, error) {
	if to <= from {
		return nil, ErrBadRange
	}
	out := []UsageLine{}
	for _, id := range s.store.keysOf(org) {
		events := s.store.eventsBetween(id, from, to)
		if len(events) == 0 {
			continue
		}
		k, _ := s.store.key(id)
		line := UsageLine{KeyID: id, Plan: k.Plan}
		for _, e := range events {
			if e.Allowed {
				line.Requests++
				line.Units += e.Cost
			} else {
				line.Denied++
			}
		}
		out = append(out, line)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Units != out[j].Units {
			return out[i].Units > out[j].Units
		}
		return out[i].KeyID < out[j].KeyID
	})
	return out, nil
}
