// Package fixture is the reference for the harness fixture.
package fixture

import (
	"errors"
	"fmt"
	"sort"
)

var (
	ErrInvalidAmount     = errors.New("invalid amount")
	ErrInsufficientFunds = errors.New("insufficient funds")
	ErrInvalidWindow     = errors.New("invalid window")
	ErrWalletFrozen      = errors.New("wallet frozen")
)

type Entry struct {
	AccountID   string
	AmountCents int
}

func NetByAccount(entries []Entry) []Entry {
	tot := map[string]int{}
	for _, e := range entries {
		tot[e.AccountID] += e.AmountCents
	}
	out := make([]Entry, 0, len(tot))
	for a, v := range tot {
		out = append(out, Entry{a, v})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].AccountID < out[j].AccountID })
	return out
}

func MaxWindow(values []int, k int) (int, error) {
	if k < 1 || k > len(values) {
		return 0, fmt.Errorf("%w: k=%d", ErrInvalidWindow, k)
	}
	s := 0
	for _, v := range values[:k] {
		s += v
	}
	best := s
	for i := k; i < len(values); i++ {
		s += values[i] - values[i-k]
		best = max(best, s)
	}
	return best, nil
}

func FirstNegative(values []int) (int, bool) {
	for i, v := range values {
		if v < 0 {
			return i, true
		}
	}
	return 0, false
}

func Grid(n int) [][]int {
	g := make([][]int, n)
	for r := range g {
		g[r] = make([]int, n)
		for c := range g[r] {
			g[r][c] = r*n + c + 1
		}
	}
	return g
}

type Wallet struct {
	owner  string
	bal    int
	hist   []string
	frozen bool
}

func NewWallet(owner string) *Wallet { return &Wallet{owner: owner} }

func (w *Wallet) check(cents int) error {
	if w.frozen {
		return ErrWalletFrozen
	}
	if cents <= 0 {
		return fmt.Errorf("%w: %d", ErrInvalidAmount, cents)
	}
	return nil
}

func (w *Wallet) Deposit(cents int) error {
	if err := w.check(cents); err != nil {
		return err
	}
	w.bal += cents
	w.hist = append(w.hist, fmt.Sprintf("+%d", cents))
	return nil
}

func (w *Wallet) Withdraw(cents int) (int, error) {
	if err := w.check(cents); err != nil {
		return 0, err
	}
	if cents > w.bal {
		return 0, fmt.Errorf("%w: %d", ErrInsufficientFunds, cents)
	}
	w.bal -= cents
	w.hist = append(w.hist, fmt.Sprintf("-%d", cents))
	return w.bal, nil
}

func (w *Wallet) Balance() int      { return w.bal }
func (w *Wallet) OwnerName() string { return w.owner }

// History lists "+<cents>" / "-<cents>" per successful deposit/withdrawal.
func (w *Wallet) History() []string { return append([]string(nil), w.hist...) }
func (w *Wallet) Freeze()           { w.frozen = true }
func (w *Wallet) Frozen() bool      { return w.frozen }
