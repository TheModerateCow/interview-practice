package shipping

import "testing"

// An example to copy. Write your own tests first, run them with My tests,
// then implement shipping.go.
func TestExampleBillableGrams(t *testing.T) {
	got, err := BillableGrams(Parcel{WeightGrams: 400, LengthCm: 30, WidthCm: 20, HeightCm: 10})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != 1500 {
		t.Fatalf("got %d want 1500", got)
	}
}
