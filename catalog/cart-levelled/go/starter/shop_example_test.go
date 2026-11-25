package shop

import (
	"reflect"
	"testing"
)

// An example to copy. Run your tests with the My tests button.
func TestExampleCart(t *testing.T) {
	s := NewShop()
	if !s.AddProduct(1, "scarf", 1250, 4) {
		t.Fatal("add product failed")
	}
	if !s.AddToCart(2, "cart-9", "scarf", 2) {
		t.Fatal("add to cart failed")
	}
	if got := s.CartTotal(3, "cart-9"); got != 2500 {
		t.Fatalf("total: got %d want 2500", got)
	}
	if got := s.Items(4, "cart-9"); !reflect.DeepEqual(got, []string{"scarf:2"}) {
		t.Fatalf("items: got %v", got)
	}
}
