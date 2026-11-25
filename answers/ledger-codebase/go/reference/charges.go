package ledger

import "container/heap"

// chargeBook holds every captured charge by ID, plus each merchant's unsettled charges
// in a min-heap keyed on when their funds become available.
type chargeBook struct {
	byID    map[string]*Charge
	pending map[string]*dueQueue
}

func newChargeBook() *chargeBook {
	return &chargeBook{byID: map[string]*Charge{}, pending: map[string]*dueQueue{}}
}

func (b *chargeBook) add(c *Charge) {
	c.seq = len(b.byID)
	b.byID[c.ID] = c
	q := b.pending[c.Merchant]
	if q == nil {
		q = &dueQueue{}
		b.pending[c.Merchant] = q
	}
	heap.Push(q, c)
}

// due returns the merchant's unsettled charges whose funds are available at ts, earliest
// AvailableOn first (capture order breaks ties). It takes them off the merchant's pending set.
func (b *chargeBook) due(merchant string, ts int64) []*Charge {
	q := b.pending[merchant]
	var out []*Charge
	for q != nil && q.Len() > 0 && (*q)[0].AvailableOn <= ts {
		out = append(out, heap.Pop(q).(*Charge))
	}
	return out
}

// dueQueue implements heap.Interface over charges, ordered by Charge.before.
type dueQueue []*Charge

func (q dueQueue) Len() int           { return len(q) }
func (q dueQueue) Less(i, j int) bool { return q[i].before(q[j]) }
func (q dueQueue) Swap(i, j int)      { q[i], q[j] = q[j], q[i] }
func (q *dueQueue) Push(x any)        { *q = append(*q, x.(*Charge)) }
func (q *dueQueue) Pop() any {
	old := *q
	c := old[len(old)-1]
	*q = old[:len(old)-1]
	return c
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
