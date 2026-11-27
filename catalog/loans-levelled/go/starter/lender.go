package loans

type Lender struct{}

func NewLender() *Lender {
	panic("not implemented")
}

func (l *Lender) Originate(day int, loanID string, principal int, months int, rateBp int) bool {
	panic("not implemented")
}

func (l *Lender) Schedule(day int, loanID string) []string {
	panic("not implemented")
}

func (l *Lender) AmountDue(day int, loanID string) int {
	panic("not implemented")
}
