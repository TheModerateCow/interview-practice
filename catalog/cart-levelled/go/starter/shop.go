package shop

type Shop struct{}

func NewShop() *Shop {
	panic("not implemented")
}

func (s *Shop) AddProduct(ts int, sku string, priceCents int, stock int) bool {
	panic("not implemented")
}

func (s *Shop) AddToCart(ts int, cartID string, sku string, qty int) bool {
	panic("not implemented")
}

func (s *Shop) RemoveFromCart(ts int, cartID string, sku string, qty int) int {
	panic("not implemented")
}

func (s *Shop) CartTotal(ts int, cartID string) int {
	panic("not implemented")
}

func (s *Shop) Items(ts int, cartID string) []string {
	panic("not implemented")
}
