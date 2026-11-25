package ledger

import "sort"

// chargeBook holds every captured charge, by ID and by merchant in capture order.
type chargeBook struct {
	byID       map[string]*Charge
	byMerchant map[string][]*Charge
}

func newChargeBook() *chargeBook {
	return &chargeBook{byID: map[string]*Charge{}, byMerchant: map[string][]*Charge{}}
}

func (b *chargeBook) add(c *Charge) {
	c.seq = len(b.byID)
	b.byID[c.ID] = c
	b.byMerchant[c.Merchant] = append(b.byMerchant[c.Merchant], c)
}

// due returns the merchant's unsettled charges whose funds are available at ts, earliest
// AvailableOn first (capture order breaks ties). A charge counts as settled once its
// Batch is set.
func (b *chargeBook) due(merchant string, ts int64) []*Charge {
	var out []*Charge
	for _, c := range b.byMerchant[merchant] {
		if c.Batch == "" && c.AvailableOn <= ts {
			out = append(out, c)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].before(out[j]) })
	return out
}

// Day is one day in ledger time (seconds).
const Day = 86400

// holds is how long captured funds wait before they can be settled, by payment method.
var holds = map[string]int64{"card": 2 * Day, "bank": 5 * Day}

// Charge is one captured payment to a merchant.
type Charge struct {
	ID          string
	Merchant    string
	Currency    string
	Method      string // "card" or "bank"
	Amount      int64  // captured amount, minor units
	Refunded    int64  // refunded so far, minor units
	CapturedAt  int64
	AvailableOn int64  // CapturedAt + the method's hold
	Batch       string // settlement batch that paid it out; empty until settled
	seq         int    // capture order
}

// before orders charges by AvailableOn, then capture order.
func (c *Charge) before(o *Charge) bool {
	if c.AvailableOn != o.AvailableOn {
		return c.AvailableOn < o.AvailableOn
	}
	return c.seq < o.seq
}

func (b *chargeBook) get(id string) (*Charge, bool) {
	c, ok := b.byID[id]
	return c, ok
}
