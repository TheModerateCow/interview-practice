package fixture

import "errors"

type Entry struct {
	AccountID   string
	AmountCents int
}

var (
	ErrInvalidAmount     = errors.New("invalid amount")
	ErrInsufficientFunds = errors.New("insufficient funds")
	ErrInvalidWindow     = errors.New("invalid window")
	ErrWalletFrozen      = errors.New("wallet frozen")
	ErrInvalidOwner      = errors.New("invalid owner")
)

func NetByAccount(entries []Entry) []Entry {
	panic("not implemented")
}

func MaxWindow(values []int, k int) (int, error) {
	panic("not implemented")
}

func FirstNegative(values []int) (int, bool) {
	panic("not implemented")
}

func Grid(n int) [][]int {
	panic("not implemented")
}

type Wallet struct{}

func NewWallet(owner string) (*Wallet, error) {
	panic("not implemented")
}

func (w *Wallet) Deposit(cents int) error {
	panic("not implemented")
}

func (w *Wallet) Withdraw(cents int) (int, error) {
	panic("not implemented")
}

func (w *Wallet) Balance() int {
	panic("not implemented")
}

func (w *Wallet) OwnerName() string {
	panic("not implemented")
}
