// Package invoice is one B2B invoice: discounted line items, tax by category, credit notes, payments and late fees.
//
// All money is an int number of cents. Days are day numbers (0, 1, 2, ...).
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

var terms = map[string]int{"net15": 15, "net30": 30, "net60": 60}

// taxBP is in basis points: 2000 = 20%.
var taxBP = map[string]int{"standard": 2000, "reduced": 500, "zero": 0}

const lateFeeBP = 150 // 1.5%

// halfUp is numerator / denominator rounded to the nearest int, an exact half rounding up (both >= 0).
func halfUp(numerator, denominator int) int {
	return (numerator + denominator/2) / denominator
}

func discountBP(quantity int) int {
	if quantity >= 100 {
		return 1000
	}
	if quantity >= 50 {
		return 500
	}
	return 0
}

type line struct {
	category string
	net      int
}

type Invoice struct {
	issueDay int
	terms    int
	lines    []line
	settled  int // payments + credit notes
}

func NewInvoice(issueDay int, termsName string) (*Invoice, error) {
	t, ok := terms[termsName]
	if !ok {
		return nil, ErrInvalidTerms
	}
	return &Invoice{issueDay: issueDay, terms: t}, nil
}

func (i *Invoice) AddLine(unitPrice int, quantity int, category string) (int, error) {
	if _, ok := taxBP[category]; !ok {
		return 0, ErrInvalidCategory
	}
	if quantity < 1 {
		return 0, ErrInvalidQuantity
	}
	if unitPrice < 0 {
		return 0, ErrInvalidPrice
	}
	gross := unitPrice * quantity
	net := gross - halfUp(gross*discountBP(quantity), 10000)
	i.lines = append(i.lines, line{category, net})
	return net, nil
}

func (i *Invoice) Subtotal() int {
	sum := 0
	for _, l := range i.lines {
		sum += l.net
	}
	return sum
}

func (i *Invoice) Tax() int {
	byCategory := map[string]int{}
	for _, l := range i.lines {
		byCategory[l.category] += l.net
	}
	sum := 0
	for c, net := range byCategory {
		sum += halfUp(net*taxBP[c], 10000)
	}
	return sum
}

func (i *Invoice) Total() int { return i.Subtotal() + i.Tax() }

func (i *Invoice) DueDay() int { return i.issueDay + i.terms }

func (i *Invoice) Balance() int { return i.Total() - i.settled }

func (i *Invoice) settle(amount int) error {
	if amount < 1 || amount > i.Balance() {
		return ErrInvalidAmount
	}
	i.settled += amount
	return nil
}

func (i *Invoice) Pay(amount int) error { return i.settle(amount) }

func (i *Invoice) CreditNote(amount int) error { return i.settle(amount) }

func (i *Invoice) AmountDue(day int) (int, error) {
	if day < i.issueDay {
		return 0, ErrInvalidDay
	}
	owed := i.Balance()
	if day > i.DueDay() && owed > 0 {
		return owed + halfUp(owed*lateFeeBP, 10000), nil
	}
	return owed, nil
}
