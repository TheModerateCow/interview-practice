package inventory

// Replenishment plans restocking for one warehouse at time now: one Suggestion for each
// SKU with a Rule there whose stock position has fallen to the rule's Min, sorted by SKU.
// It only plans; nothing is moved or ordered. See problem.md for the full rules.
func (s *Service) Replenishment(warehouse string, now int64) ([]Suggestion, error) {
	panic("not implemented")
}
