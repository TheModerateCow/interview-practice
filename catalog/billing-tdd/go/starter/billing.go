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

// Subscription is one customer's subscription. The first period is paid when it is created.
type Subscription struct {
	// your state here
}

// NewSubscription returns an empty subscription; call Start before anything else.
func NewSubscription() *Subscription {
	return &Subscription{}
}

// Start begins the subscription on day; its first period runs from day to day + cycle length.
func (s *Subscription) Start(day int, plan, cycle string, seats int) error {
	panic("not implemented")
}

// PeriodPrice is the full price of one period for the current plan and seats, in cents.
func (s *Subscription) PeriodPrice() int {
	panic("not implemented")
}

// PeriodEnd is the first day of the next period.
func (s *Subscription) PeriodEnd() int {
	panic("not implemented")
}

// Credit is the unused credit balance, in cents.
func (s *Subscription) Credit() int {
	panic("not implemented")
}

// Change moves to plan and seats on day and returns the cents charged now.
func (s *Subscription) Change(day int, plan string, seats int) (int, error) {
	panic("not implemented")
}

// Renew starts the next period at PeriodEnd and returns the cents charged for it.
func (s *Subscription) Renew() int {
	panic("not implemented")
}
