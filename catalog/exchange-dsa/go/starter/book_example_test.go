package book

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleTwoLevels(t *testing.T) {
	// 1 share at 40 is cheapest, then 1 of the 2 shares at 50.
	got := RunBook([]Event{{Kind: "add", Price: 50, Qty: 2}, {Kind: "add", Price: 40, Qty: 1}, {Kind: "quote", Qty: 2}})
	if len(got) != 1 || got[0] != 90 {
		t.Fatalf("got %v want [90]", got)
	}
}
