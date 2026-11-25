package scheduler

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleOneAttendee(t *testing.T) {
	alex := []Attendee{{Offset: 0, WorkStart: 540, WorkEnd: 1020}}
	if got := EarliestQuorumSlot(alex, 1, 30, 1); got != 540 {
		t.Fatalf("got %d want 540", got)
	}
}
