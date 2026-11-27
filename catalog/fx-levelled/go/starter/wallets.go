package wallets

type Wallets struct{}

func NewWallets() *Wallets {
	panic("not implemented")
}

func (w *Wallets) OpenWallet(ts int, walletID string) bool {
	panic("not implemented")
}

func (w *Wallets) Deposit(ts int, walletID string, currency string, amount int) int {
	panic("not implemented")
}

func (w *Wallets) Withdraw(ts int, walletID string, currency string, amount int) int {
	panic("not implemented")
}

func (w *Wallets) Balance(ts int, walletID string, currency string) int {
	panic("not implemented")
}

func (w *Wallets) Holdings(ts int, walletID string) []string {
	panic("not implemented")
}
