// Package billing tracks one customer's per-seat SaaS subscription: renewals, mid-cycle changes and credit.
package billing

import "errors"

var (
	// ErrUnknownPlan is returned for a plan name that isn't in the price list.
	ErrUnknownPlan = errors.New("unknown plan")
	// ErrUnknownCycle is returned for a billing cycle other than "monthly" or "annual".
	ErrUnknownCycle = errors.New("unknown billing cycle")
	// ErrInvalidSeats is returned for a seat count outside 1..500.
	ErrInvalidSeats = errors.New("seats must be 1 to 500")
	// ErrOutsidePeriod is returned for a change on a day outside the current billing period.
	ErrOutsidePeriod = errors.New("day is outside the current period")
)

const maxSeats = 500

// Per-seat price of one period, in cents.
var prices = map[string]map[string]int{
	"monthly": {"starter": 1_299, "team": 2_499, "business": 5_999},
	"annual":  {"starter": 12_990, "team": 24_990, "business": 59_990},
}

var cycleDays = map[string]int{"monthly": 30, "annual": 360}

// Subscription is one customer's subscription. The first period is paid when it is created.
type Subscription struct {
	cycle      string
	plan       string
	seats      int
	start, end int
	credit     int
}

// New starts a subscription on day; its first period runs from day to day + cycle length.
func New(day int, plan, cycle string, seats int) (*Subscription, error) {
	days, ok := cycleDays[cycle]
	if !ok {
		return nil, ErrUnknownCycle
	}
	if err := check(cycle, plan, seats); err != nil {
		return nil, err
	}
	return &Subscription{cycle: cycle, plan: plan, seats: seats, start: day, end: day + days}, nil
}

func check(cycle, plan string, seats int) error {
	if _, ok := prices[cycle][plan]; !ok {
		return ErrUnknownPlan
	}
	if seats < 1 || seats > maxSeats {
		return ErrInvalidSeats
	}
	return nil
}

// PeriodPrice is the full price of one period for the current plan and seats, in cents.
func (s *Subscription) PeriodPrice() int {
	return prices[s.cycle][s.plan] * s.seats
}

// PeriodEnd is the first day of the next period.
func (s *Subscription) PeriodEnd() int { return s.end }

// Credit is the unused credit balance, in cents.
func (s *Subscription) Credit() int { return s.credit }

// pay applies credit to a charge and returns what is left to charge.
func (s *Subscription) pay(amount int) int {
	used := min(amount, s.credit)
	s.credit -= used
	return amount - used
}

// Change moves to plan and seats on day and returns the cents charged now.
func (s *Subscription) Change(day int, plan string, seats int) (int, error) {
	if day < s.start || day >= s.end {
		return 0, ErrOutsidePeriod
	}
	if err := check(s.cycle, plan, seats); err != nil {
		return 0, err
	}
	old := s.PeriodPrice()
	s.plan, s.seats = plan, seats
	diff, left, length := s.PeriodPrice()-old, s.end-day, s.end-s.start
	if diff > 0 {
		return s.pay((diff*left + length/2) / length), nil
	}
	s.credit += (-diff) * left / length
	return 0, nil
}

// Renew starts the next period at PeriodEnd and returns the cents charged for it.
func (s *Subscription) Renew() int {
	length := s.end - s.start
	s.start, s.end = s.end, s.end+length
	return s.pay(s.PeriodPrice())
}
