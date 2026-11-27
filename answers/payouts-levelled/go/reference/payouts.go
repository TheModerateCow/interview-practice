// Package payouts is the settlement service for a marketplace: merchants, sales, refunds,
// payouts, a rolling reserve and chargebacks.
package payouts

import (
	"fmt"
	"sort"
)

const (
	settleDays    = 3
	chargebackFee = 1500
)

// fee in basis points, half a cent rounds up.
func fee(amount, bps int) int { return (amount*bps + 5000) / 10000 }

type entry struct {
	settle, amount int
	reserve        bool
}

type merchant struct {
	bps, reserveBps, hold int
	entries               []entry
	log, paid             []string
}

type sale struct {
	merchant              string
	amount, refunded, fee int
	chargedBack           bool
}

// Payouts: every method takes day first, today's date as an integer. Days never decrease.
type Payouts struct {
	merchants map[string]*merchant
	sales     map[string]*sale
	nextSale  int
}

// NewPayouts returns an empty service.
func NewPayouts() *Payouts {
	return &Payouts{merchants: map[string]*merchant{}, sales: map[string]*sale{}}
}

// post records a debit (refund, payout, chargeback): it counts at once.
func post(m *merchant, day int, kind string, amount int) {
	m.entries = append(m.entries, entry{day, amount, false})
	m.log = append(m.log, fmt.Sprintf("%d:%s:%d", day, kind, amount))
}

// ---------------------------------------------------------------- level 1

func (p *Payouts) AddMerchant(day int, merchantID string, feeBps int) bool {
	if _, ok := p.merchants[merchantID]; ok || feeBps < 0 || feeBps > 10000 {
		return false
	}
	p.merchants[merchantID] = &merchant{bps: feeBps}
	return true
}

func (p *Payouts) RecordSale(day int, merchantID string, amount int) string {
	m, ok := p.merchants[merchantID]
	if !ok || amount <= 0 {
		return ""
	}
	p.nextSale++
	id := fmt.Sprintf("s%d", p.nextSale)
	f := fee(amount, m.bps)
	net := amount - f
	reserve := fee(net, m.reserveBps)
	m.entries = append(m.entries, entry{day + settleDays, net - reserve, false})
	if reserve > 0 {
		m.entries = append(m.entries, entry{day + m.hold, reserve, true})
	}
	m.log = append(m.log, fmt.Sprintf("%d:sale:%d", day, net))
	p.sales[id] = &sale{merchant: merchantID, amount: amount, fee: f}
	return id
}

func (p *Payouts) Fee(day int, saleID string) int {
	s, ok := p.sales[saleID]
	if !ok {
		return -1
	}
	return s.fee
}

func (p *Payouts) Balance(day int, merchantID string) int {
	m, ok := p.merchants[merchantID]
	if !ok {
		return 0
	}
	total := 0
	for _, e := range m.entries {
		total += e.amount
	}
	return total
}

// ---------------------------------------------------------------- level 2

func (p *Payouts) Refund(day int, saleID string, amount int) int {
	s, ok := p.sales[saleID]
	if !ok || s.chargedBack || amount <= 0 || amount > s.amount-s.refunded {
		return -1
	}
	m := p.merchants[s.merchant]
	s.refunded += amount
	newFee := fee(s.amount-s.refunded, m.bps)
	debit := amount - (s.fee - newFee)
	s.fee = newFee
	post(m, day, "refund", -debit)
	return debit
}

func (p *Payouts) Activity(day int, merchantID string) []string {
	m, ok := p.merchants[merchantID]
	if !ok {
		return []string{}
	}
	return append([]string{}, m.log...)
}

// ---------------------------------------------------------------- level 3

func (p *Payouts) Available(day int, merchantID string) int {
	m, ok := p.merchants[merchantID]
	if !ok {
		return 0
	}
	total := 0
	for _, e := range m.entries {
		if e.settle <= day {
			total += e.amount
		}
	}
	return total
}

func (p *Payouts) RunPayouts(day int) []string {
	ids := make([]string, 0, len(p.merchants))
	for id := range p.merchants {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	out := []string{}
	for _, id := range ids {
		m := p.merchants[id]
		if a := p.Available(day, id); a > 0 {
			post(m, day, "payout", -a)
			m.paid = append(m.paid, fmt.Sprintf("%d:%d", day, a))
			out = append(out, fmt.Sprintf("%s:%d", id, a))
		}
	}
	return out
}

func (p *Payouts) PayoutHistory(day int, merchantID string) []string {
	m, ok := p.merchants[merchantID]
	if !ok {
		return []string{}
	}
	return append([]string{}, m.paid...)
}

// ---------------------------------------------------------------- level 4

func (p *Payouts) SetReserve(day int, merchantID string, reserveBps int, holdDays int) bool {
	m, ok := p.merchants[merchantID]
	if !ok || reserveBps < 0 || reserveBps > 10000 || holdDays < 1 {
		return false
	}
	m.reserveBps, m.hold = reserveBps, holdDays
	return true
}

func (p *Payouts) ReserveHeld(day int, merchantID string) int {
	m, ok := p.merchants[merchantID]
	if !ok {
		return 0
	}
	total := 0
	for _, e := range m.entries {
		if e.reserve && e.settle > day {
			total += e.amount
		}
	}
	return total
}

func (p *Payouts) Chargeback(day int, saleID string) int {
	s, ok := p.sales[saleID]
	if !ok || s.chargedBack || s.refunded == s.amount {
		return -1
	}
	s.chargedBack = true
	debit := s.amount - s.refunded + chargebackFee
	post(p.merchants[s.merchant], day, "chargeback", -debit)
	return debit
}
