package ledger

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleCapture(t *testing.T) {
	l := New()
	if err := l.AddMerchant("m1", Pricing{Bps: 250}); err != nil {
		t.Fatal(err)
	}
	if _, err := l.Capture("ch1", "m1", "USD", 1999, "card", 100); err != nil {
		t.Fatal(err)
	}
	if got := l.Balance(PendingAccount("m1"), "USD"); got != 1999 {
		t.Fatalf("pending: got %d want 1999", got)
	}
	if got := l.TrialBalance("USD"); got != 0 {
		t.Fatalf("trial balance: got %d want 0", got)
	}
}
