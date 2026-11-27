// Package wallets is the core of a multi-currency wallet app: balances per currency, published
// exchange rates with a fee, rate history with expiry, and standing conversion orders.
package wallets

import (
	"fmt"
	"sort"
)

const (
	scale      = 1_000_000 // a rate of 920_000 means 1 minor unit of source buys 0.92 minor units of target
	feePercent = 1
	rateTTL    = 100 // a rate published at t is in force until t + rateTTL (exclusive)
)

type pair struct{ source, target string }

type published struct{ ts, rate int }

type order struct {
	wallet, source, target string
	amount, minRate        int
	status                 string
}

// Wallets: every method takes ts first, the time of the call. Timestamps never decrease.
type Wallets struct {
	wallets map[string]map[string]int
	rates   map[pair][]published
	orders  map[string]*order
	ids     []string // order ids in creation order
}

// NewWallets returns an app with no wallets.
func NewWallets() *Wallets {
	return &Wallets{wallets: map[string]map[string]int{}, rates: map[pair][]published{}, orders: map[string]*order{}}
}

func isCode(c string) bool {
	if len(c) != 3 {
		return false
	}
	for i := 0; i < len(c); i++ {
		if c[i] < 'A' || c[i] > 'Z' {
			return false
		}
	}
	return true
}

func (w *Wallets) rateAt(source, target string, atTs int) int {
	rate := -1
	for _, p := range w.rates[pair{source, target}] {
		if p.ts <= atTs {
			if atTs < p.ts+rateTTL {
				rate = p.rate
			} else {
				rate = -1
			}
		}
	}
	return rate
}

func (w *Wallets) quoteAt(source, target string, amount, atTs int) int {
	if !isCode(source) || !isCode(target) || source == target || amount <= 0 {
		return -1
	}
	rate := w.rateAt(source, target, atTs)
	if rate < 0 {
		return -1
	}
	d := scale * 100
	return (amount*rate*(100-feePercent) + d/2) / d
}

// ---------------------------------------------------------------- level 1

func (w *Wallets) OpenWallet(ts int, walletID string) bool {
	if _, ok := w.wallets[walletID]; ok {
		return false
	}
	w.wallets[walletID] = map[string]int{}
	return true
}

func (w *Wallets) Deposit(ts int, walletID string, currency string, amount int) int {
	b, ok := w.wallets[walletID]
	if !ok || !isCode(currency) || amount <= 0 {
		return -1
	}
	b[currency] += amount
	return b[currency]
}

func (w *Wallets) Withdraw(ts int, walletID string, currency string, amount int) int {
	b, ok := w.wallets[walletID]
	if !ok || amount <= 0 || b[currency] < amount {
		return -1
	}
	b[currency] -= amount
	return b[currency]
}

func (w *Wallets) Balance(ts int, walletID string, currency string) int {
	b, ok := w.wallets[walletID]
	if !ok {
		return -1
	}
	return b[currency]
}

func (w *Wallets) Holdings(ts int, walletID string) []string {
	b := w.wallets[walletID]
	codes := []string{}
	for c, a := range b {
		if a > 0 {
			codes = append(codes, c)
		}
	}
	sort.Strings(codes)
	out := []string{}
	for _, c := range codes {
		out = append(out, fmt.Sprintf("%s:%d", c, b[c]))
	}
	return out
}

// ---------------------------------------------------------------- level 2

func (w *Wallets) SetRate(ts int, source string, target string, rate int) bool {
	if !isCode(source) || !isCode(target) || source == target || rate <= 0 {
		return false
	}
	k := pair{source, target}
	w.rates[k] = append(w.rates[k], published{ts, rate})
	for _, id := range w.ids {
		o := w.orders[id]
		if o.status == "open" && o.source == source && o.target == target && rate >= o.minRate {
			got := w.Convert(ts, o.wallet, source, target, o.amount)
			if got < 0 {
				o.status = "cancelled"
			} else {
				o.status = fmt.Sprintf("filled:%d", got)
			}
		}
	}
	return true
}

func (w *Wallets) Quote(ts int, source string, target string, amount int) int {
	return w.quoteAt(source, target, amount, ts)
}

func (w *Wallets) Convert(ts int, walletID string, source string, target string, amount int) int {
	b, ok := w.wallets[walletID]
	got := w.quoteAt(source, target, amount, ts)
	if !ok || got <= 0 || b[source] < amount {
		return -1
	}
	b[source] -= amount
	b[target] += got
	return got
}

func (w *Wallets) Transfer(ts int, sender string, receiver string, currency string, amount int) bool {
	s, okS := w.wallets[sender]
	r, okR := w.wallets[receiver]
	if !okS || !okR || sender == receiver || amount <= 0 || s[currency] < amount {
		return false
	}
	s[currency] -= amount
	r[currency] += amount
	return true
}

// ---------------------------------------------------------------- level 3

func (w *Wallets) QuoteAt(ts int, source string, target string, amount int, atTs int) int {
	return w.quoteAt(source, target, amount, atTs)
}

func (w *Wallets) TotalValue(ts int, walletID string, currency string) int {
	b, ok := w.wallets[walletID]
	if !ok || !isCode(currency) {
		return -1
	}
	total := 0
	for c, a := range b {
		if a == 0 {
			continue
		}
		v := a
		if c != currency {
			v = w.quoteAt(c, currency, a, ts)
		}
		if v < 0 {
			return -1
		}
		total += v
	}
	return total
}

// ---------------------------------------------------------------- level 4

func (w *Wallets) PlaceOrder(ts int, walletID string, source string, target string, amount int, minRate int) string {
	if _, ok := w.wallets[walletID]; !ok || !isCode(source) || !isCode(target) || source == target ||
		amount <= 0 || minRate <= 0 {
		return ""
	}
	id := fmt.Sprintf("o%d", len(w.ids)+1)
	w.orders[id] = &order{wallet: walletID, source: source, target: target, amount: amount, minRate: minRate, status: "open"}
	w.ids = append(w.ids, id)
	return id
}

func (w *Wallets) CancelOrder(ts int, orderID string) bool {
	o, ok := w.orders[orderID]
	if !ok || o.status != "open" {
		return false
	}
	o.status = "cancelled"
	return true
}

func (w *Wallets) OrderStatus(ts int, orderID string) string {
	o, ok := w.orders[orderID]
	if !ok {
		return ""
	}
	return o.status
}
