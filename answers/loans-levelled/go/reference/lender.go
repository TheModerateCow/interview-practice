// Package loans is loan servicing for a consumer lender: instalment schedules,
// payments, late fees, payoff quotes and restructuring.
package loans

import "fmt"

const (
	graceDays = 10
	lateFee   = 2500
)

type instalment struct {
	due, amount              int
	fee, interest, principal int // still unpaid
	charged                  bool
}

func (i *instalment) left() int { return i.fee + i.interest + i.principal }

type loan struct {
	rateBp int
	inst   []*instalment // in due order
}

// Lender holds every loan. Days passed to its methods only ever increase.
type Lender struct {
	loans map[string]*loan
}

// NewLender returns a lender with no loans.
func NewLender() *Lender {
	return &Lender{loans: map[string]*loan{}}
}

// instalments: flat interest rounded half up; the last instalment absorbs the principal remainder.
func instalments(start, principal, months, rateBp int) []*instalment {
	interest := (principal*rateBp + 5000) / 10000
	base := principal / months
	out := make([]*instalment, 0, months)
	for k := 1; k <= months; k++ {
		p := base
		if k == months {
			p = principal - base*(months-1)
		}
		out = append(out, &instalment{due: start + 30*k, amount: p + interest, interest: interest, principal: p})
	}
	return out
}

// ---------------------------------------------------------------- level 1

func (l *Lender) Originate(day int, loanID string, principal int, months int, rateBp int) bool {
	if _, ok := l.loans[loanID]; ok || principal <= 0 || months <= 0 || rateBp < 0 {
		return false
	}
	l.loans[loanID] = &loan{rateBp: rateBp, inst: instalments(day, principal, months, rateBp)}
	return true
}

func (l *Lender) Schedule(day int, loanID string) []string {
	out := []string{}
	if ln, ok := l.loans[loanID]; ok {
		for _, i := range ln.inst {
			out = append(out, fmt.Sprintf("%d:%d", i.due, i.amount))
		}
	}
	return out
}

func (l *Lender) AmountDue(day int, loanID string) int {
	ln, ok := l.loans[loanID]
	if !ok {
		return -1
	}
	sum := 0
	for _, i := range ln.inst {
		if i.due <= day {
			sum += i.left()
		}
	}
	return sum
}

// ---------------------------------------------------------------- level 2

func (l *Lender) Pay(day int, loanID string, amount int) int {
	ln, ok := l.loans[loanID]
	if !ok || amount <= 0 {
		return -1
	}
	for _, i := range ln.inst {
		for _, part := range []*int{&i.fee, &i.interest, &i.principal} {
			take := min(amount, *part)
			*part -= take
			amount -= take
		}
	}
	return amount
}

func (l *Lender) Owed(day int, loanID string) int {
	ln, ok := l.loans[loanID]
	if !ok {
		return -1
	}
	sum := 0
	for _, i := range ln.inst {
		sum += i.left()
	}
	return sum
}

func (l *Lender) PrincipalLeft(day int, loanID string) int {
	ln, ok := l.loans[loanID]
	if !ok {
		return -1
	}
	sum := 0
	for _, i := range ln.inst {
		sum += i.principal
	}
	return sum
}

// ---------------------------------------------------------------- level 3

func (l *Lender) ChargeLateFees(day int) int {
	n := 0
	for _, ln := range l.loans {
		for _, i := range ln.inst {
			if i.due+graceDays < day && i.left() > 0 && !i.charged {
				i.charged = true
				i.fee += lateFee
				n++
			}
		}
	}
	return n
}

func (l *Lender) Status(day int, loanID string) string {
	ln, ok := l.loans[loanID]
	if !ok {
		return ""
	}
	paid, late := true, false
	for _, i := range ln.inst {
		if i.left() > 0 {
			paid = false
			if i.due+graceDays < day {
				late = true
			}
		}
	}
	if paid {
		return "paid_off"
	}
	if late {
		return "late"
	}
	return "current"
}

// ---------------------------------------------------------------- level 4

func (l *Lender) PayoffQuote(day int, loanID string) int {
	ln, ok := l.loans[loanID]
	if !ok {
		return -1
	}
	sum := 0
	for _, i := range ln.inst {
		sum += i.principal
		if i.due <= day {
			sum += i.fee + i.interest
		}
	}
	return sum
}

func (l *Lender) Restructure(day int, loanID string, months int) bool {
	ln, ok := l.loans[loanID]
	if !ok || months <= 0 {
		return false
	}
	var kept []*instalment
	rest, future := 0, 0
	for _, i := range ln.inst {
		if i.due <= day {
			kept = append(kept, i)
			continue
		}
		if i.left() != i.amount {
			return false
		}
		future++
		rest += i.principal
	}
	if future == 0 {
		return false
	}
	ln.inst = append(kept, instalments(day, rest, months, ln.rateBp)...)
	return true
}
