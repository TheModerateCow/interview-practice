package ledger

import (
	"fmt"
	"sort"
)

// Settle moves every charge of merchant whose funds are available at ts from pending to
// available, minus fees, as one batch per currency (sorted by currency code).
func (l *Ledger) Settle(merchant string, ts int64) ([]Batch, error) {
	pricing, ok := l.merchants[merchant]
	if !ok {
		return nil, fmt.Errorf("%w: %q", ErrUnknownMerchant, merchant)
	}
	if ts < l.store.headTS {
		return nil, ErrBackdated
	}
	due := l.charges.due(merchant, ts)
	if len(due) == 0 {
		return nil, nil
	}
	groups := map[string][]*Charge{}
	for _, c := range due {
		groups[c.Currency] = append(groups[c.Currency], c)
	}
	curs := make([]string, 0, len(groups))
	for cur := range groups {
		curs = append(curs, cur)
	}
	sort.Strings(curs)
	var out []Batch
	for _, cur := range curs {
		l.batchSeq++
		b := Batch{ID: fmt.Sprintf("b%d", l.batchSeq), Merchant: merchant, Currency: cur, TS: ts}
		for _, c := range groups[cur] {
			b.Charges = append(b.Charges, c.ID)
			b.Gross += c.Amount - c.Refunded
			b.Fees += pricing.fee(c.Amount, cur)
			c.Batch = b.ID
		}
		b.Net = b.Gross - b.Fees
		var ps []Posting
		for _, p := range []Posting{
			{PendingAccount(merchant), cur, -b.Gross},
			{AvailableAccount(merchant), cur, b.Net},
			{FeesAccount, cur, b.Fees},
		} {
			if p.Amount != 0 {
				ps = append(ps, p)
			}
		}
		if len(ps) > 0 {
			if _, err := l.Post(Entry{TS: ts, Memo: "settlement " + b.ID, Postings: ps}); err != nil {
				return out, err
			}
		}
		out = append(out, b)
	}
	return out, nil
}

// Pricing is what the platform charges a merchant on each settled charge: Bps basis
// points of the captured amount, rounded half up to a whole minor unit, plus a fixed fee
// per currency in that currency's minor units.
type Pricing struct {
	Bps   int64
	Fixed map[string]int64
}

// fee is the platform fee on one charge of amount minor units in cur.
func (p Pricing) fee(amount int64, cur string) int64 {
	return (amount*p.Bps+5000)/10000 + p.Fixed[cur]
}

// Batch is one settlement of a merchant's charges in one currency.
type Batch struct {
	ID       string
	Merchant string
	Currency string
	TS       int64
	Charges  []string // charge IDs, earliest AvailableOn first
	Gross    int64    // captured minus refunded, over the batch's charges
	Fees     int64
	Net      int64 // Gross - Fees, credited to the merchant's available balance
}
