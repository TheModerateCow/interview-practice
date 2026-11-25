// Package loyalty is the points ledger for one member of a retail loyalty programme.
package loyalty

import "errors"

var (
	// ErrInvalidAmount is returned for a spend or a redemption that is zero or negative.
	ErrInvalidAmount = errors.New("amount must be positive")
	// ErrInsufficientPoints is returned when a redemption is larger than the usable balance.
	ErrInsufficientPoints = errors.New("not enough points")
)

const (
	silverFrom   = 50_000  // lifetime spend in cents
	goldFrom     = 200_000 // lifetime spend in cents
	capPerBuy    = 500     // points
	lifetimeDays = 365
)

type lot struct{ day, points int }

// Account is one member's ledger. Days passed to its methods never decrease.
type Account struct {
	spent int   // lifetime spend in cents
	lots  []lot // earned points, oldest first, minus what was redeemed
}

// NewAccount returns a member with no spend and no points.
func NewAccount() *Account { return &Account{} }

// Tier is "base", "silver" or "gold", from lifetime spend.
func (a *Account) Tier() string { return tierOf(a.spent) }

func tierOf(spent int) string {
	switch {
	case spent >= goldFrom:
		return "gold"
	case spent >= silverFrom:
		return "silver"
	}
	return "base"
}

// rate is the percentage of base points a member with this lifetime spend earns.
func rate(spent int) int {
	switch tierOf(spent) {
	case "gold":
		return 150
	case "silver":
		return 125
	}
	return 100
}

// Earn records a purchase of spendCents on day and returns the points it earned.
func (a *Account) Earn(day, spendCents int) (int, error) {
	if spendCents <= 0 {
		return 0, ErrInvalidAmount
	}
	pts := (spendCents*rate(a.spent) + 5_000) / 10_000
	pts = min(pts, capPerBuy)
	a.spent += spendCents
	if pts > 0 {
		a.lots = append(a.lots, lot{day, pts})
	}
	return pts, nil
}

func usable(l lot, day int) bool { return day < l.day+lifetimeDays }

// Balance is the number of points usable on day.
func (a *Account) Balance(day int) int {
	n := 0
	for _, l := range a.lots {
		if usable(l, day) {
			n += l.points
		}
	}
	return n
}

// Redeem spends points on day, oldest usable points first.
func (a *Account) Redeem(day, points int) error {
	if points <= 0 {
		return ErrInvalidAmount
	}
	if points > a.Balance(day) {
		return ErrInsufficientPoints
	}
	for i := range a.lots {
		if points == 0 {
			break
		}
		if !usable(a.lots[i], day) {
			continue
		}
		take := min(points, a.lots[i].points)
		a.lots[i].points -= take
		points -= take
	}
	return nil
}
