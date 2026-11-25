package hotel

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleBookingCost(t *testing.T) {
	h := NewHotel()
	if !h.AddRoom(1, "7", "twin", 5000) {
		t.Fatal("add room failed")
	}
	if got := h.Book(2, "kit", "7", 30, 32); got != "b1" {
		t.Fatalf("book: got %q want b1", got)
	}
	if got := h.Cost(3, "b1"); got != 10000 {
		t.Fatalf("cost: got %d want 10000", got)
	}
}
