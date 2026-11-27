package payouts

type Payouts struct{}

func NewPayouts() *Payouts {
	panic("not implemented")
}

func (p *Payouts) AddMerchant(day int, merchantID string, feeBps int) bool {
	panic("not implemented")
}

func (p *Payouts) RecordSale(day int, merchantID string, amount int) string {
	panic("not implemented")
}

func (p *Payouts) Fee(day int, saleID string) int {
	panic("not implemented")
}

func (p *Payouts) Balance(day int, merchantID string) int {
	panic("not implemented")
}
