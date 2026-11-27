// Package cards is a card issuer's authorisation service: cards with credit limits, holds that
// are captured, voided or expire, refunds and statements, per-category daily limits and frozen cards.
package cards

import "fmt"

const holdDays = 7

type card struct {
	limit     int
	frozen    bool
	catLimits map[string]int
	entries   []string
}

type auth struct {
	id, card, category string
	amount, day        int
	status             string // open, captured, voided
	captured, refunded int
}

// Issuer: every method takes day first, today's date as an integer. Days never decrease.
type Issuer struct {
	cards map[string]*card
	auths map[string]*auth
	order []*auth // in approval (id) order
}

// NewIssuer returns an issuer with no cards.
func NewIssuer() *Issuer {
	return &Issuer{cards: map[string]*card{}, auths: map[string]*auth{}}
}

// status is open, captured, voided or expired: an open hold expires holdDays days after approval.
func status(day int, a *auth) string {
	if a.status == "open" && day >= a.day+holdDays {
		return "expired"
	}
	return a.status
}

func (s *Issuer) held(day int, cardID string) int {
	total := 0
	for _, a := range s.order {
		if a.card == cardID && status(day, a) == "open" {
			total += a.amount
		}
	}
	return total
}

func (s *Issuer) posted(cardID string) int {
	total := 0
	for _, a := range s.order {
		if a.card == cardID {
			total += a.captured - a.refunded
		}
	}
	return total
}

// spent is today's spending in a category: open holds at their amount, captures at what was captured.
func (s *Issuer) spent(day int, cardID, category string) int {
	total := 0
	for _, a := range s.order {
		if a.card == cardID && a.category == category && a.day == day {
			switch status(day, a) {
			case "open":
				total += a.amount
			case "captured":
				total += a.captured
			}
		}
	}
	return total
}

// ---------------------------------------------------------------- level 1

func (s *Issuer) IssueCard(day int, cardID string, limit int) bool {
	if _, ok := s.cards[cardID]; ok || limit <= 0 {
		return false
	}
	s.cards[cardID] = &card{limit: limit, catLimits: map[string]int{}}
	return true
}

func (s *Issuer) Authorize(day int, cardID string, category string, amount int) string {
	c, ok := s.cards[cardID]
	if !ok || c.frozen || amount <= 0 || amount > s.Available(day, cardID) {
		return ""
	}
	if lim, ok := c.catLimits[category]; ok && s.spent(day, cardID, category)+amount > lim {
		return ""
	}
	a := &auth{id: fmt.Sprintf("a%d", len(s.order)+1), card: cardID, category: category,
		amount: amount, day: day, status: "open"}
	s.auths[a.id] = a
	s.order = append(s.order, a)
	return a.id
}

func (s *Issuer) Capture(day int, authID string, amount int) bool {
	a, ok := s.auths[authID]
	if !ok || status(day, a) != "open" || amount <= 0 || amount > a.amount {
		return false
	}
	a.status = "captured"
	a.captured = amount
	c := s.cards[a.card]
	c.entries = append(c.entries, fmt.Sprintf("%d:%s:charge:%d", day, authID, amount))
	return true
}

func (s *Issuer) VoidAuth(day int, authID string) bool {
	a, ok := s.auths[authID]
	if !ok || status(day, a) != "open" {
		return false
	}
	a.status = "voided"
	return true
}

func (s *Issuer) Available(day int, cardID string) int {
	c, ok := s.cards[cardID]
	if !ok {
		return -1
	}
	return c.limit - s.posted(cardID) - s.held(day, cardID)
}

// ---------------------------------------------------------------- level 2

func (s *Issuer) Holds(day int, cardID string) []string {
	out := []string{}
	for _, a := range s.order {
		if a.card == cardID && status(day, a) == "open" {
			out = append(out, fmt.Sprintf("%s:%d", a.id, a.amount))
		}
	}
	return out
}

func (s *Issuer) AuthStatus(day int, authID string) string {
	a, ok := s.auths[authID]
	if !ok {
		return ""
	}
	return status(day, a)
}

// ---------------------------------------------------------------- level 3

func (s *Issuer) Refund(day int, authID string, amount int) bool {
	a, ok := s.auths[authID]
	if !ok || a.status != "captured" || amount <= 0 || amount > a.captured-a.refunded {
		return false
	}
	a.refunded += amount
	c := s.cards[a.card]
	c.entries = append(c.entries, fmt.Sprintf("%d:%s:refund:%d", day, authID, amount))
	return true
}

func (s *Issuer) Balance(day int, cardID string) int {
	if _, ok := s.cards[cardID]; !ok {
		return -1
	}
	return s.posted(cardID)
}

func (s *Issuer) Statement(day int, cardID string) []string {
	c, ok := s.cards[cardID]
	if !ok {
		return []string{}
	}
	return append([]string{}, c.entries...)
}

// ---------------------------------------------------------------- level 4

func (s *Issuer) SetCategoryLimit(day int, cardID string, category string, limit int) bool {
	c, ok := s.cards[cardID]
	if !ok || limit < 0 {
		return false
	}
	c.catLimits[category] = limit
	return true
}

func (s *Issuer) Freeze(day int, cardID string) bool {
	c, ok := s.cards[cardID]
	if !ok || c.frozen {
		return false
	}
	c.frozen = true
	return true
}

func (s *Issuer) Unfreeze(day int, cardID string) bool {
	c, ok := s.cards[cardID]
	if !ok || !c.frozen {
		return false
	}
	c.frozen = false
	return true
}
