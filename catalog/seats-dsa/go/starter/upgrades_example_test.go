package upgrades

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleTwoPassengersOneSeat(t *testing.T) {
	// One leg with a single free seat, two passengers want it.
	if got := MaxUpgrades([]int{1}, [][]int{{0, 1}, {0, 1}}); got != 1 {
		t.Fatalf("got %d want 1", got)
	}
}
