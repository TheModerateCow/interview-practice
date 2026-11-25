package search_box

import "testing"

func TestExample(t *testing.T) {
	got1 := FewestKeystrokes([]string{"pizza"}, "pizzas")
	if got1 != 2 {
		t.Fatalf("expected %v, got %v", 2, got1)
	}
}
