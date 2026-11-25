package ledger

import (
	"sort"
	"strconv"
)

// bucket is one account's balance in one currency.
type bucket struct{ account, currency string }

// Line is one posting as it appears on an account statement.
type Line struct {
	TS      int64
	EntryID string
	Amount  int64
	Balance int64 // the account's balance right after this posting
}

// store is the in-memory journal: every entry in posting order, plus a per-account index of
// lines with running balances so balance queries don't replay the journal.
type store struct {
	entries []Entry
	lines   map[bucket][]Line
	headTS  int64
	payouts map[string]*Payout
}

func newStore() *store {
	return &store{lines: map[bucket][]Line{}, payouts: map[string]*Payout{}}
}

// append records an already-validated entry and returns it with its ID set.
func (s *store) append(e Entry) Entry {
	e.ID = "e" + strconv.Itoa(len(s.entries)+1)
	s.entries = append(s.entries, e)
	for _, p := range e.Postings {
		b := bucket{p.Account, p.Currency}
		ls := s.lines[b]
		bal := p.Amount
		if n := len(ls); n > 0 {
			bal += ls[n-1].Balance
		}
		s.lines[b] = append(ls, Line{TS: e.TS, EntryID: e.ID, Amount: p.Amount, Balance: bal})
	}
	s.headTS = e.TS
	return e
}

// history returns an account's lines, oldest first.
func (s *store) history(b bucket) []Line {
	return s.lines[b]
}

// balanceAt returns the account's balance after every posting with TS <= ts.
func (s *store) balanceAt(b bucket, ts int64) int64 {
	ls := s.lines[b]
	i := sort.Search(len(ls), func(i int) bool { return ls[i].TS > ts })
	if i == 0 {
		return 0
	}
	return ls[i-1].Balance
}

// balance returns the account's current balance.
func (s *store) balance(b bucket) int64 {
	ls := s.lines[b]
	if len(ls) == 0 {
		return 0
	}
	return ls[len(ls)-1].Balance
}

// updatePayout runs fn on a copy of the stored payout and keeps the copy only if fn
// succeeds, so a rejected transition leaves the payout as it was.
func (s *store) updatePayout(id string, fn func(p *Payout) error) error {
	p, ok := s.payouts[id]
	if !ok {
		return ErrNotFound
	}
	next := *p
	if err := fn(&next); err != nil {
		return err
	}
	p = &next
	return nil
}
