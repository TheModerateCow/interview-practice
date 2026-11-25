package dispatch

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleTwoPickups(t *testing.T) {
	// Riders at 0 and 10, drivers at 3 and 12: pairs (0,3) and (10,12), so R = 3.
	if got := MinDispatchRadius([]int{0, 10}, []int{3, 12}, 2); got != 3 {
		t.Fatalf("got %d want 3", got)
	}
}
