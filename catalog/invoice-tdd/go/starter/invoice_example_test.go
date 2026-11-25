package invoice

import "testing"

// An example to copy. Write your own tests in invoice_test.go and run them with My tests.
func TestExampleSingleLine(t *testing.T) {
	inv, err := NewInvoice(0, "net30")
	if err != nil {
		t.Fatalf("NewInvoice: unexpected error %v", err)
	}
	got, err := inv.AddLine(1000, 2, "standard") // 2 x 10.00, no discount
	if err != nil || got != 2000 {
		t.Fatalf("AddLine: got %d, %v want 2000", got, err)
	}
	if total := inv.Total(); total != 2400 { // plus 20% tax
		t.Fatalf("Total: got %d want 2400", total)
	}
}

func TestExampleUnknownTerms(t *testing.T) {
	if _, err := NewInvoice(0, "net7"); err == nil {
		t.Fatal("NewInvoice: expected an error for unknown terms")
	}
}
