package notify

// Digest builds the user's daily digest of held notifications: those from
// the user's local day before the one containing now. See problem.md.
func (s *Service) Digest(id string, now int64) ([]DigestLine, error) {
	panic("not implemented")
}
