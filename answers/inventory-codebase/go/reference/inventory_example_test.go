package inventory

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleReceiveAndReserve(t *testing.T) {
	s := New()
	if err := s.AddWarehouse("north"); err != nil {
		t.Fatal(err)
	}
	if err := s.Receive("north", "B-07", "MUG-RED", 12, 100); err != nil {
		t.Fatal(err)
	}
	if _, err := s.Reserve("o1", "north", "MUG-RED", 5, 900, 200); err != nil {
		t.Fatal(err)
	}
	if got, _ := s.Available("north", "MUG-RED", 300); got != 7 {
		t.Fatalf("available: got %d want 7", got)
	}
	if got := s.OnHand("north", "MUG-RED"); got != 12 {
		t.Fatalf("on hand: got %d want 12", got)
	}
}
