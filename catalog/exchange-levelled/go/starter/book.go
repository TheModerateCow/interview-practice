package book

type OrderBook struct{}

func NewOrderBook() *OrderBook {
	panic("not implemented")
}

func (o *OrderBook) AddOrder(orderID string, price int, qty int) bool {
	panic("not implemented")
}

func (o *OrderBook) CancelOrder(orderID string) bool {
	panic("not implemented")
}

func (o *OrderBook) BestAsk() (int, bool) {
	panic("not implemented")
}

func (o *OrderBook) DepthAt(price int) int {
	panic("not implemented")
}
