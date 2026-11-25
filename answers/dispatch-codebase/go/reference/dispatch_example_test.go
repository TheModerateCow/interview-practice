package dispatch

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleAssignNearest(t *testing.T) {
	d := New()
	d.AddCourier("near", Point{X: 100, Y: 0}, 1)
	d.AddCourier("far", Point{X: 900, Y: 900}, 1)
	d.PlaceOrder("o1", Point{X: 0, Y: 0}, Point{X: 500, Y: 0}, 0, 5)
	got, err := d.Assign("o1")
	if err != nil || got != "near" {
		t.Fatalf("Assign: got %q, %v; want near", got, err)
	}
}
