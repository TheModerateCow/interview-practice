package parking

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExamplePark(t *testing.T) {
	g := NewGarage()
	if !g.AddSpot(1, "P1", "medium") {
		t.Fatal("add spot failed")
	}
	if got := g.Park(2, "AB-123", "small"); got != "P1" {
		t.Fatalf("park: got %q want %q", got, "P1")
	}
	if got := g.SpotOf(3, "AB-123"); got != "P1" {
		t.Fatalf("spot of: got %q want %q", got, "P1")
	}
}
