// Package bank is the in-memory core of a retail bank: accounts, money movement, rankings,
// scheduled payments, merges and balance history.
package bank

import (
	"fmt"
	"sort"
	"strconv"
)

type account struct {
	balance int
	spent   int // withdrawals, transfers sent and scheduled payments made
}

// change is one point in an account id's balance history.
type change struct {
	ts      int
	balance int
	open    bool
}

type payment struct {
	account string
	amount  int
	due     int
	status  string
}

// Bank holds accounts by id. Timestamps passed to its methods only ever increase.
type Bank struct {
	accounts map[string]*account
	history  map[string][]change
	payments []*payment // in the order they were scheduled
	byID     map[string]*payment
}

// NewBank returns a bank with no accounts.
func NewBank() *Bank {
	return &Bank{accounts: map[string]*account{}, history: map[string][]change{}, byID: map[string]*payment{}}
}

func (b *Bank) record(ts int, id string) {
	a, open := b.accounts[id]
	c := change{ts: ts, open: open}
	if open {
		c.balance = a.balance
	}
	b.history[id] = append(b.history[id], c)
}

// settle runs every pending payment due at or before ts, earliest due first, ties in schedule order.
func (b *Bank) settle(ts int) {
	var due []*payment
	for _, p := range b.payments {
		if p.status == "pending" && p.due <= ts {
			due = append(due, p)
		}
	}
	sort.SliceStable(due, func(i, j int) bool { return due[i].due < due[j].due })
	for _, p := range due {
		a, ok := b.accounts[p.account]
		if !ok || a.balance < p.amount {
			p.status = "failed"
			continue
		}
		a.balance -= p.amount
		a.spent += p.amount
		p.status = "paid"
		b.record(p.due, p.account)
	}
}

// OpenAccount creates an empty account. False if the id is already open.
func (b *Bank) OpenAccount(ts int, id string) bool {
	b.settle(ts)
	if _, ok := b.accounts[id]; ok {
		return false
	}
	b.accounts[id] = &account{}
	b.record(ts, id)
	return true
}

// Deposit adds amount to the account and returns the new balance.
func (b *Bank) Deposit(ts int, id string, amount int) (int, bool) {
	b.settle(ts)
	a, ok := b.accounts[id]
	if !ok {
		return 0, false
	}
	a.balance += amount
	b.record(ts, id)
	return a.balance, true
}

// Withdraw takes amount out of the account and returns the new balance.
func (b *Bank) Withdraw(ts int, id string, amount int) (int, bool) {
	b.settle(ts)
	a, ok := b.accounts[id]
	if !ok || a.balance < amount {
		return 0, false
	}
	a.balance -= amount
	a.spent += amount
	b.record(ts, id)
	return a.balance, true
}

// Transfer moves amount between two different accounts and returns the sender's new balance.
func (b *Bank) Transfer(ts int, from, to string, amount int) (int, bool) {
	b.settle(ts)
	src, ok1 := b.accounts[from]
	dst, ok2 := b.accounts[to]
	if !ok1 || !ok2 || from == to || src.balance < amount {
		return 0, false
	}
	src.balance -= amount
	src.spent += amount
	dst.balance += amount
	b.record(ts, from)
	b.record(ts, to)
	return src.balance, true
}

// Balance returns the account's balance.
func (b *Bank) Balance(ts int, id string) (int, bool) {
	b.settle(ts)
	a, ok := b.accounts[id]
	if !ok {
		return 0, false
	}
	return a.balance, true
}

// TopSpenders returns up to n open accounts as "id:spent", most spent first, ties by id.
func (b *Bank) TopSpenders(ts int, n int) []string {
	b.settle(ts)
	ids := make([]string, 0, len(b.accounts))
	for id := range b.accounts {
		ids = append(ids, id)
	}
	sort.Slice(ids, func(i, j int) bool {
		si, sj := b.accounts[ids[i]].spent, b.accounts[ids[j]].spent
		if si != sj {
			return si > sj
		}
		return ids[i] < ids[j]
	})
	if n < len(ids) {
		ids = ids[:n]
	}
	out := make([]string, 0, len(ids))
	for _, id := range ids {
		out = append(out, fmt.Sprintf("%s:%d", id, b.accounts[id].spent))
	}
	return out
}

// AccountsAbove returns every open account holding at least min, as "id:balance",
// largest balance first, ties by id.
func (b *Bank) AccountsAbove(ts int, min int) []string {
	b.settle(ts)
	ids := []string{}
	for id, a := range b.accounts {
		if a.balance >= min {
			ids = append(ids, id)
		}
	}
	sort.Slice(ids, func(i, j int) bool {
		bi, bj := b.accounts[ids[i]].balance, b.accounts[ids[j]].balance
		if bi != bj {
			return bi > bj
		}
		return ids[i] < ids[j]
	})
	out := make([]string, 0, len(ids))
	for _, id := range ids {
		out = append(out, fmt.Sprintf("%s:%d", id, b.accounts[id].balance))
	}
	return out
}

// SchedulePayment books a payment of amount out of the account, due delay after ts.
// Returns its id: "pay1", "pay2", ...
func (b *Bank) SchedulePayment(ts int, id string, amount, delay int) (string, bool) {
	b.settle(ts)
	if _, ok := b.accounts[id]; !ok {
		return "", false
	}
	p := &payment{account: id, amount: amount, due: ts + delay, status: "pending"}
	b.payments = append(b.payments, p)
	pid := "pay" + strconv.Itoa(len(b.payments))
	b.byID[pid] = p
	return pid, true
}

// CancelPayment cancels a pending payment that draws on the account.
func (b *Bank) CancelPayment(ts int, id, paymentID string) bool {
	b.settle(ts)
	p, ok := b.byID[paymentID]
	if !ok || p.status != "pending" || p.account != id {
		return false
	}
	p.status = "cancelled"
	return true
}

// PaymentStatus is "pending", "paid", "failed" or "cancelled"; "" for an unknown id.
func (b *Bank) PaymentStatus(ts int, paymentID string) string {
	b.settle(ts)
	if p, ok := b.byID[paymentID]; ok {
		return p.status
	}
	return ""
}

// MergeAccounts folds absorb into keep: balance, spending and pending payments. absorb is closed.
func (b *Bank) MergeAccounts(ts int, keep, absorb string) bool {
	b.settle(ts)
	k, ok1 := b.accounts[keep]
	a, ok2 := b.accounts[absorb]
	if !ok1 || !ok2 || keep == absorb {
		return false
	}
	k.balance += a.balance
	k.spent += a.spent
	for _, p := range b.payments {
		if p.status == "pending" && p.account == absorb {
			p.account = keep
		}
	}
	delete(b.accounts, absorb)
	b.record(ts, keep)
	b.record(ts, absorb)
	return true
}

// BalanceAt returns what the id's balance was right after everything at or before atTs (atTs <= ts).
func (b *Bank) BalanceAt(ts int, id string, atTs int) (int, bool) {
	b.settle(ts)
	h := b.history[id]
	i := sort.Search(len(h), func(i int) bool { return h[i].ts > atTs })
	if i == 0 || !h[i-1].open {
		return 0, false
	}
	return h[i-1].balance, true
}
