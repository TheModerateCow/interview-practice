package fares

import "testing"

// An example to copy. Write your own tests in fares_test.go and run them with My tests.
func TestExampleOneOffPeakAdultRideAcrossTwoZones(t *testing.T) {
	card, err := NewFareCard("adult")
	if err != nil {
		t.Fatalf("NewFareCard: unexpected error %v", err)
	}
	got, err := card.Ride(600, 1, 2) // Monday 10:00
	if err != nil {
		t.Fatalf("Ride: unexpected error %v", err)
	}
	if got != 320 {
		t.Fatalf("Ride: got %d want 320", got)
	}
}
