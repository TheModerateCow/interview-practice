// Package ledger is the merchant ledger of a payment platform: it books captured payments,
// refunds, settlement batches and payouts as balanced double entries in integer minor units.
package ledger

import (
	"fmt"
	"slices"
)

// Ledger is the service the payment flows call. It is not safe for concurrent use.
type Ledger struct {
	store     *store
	charges   *chargeBook
	merchants map[string]Pricing
	batchSeq  int
}

// New returns an empty ledger.
func New() *Ledger {
	return &Ledger{store: newStore(), charges: newChargeBook(), merchants: map[string]Pricing{}}
}

// AddMerchant onboards a merchant with its pricing.
func (l *Ledger) AddMerchant(id string, p Pricing) error {
	if id == "" || p.Bps < 0 {
		return ErrInvalid
	}
	if _, ok := l.merchants[id]; ok {
		return fmt.Errorf("%w: merchant %q", ErrDuplicate, id)
	}
	l.merchants[id] = p
	return nil
}

// Post validates and books a journal entry. Entries must arrive in time order.
func (l *Ledger) Post(e Entry) (Entry, error) {
	if err := e.validate(); err != nil {
		return Entry{}, err
	}
	if e.TS < l.store.headTS {
		return Entry{}, ErrBackdated
	}
	e.Postings = append([]Posting(nil), e.Postings...)
	return l.store.append(e), nil
}

// Balance returns the current balance of account in cur.
func (l *Ledger) Balance(account, cur string) int64 {
	return l.store.balance(bucket{account, cur})
}

// BalanceAt returns the balance of account in cur as of time ts (inclusive).
func (l *Ledger) BalanceAt(account, cur string, ts int64) int64 {
	return l.store.balanceAt(bucket{account, cur}, ts)
}

// Statement lists the account's lines with from <= TS <= to, newest first, as the
// merchant dashboard shows them.
func (l *Ledger) Statement(account, cur string, from, to int64) []Line {
	ls := l.store.history(bucket{account, cur})
	slices.Reverse(ls)
	var out []Line
	for _, x := range ls {
		if x.TS >= from && x.TS <= to {
			out = append(out, x)
		}
	}
	return out
}

// TrialBalance sums every account's balance in cur. A healthy ledger always returns 0.
func (l *Ledger) TrialBalance(cur string) int64 {
	var sum int64
	for b := range l.store.lines {
		if b.currency == cur {
			sum += l.store.balance(b)
		}
	}
	return sum
}
