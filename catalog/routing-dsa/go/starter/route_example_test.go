package route

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleDirectRoad(t *testing.T) {
	// Two junctions, one road that needs 3 units; the van has 5.
	got := FastestDelivery(2, 5, 5, []int{0, 0}, []Road{{0, 1, 12, 3}})
	if got != 12 {
		t.Fatalf("got %d want 12", got)
	}
}
