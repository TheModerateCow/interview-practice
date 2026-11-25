package quota

// Report summarises an organisation's traffic with from <= At < to, one line
// per key that made a request in that range. See problem.md for the rules.
func (s *Service) Report(org string, from, to int64) ([]UsageLine, error) {
	panic("not implemented")
}
