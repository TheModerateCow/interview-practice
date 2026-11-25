package flags

// An example to copy. Run your tests with the My tests button.

import "testing"

func TestExample(t *testing.T) {
	f := NewFlagService()
	got2 := f.CreateFlag(1, "new-nav")
	if got2 != true {
		t.Fatalf("expected %v, got %v", true, got2)
	}
	got3 := f.SetEnabled(2, "new-nav", "dev", true)
	if got3 != true {
		t.Fatalf("expected %v, got %v", true, got3)
	}
	got4 := f.IsEnabled(3, "new-nav", "dev", "riya")
	if got4 != true {
		t.Fatalf("expected %v, got %v", true, got4)
	}
}
