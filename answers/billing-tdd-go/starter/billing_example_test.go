package billing

import "testing"

// An example to copy. Write your own tests in billing_test.go and run them with My tests.
func TestExampleRenew(t *testing.T) {
	s, err := New(0, "starter", "monthly", 2)
	if err != nil {
		t.Fatalf("New: unexpected error %v", err)
	}
	if got := s.Renew(); got != 2598 { // 2 seats x 12.99
		t.Fatalf("Renew: charged %d want 2598", got)
	}
	if got := s.PeriodEnd(); got != 60 {
		t.Fatalf("PeriodEnd: got %d want 60", got)
	}
}
