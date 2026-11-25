package ledger

import "fmt"

// PayoutStatus is where a payout is in its life: pending until the bank's webhook says
// it was paid or it failed.
type PayoutStatus string

const (
	PayoutPending PayoutStatus = "pending"
	PayoutPaid    PayoutStatus = "paid"
	PayoutFailed  PayoutStatus = "failed"
)

// Payout is a transfer of a merchant's available funds to their bank account.
type Payout struct {
	ID        string
	Merchant  string
	Currency  string
	Amount    int64
	Status    PayoutStatus
	UpdatedAt int64
}

// RequestPayout moves amount from the merchant's available balance to in-transit.
func (l *Ledger) RequestPayout(id, merchant, cur string, amount, ts int64) (Payout, error) {
	if id == "" || amount <= 0 {
		return Payout{}, fmt.Errorf("%w: payout %q", ErrInvalid, id)
	}
	if _, ok := l.store.payouts[id]; ok {
		return Payout{}, fmt.Errorf("%w: payout %q", ErrDuplicate, id)
	}
	if l.Balance(AvailableAccount(merchant), cur) < amount {
		return Payout{}, ErrInsufficientFunds
	}
	_, err := l.Post(Entry{TS: ts, Memo: "payout " + id, Postings: []Posting{
		{AvailableAccount(merchant), cur, -amount},
		{InTransitAccount, cur, amount},
	}})
	if err != nil {
		return Payout{}, err
	}
	p := &Payout{ID: id, Merchant: merchant, Currency: cur, Amount: amount, Status: PayoutPending, UpdatedAt: ts}
	l.store.payouts[id] = p
	return *p, nil
}

// PayoutPaid handles the bank's "paid" webhook. The bank retries webhooks, so a repeat
// of the same outcome is accepted and changes nothing.
func (l *Ledger) PayoutPaid(id string, ts int64) error { return l.finishPayout(id, PayoutPaid, ts) }

// PayoutFailed handles the bank's "failed" webhook: the money goes back to available.
// Repeats are accepted and change nothing.
func (l *Ledger) PayoutFailed(id string, ts int64) error { return l.finishPayout(id, PayoutFailed, ts) }

func (l *Ledger) finishPayout(id string, to PayoutStatus, ts int64) error {
	return l.store.updatePayout(id, func(p *Payout) error {
		if p.Status == to {
			return nil
		}
		if p.Status != PayoutPending {
			return fmt.Errorf("%w: %s payout %q cannot become %s", ErrPayoutState, p.Status, id, to)
		}
		dest := BankAccount
		if to == PayoutFailed {
			dest = AvailableAccount(p.Merchant)
		}
		_, err := l.Post(Entry{TS: ts, Memo: fmt.Sprintf("payout %s %s", id, to), Postings: []Posting{
			{InTransitAccount, p.Currency, -p.Amount},
			{dest, p.Currency, p.Amount},
		}})
		if err != nil {
			return err
		}
		p.Status, p.UpdatedAt = to, ts
		return nil
	})
}

// Payout returns a copy of the payout with this ID.
func (l *Ledger) Payout(id string) (Payout, bool) {
	p, ok := l.store.payouts[id]
	if !ok {
		return Payout{}, false
	}
	return *p, true
}
