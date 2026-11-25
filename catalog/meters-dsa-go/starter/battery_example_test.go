package meters

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleOneCycle(t *testing.T) {
	// Charge at 3, discharge at 7 and pay 1 of wear: 7 - 1 - 3 = 3.
	if got := BestBatteryProfit([]int{3, 7}, 1, 1); got != 3 {
		t.Fatalf("got %d want 3", got)
	}
}
