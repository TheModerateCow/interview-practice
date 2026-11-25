// Package bank is the in-memory core of a retail bank's ledger.
package bank

// Bank holds accounts by id. Timestamps passed to its methods only ever increase.
type Bank struct {
	// your state here
}

// NewBank returns a bank with no accounts.
func NewBank() *Bank {
	return &Bank{}
}

// OpenAccount opens an empty account. False if the id is already open.
func (b *Bank) OpenAccount(ts int, id string) bool {
	panic("not implemented")
}

// Deposit adds amount to the account and returns the new balance.
func (b *Bank) Deposit(ts int, id string, amount int) (int, bool) {
	panic("not implemented")
}

// Withdraw takes amount out of the account and returns the new balance.
func (b *Bank) Withdraw(ts int, id string, amount int) (int, bool) {
	panic("not implemented")
}

// Transfer moves amount between two accounts and returns the sender's new balance.
func (b *Bank) Transfer(ts int, from, to string, amount int) (int, bool) {
	panic("not implemented")
}

// Balance returns the account's balance.
func (b *Bank) Balance(ts int, id string) (int, bool) {
	panic("not implemented")
}
