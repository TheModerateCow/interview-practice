package tickets

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleBuy(t *testing.T) {
	o := NewOffice()
	if !o.CreateEvent(1, "jazz-night", 3) {
		t.Fatal("create failed")
	}
	if !o.Buy(2, "jazz-night", "maya", 2) {
		t.Fatal("buy failed")
	}
	if got := o.Available(3, "jazz-night"); got != 1 {
		t.Fatalf("available: got %d want 1", got)
	}
}
