package pipeline

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleTwoJobChain(t *testing.T) {
	// Job 1 feeds the release (job 0); nothing is warmed, so 4 + 7 minutes.
	got := FastestRelease([]Job{{-1, 7, 1}, {0, 4, 2}}, 0)
	if got != 11 {
		t.Fatalf("got %d want 11", got)
	}
}
