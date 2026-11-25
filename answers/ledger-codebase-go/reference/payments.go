package ledger

import "fmt"

// Capture books a captured payment: the platform is now owed amount by the card network
// or bank (clearing), and owes it to the merchant once it settles (pending).
func (l *Ledger) Capture(id, merchant, cur string, amount int64, method string, ts int64) (Charge, error) {
	if _, ok := l.merchants[merchant]; !ok {
		return Charge{}, fmt.Errorf("%w: %q", ErrUnknownMerchant, merchant)
	}
	hold, ok := holds[method]
	if !ok || amount <= 0 || id == "" {
		return Charge{}, fmt.Errorf("%w: capture %q", ErrInvalid, id)
	}
	if _, dup := l.charges.get(id); dup {
		return Charge{}, fmt.Errorf("%w: charge %q", ErrDuplicate, id)
	}
	_, err := l.Post(Entry{TS: ts, Memo: "capture " + id, Postings: []Posting{
		{ClearingAccount, cur, -amount},
		{PendingAccount(merchant), cur, amount},
	}})
	if err != nil {
		return Charge{}, err
	}
	c := &Charge{ID: id, Merchant: merchant, Currency: cur, Method: method, Amount: amount,
		CapturedAt: ts, AvailableOn: ts + hold}
	l.charges.add(c)
	return *c, nil
}

// Refund sends amount of a charge back to the customer. Before the charge settles the
// money comes out of the merchant's pending balance; after, out of available, which may
// go negative. Fees are not returned.
func (l *Ledger) Refund(chargeID string, amount, ts int64) error {
	c, ok := l.charges.get(chargeID)
	if !ok {
		return fmt.Errorf("%w: charge %q", ErrNotFound, chargeID)
	}
	if amount <= 0 || amount > c.Amount-c.Refunded {
		return fmt.Errorf("%w: refund %d of %q", ErrInvalid, amount, chargeID)
	}
	from := PendingAccount(c.Merchant)
	if c.Batch != "" {
		from = AvailableAccount(c.Merchant)
	}
	_, err := l.Post(Entry{TS: ts, Memo: "refund " + chargeID, Postings: []Posting{
		{from, c.Currency, -amount},
		{ClearingAccount, c.Currency, amount},
	}})
	if err != nil {
		return err
	}
	c.Refunded += amount
	return nil
}

// Charge returns a copy of the charge with this ID.
func (l *Ledger) Charge(id string) (Charge, bool) {
	c, ok := l.charges.get(id)
	if !ok {
		return Charge{}, false
	}
	return *c, true
}
