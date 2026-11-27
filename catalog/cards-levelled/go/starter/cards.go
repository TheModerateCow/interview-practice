package cards

type Issuer struct{}

func NewIssuer() *Issuer {
	panic("not implemented")
}

func (s *Issuer) IssueCard(day int, cardID string, limit int) bool {
	panic("not implemented")
}

func (s *Issuer) Authorize(day int, cardID string, category string, amount int) string {
	panic("not implemented")
}

func (s *Issuer) Capture(day int, authID string, amount int) bool {
	panic("not implemented")
}

func (s *Issuer) VoidAuth(day int, authID string) bool {
	panic("not implemented")
}

func (s *Issuer) Available(day int, cardID string) int {
	panic("not implemented")
}
