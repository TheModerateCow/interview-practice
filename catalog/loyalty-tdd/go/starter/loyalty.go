// Package loyalty is the points ledger for one member of a retail loyalty programme.
package loyalty

import "errors"

var (
	// ErrInvalidAmount is returned for a spend or a redemption that is zero or negative.
	ErrInvalidAmount = errors.New("amount must be positive")
	// ErrInsufficientPoints is returned when a redemption is larger than the usable balance.
	ErrInsufficientPoints = errors.New("not enough points")
)

// Account is one member's ledger. Days passed to its methods never decrease.
type Account struct {
	// your state here
}

// NewAccount returns a member with no spend and no points.
func NewAccount() *Account {
	return &Account{}
}

// Earn records a purchase of spendCents on day and returns the points it earned.
func (a *Account) Earn(day, spendCents int) (int, error) {
	panic("not implemented")
}

// Balance is the number of points usable on day.
func (a *Account) Balance(day int) int {
	panic("not implemented")
}

// Redeem spends points on day, oldest usable points first.
func (a *Account) Redeem(day, points int) error {
	panic("not implemented")
}

// Tier is "base", "silver" or "gold", from lifetime spend.
func (a *Account) Tier() string {
	panic("not implemented")
}
