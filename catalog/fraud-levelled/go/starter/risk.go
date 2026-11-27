package risk

type RiskScreen struct{}

func NewRiskScreen() *RiskScreen {
	panic("not implemented")
}

func (r *RiskScreen) Block(ts int, kind string, value string) bool {
	panic("not implemented")
}

func (r *RiskScreen) Unblock(ts int, kind string, value string) bool {
	panic("not implemented")
}

func (r *RiskScreen) Screen(ts int, txnID string, card string, merchant string, amount int, country string) string {
	panic("not implemented")
}

func (r *RiskScreen) Decision(ts int, txnID string) string {
	panic("not implemented")
}
