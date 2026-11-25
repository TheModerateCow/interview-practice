package library

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleCheckout(t *testing.T) {
	lib := NewLibrary()
	if !lib.AddMember(1, "m-7") || !lib.AddCopy(2, "B-1", "Beowulf") {
		t.Fatal("setup failed")
	}
	if got := lib.Checkout(3, "m-7", "Beowulf"); got != "B-1" {
		t.Fatalf("checkout: got %q want %q", got, "B-1")
	}
	if got := lib.Borrower(4, "B-1"); got != "m-7" {
		t.Fatalf("borrower: got %q want %q", got, "m-7")
	}
}
