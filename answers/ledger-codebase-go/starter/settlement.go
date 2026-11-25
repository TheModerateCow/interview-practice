package ledger

// Settle moves every charge of merchant whose funds are available at ts from pending to
// available, minus fees, as one batch per currency (sorted by currency code).
func (l *Ledger) Settle(merchant string, ts int64) ([]Batch, error) {
	panic("not implemented")
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
