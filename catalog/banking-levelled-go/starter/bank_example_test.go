package bank

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleDepositBalance(t *testing.T) {
	b := NewBank()
	if !b.OpenAccount(1, "acc-x") {
		t.Fatal("first open should succeed")
	}
	b.Deposit(2, "acc-x", 40)
	v, ok := b.Balance(3, "acc-x")
	if !ok || v != 40 {
		t.Fatalf("balance: got %d, %v want 40, true", v, ok)
	}
}
