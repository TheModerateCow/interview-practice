package alerting

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleSpikeSpreadOut(t *testing.T) {
	// 1% budget. Minute 1 alone is at 5%, but minutes 0-2 together are 6 errors / 600 requests = 1%.
	if got := LongestCompliantWindow([]int{300, 100, 200, 50}, []int{1, 5, 0, 9}, 10000); got != 3 {
		t.Fatalf("got %d want 3", got)
	}
}
