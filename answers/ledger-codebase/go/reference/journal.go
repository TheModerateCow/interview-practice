package ledger

import (
	"errors"
	"fmt"
)

// Account names used by the payment flows. Balances are signed: a positive merchant
// balance is money the platform owes that merchant.
const (
	ClearingAccount  = "platform:clearing"           // funds due from card networks and banks
	FeesAccount      = "platform:fees"               // platform revenue
	InTransitAccount = "platform:payouts-in-transit" // payouts sent, not yet confirmed by the bank
	BankAccount      = "platform:bank-paid-out"      // payouts the bank confirmed
)

// PendingAccount holds a merchant's captured funds that have not been settled yet.
func PendingAccount(merchant string) string { return "merchant:" + merchant + ":pending" }

// AvailableAccount holds a merchant's settled funds, ready to be paid out.
func AvailableAccount(merchant string) string { return "merchant:" + merchant + ":available" }

var (
	ErrInvalid           = errors.New("invalid request")
	ErrUnbalanced        = errors.New("entry does not balance")
	ErrUnknownCurrency   = errors.New("unknown currency")
	ErrBackdated         = errors.New("entry is older than the ledger head")
	ErrNotFound          = errors.New("not found")
	ErrDuplicate         = errors.New("already exists")
	ErrUnknownMerchant   = errors.New("unknown merchant")
	ErrInsufficientFunds = errors.New("insufficient available balance")
	ErrPayoutState       = errors.New("payout cannot make that transition")
)

// Posting moves Amount minor units of Currency into (positive) or out of (negative) Account.
type Posting struct {
	Account  string
	Currency string
	Amount   int64
}

// Entry is one double-entry journal entry. ID is assigned when the entry is posted.
type Entry struct {
	ID       string
	TS       int64
	Memo     string
	Postings []Posting
}

// validate checks that e is a well-formed double entry: at least two postings, no empty
// accounts or zero amounts, only booked currencies, and debits equal to credits.
func (e Entry) validate() error {
	if len(e.Postings) < 2 {
		return fmt.Errorf("%w: an entry needs at least two postings", ErrInvalid)
	}
	sums := map[string]int64{}
	for _, p := range e.Postings {
		if p.Account == "" || p.Amount == 0 {
			return fmt.Errorf("%w: empty account or zero amount", ErrInvalid)
		}
		if !ValidCurrency(p.Currency) {
			return fmt.Errorf("%w: %q", ErrUnknownCurrency, p.Currency)
		}
		sums[p.Currency] += p.Amount
	}
	for _, p := range e.Postings {
		if sum := sums[p.Currency]; sum != 0 {
			return fmt.Errorf("%w: off by %s", ErrUnbalanced, Format(sum, p.Currency))
		}
	}
	return nil
}
