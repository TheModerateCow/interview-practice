package loyalty

import "testing"

// An example to copy. Write your own tests in loyalty_test.go and run them with My tests.
func TestExampleEarn(t *testing.T) {
	a := NewAccount()
	got, err := a.Earn(1, 2000) // a 20.00 purchase
	if err != nil {
		t.Fatalf("Earn: unexpected error %v", err)
	}
	if got != 20 {
		t.Fatalf("Earn: got %d points want 20", got)
	}
	if bal := a.Balance(1); bal != 20 {
		t.Fatalf("Balance: got %d want 20", bal)
	}
}
