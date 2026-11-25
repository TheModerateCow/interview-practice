package invoice

import "errors"

var (
	ErrInvalidTerms    = errors.New("invalid terms")
	ErrInvalidCategory = errors.New("invalid category")
	ErrInvalidQuantity = errors.New("invalid quantity")
	ErrInvalidPrice    = errors.New("invalid price")
	ErrInvalidAmount   = errors.New("invalid amount")
	ErrInvalidDay      = errors.New("invalid day")
)

type Invoice struct{}

func NewInvoice(issueDay int, terms string) (*Invoice, error) {
	panic("not implemented")
}

func (i *Invoice) AddLine(unitPrice int, quantity int, category string) (int, error) {
	panic("not implemented")
}

func (i *Invoice) Subtotal() int {
	panic("not implemented")
}

func (i *Invoice) Tax() int {
	panic("not implemented")
}

func (i *Invoice) Total() int {
	panic("not implemented")
}

func (i *Invoice) DueDay() int {
	panic("not implemented")
}

func (i *Invoice) Pay(amount int) error {
	panic("not implemented")
}

func (i *Invoice) CreditNote(amount int) error {
	panic("not implemented")
}

func (i *Invoice) Balance() int {
	panic("not implemented")
}

func (i *Invoice) AmountDue(day int) (int, error) {
	panic("not implemented")
}
