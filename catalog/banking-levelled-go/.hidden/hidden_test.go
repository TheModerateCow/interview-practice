package bank

import (
	"strconv"
	"testing"
)

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenSame(t *testing.T, what string, got, want []string) {
	t.Helper()
	if got == nil {
		t.Fatalf("%s: got a nil slice, want %q", what, want)
	}
	if len(got) != len(want) {
		t.Fatalf("%s: got %q want %q", what, got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("%s: got %q want %q", what, got, want)
		}
	}
}

// hiddenAmt turns an (amount, ok) pair into the amount as text, or "(none)" when the call failed.
func hiddenAmt(v int, ok bool) string {
	if !ok {
		return "(none)"
	}
	return strconv.Itoa(v)
}

// hiddenPid turns a (paymentID, ok) pair into the id, or "(none)" when the call failed.
func hiddenPid(id string, ok bool) string {
	if !ok {
		return "(none)"
	}
	return id
}

// hiddenFunded opens each account at ts, ts+1, ... and deposits its amount (if positive) right after.
// Returns the next free timestamp.
func hiddenFunded(b *Bank, ts int, ids []string, amounts []int) int {
	for i, id := range ids {
		b.OpenAccount(ts, id)
		ts++
		if amounts[i] > 0 {
			b.Deposit(ts, id, amounts[i])
			ts++
		}
	}
	return ts
}

// ---------------------------------------------------------------- level 1

func Test_l1_open_and_deposit(t *testing.T) {
	b := NewBank()
	hiddenEq(t, "open", b.OpenAccount(1, "acc-a"), true)
	hiddenEq(t, "new account is empty", hiddenAmt(b.Balance(2, "acc-a")), "0")
	hiddenEq(t, "deposit", hiddenAmt(b.Deposit(3, "acc-a", 500)), "500")
	hiddenEq(t, "second deposit", hiddenAmt(b.Deposit(4, "acc-a", 250)), "750")
	hiddenEq(t, "balance", hiddenAmt(b.Balance(5, "acc-a")), "750")
	hiddenEq(t, "deposit to missing account", hiddenAmt(b.Deposit(6, "acc-z", 100)), "(none)")
	hiddenEq(t, "balance of missing account", hiddenAmt(b.Balance(7, "acc-z")), "(none)")
}

func Test_l1_open_twice_keeps_money(t *testing.T) {
	b := NewBank()
	b.OpenAccount(1, "acc-a")
	b.Deposit(2, "acc-a", 300)
	hiddenEq(t, "open an open id", b.OpenAccount(3, "acc-a"), false)
	hiddenEq(t, "balance kept", hiddenAmt(b.Balance(4, "acc-a")), "300")
	hiddenEq(t, "ids are case-sensitive", b.OpenAccount(5, "ACC-A"), true)
	hiddenEq(t, "other id is empty", hiddenAmt(b.Balance(6, "ACC-A")), "0")
}

func Test_l1_withdraw(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a"}, []int{400})
	hiddenEq(t, "withdraw", hiddenAmt(b.Withdraw(ts, "acc-a", 150)), "250")
	hiddenEq(t, "more than the balance", hiddenAmt(b.Withdraw(ts+1, "acc-a", 251)), "(none)")
	hiddenEq(t, "failed withdraw changes nothing", hiddenAmt(b.Balance(ts+2, "acc-a")), "250")
	hiddenEq(t, "exactly the balance", hiddenAmt(b.Withdraw(ts+3, "acc-a", 250)), "0")
	hiddenEq(t, "empty account", hiddenAmt(b.Withdraw(ts+4, "acc-a", 1)), "(none)")
	hiddenEq(t, "missing account", hiddenAmt(b.Withdraw(ts+5, "acc-z", 1)), "(none)")
}

func Test_l1_transfer(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{1000, 200})
	hiddenEq(t, "transfer", hiddenAmt(b.Transfer(ts, "acc-a", "acc-b", 300)), "700")
	hiddenEq(t, "receiver credited", hiddenAmt(b.Balance(ts+1, "acc-b")), "500")
	hiddenEq(t, "more than the sender has", hiddenAmt(b.Transfer(ts+2, "acc-b", "acc-a", 501)), "(none)")
	hiddenEq(t, "sender unchanged", hiddenAmt(b.Balance(ts+3, "acc-b")), "500")
	hiddenEq(t, "receiver unchanged", hiddenAmt(b.Balance(ts+4, "acc-a")), "700")
	hiddenEq(t, "sender's whole balance", hiddenAmt(b.Transfer(ts+5, "acc-b", "acc-a", 500)), "0")
	hiddenEq(t, "receiver after", hiddenAmt(b.Balance(ts+6, "acc-a")), "1200")
}

func Test_l1_transfer_rejected(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{600, 0})
	hiddenEq(t, "to a missing account", hiddenAmt(b.Transfer(ts, "acc-a", "acc-z", 100)), "(none)")
	hiddenEq(t, "from a missing account", hiddenAmt(b.Transfer(ts+1, "acc-z", "acc-a", 100)), "(none)")
	hiddenEq(t, "to itself", hiddenAmt(b.Transfer(ts+2, "acc-a", "acc-a", 100)), "(none)")
	hiddenEq(t, "sender untouched", hiddenAmt(b.Balance(ts+3, "acc-a")), "600")
	hiddenEq(t, "from an empty account", hiddenAmt(b.Transfer(ts+4, "acc-b", "acc-a", 1)), "(none)")
	hiddenEq(t, "empty account untouched", hiddenAmt(b.Balance(ts+5, "acc-b")), "0")
}

func Test_l1_accounts_independent(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a", "acc-b", "acc-c"}, []int{100, 200, 300})
	b.Withdraw(ts, "acc-b", 50)
	b.Transfer(ts+1, "acc-c", "acc-a", 120)
	b.Deposit(ts+2, "acc-b", 5)
	hiddenEq(t, "acc-a", hiddenAmt(b.Balance(ts+3, "acc-a")), "220")
	hiddenEq(t, "acc-b", hiddenAmt(b.Balance(ts+4, "acc-b")), "155")
	hiddenEq(t, "acc-c", hiddenAmt(b.Balance(ts+5, "acc-c")), "180")
}

// ---------------------------------------------------------------- level 2

func Test_l2_top_spenders_order(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a", "acc-b", "acc-c"}, []int{1000, 1000, 1000})
	b.Withdraw(ts, "acc-a", 100)
	b.Transfer(ts+1, "acc-b", "acc-a", 400)
	b.Withdraw(ts+2, "acc-c", 250)
	b.Deposit(ts+3, "acc-c", 900)
	hiddenSame(t, "ranked by money out", b.TopSpenders(ts+4, 3), []string{"acc-b:400", "acc-c:250", "acc-a:100"})
	hiddenSame(t, "top two", b.TopSpenders(ts+5, 2), []string{"acc-b:400", "acc-c:250"})
}

func Test_l2_top_spenders_ties_and_limits(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-d", "acc-b", "acc-c", "acc-a"}, []int{500, 500, 500, 0})
	b.Withdraw(ts, "acc-d", 200)
	b.Withdraw(ts+1, "acc-b", 200)
	hiddenSame(t, "ties by id, idle accounts last", b.TopSpenders(ts+2, 10), []string{"acc-b:200", "acc-d:200", "acc-a:0", "acc-c:0"})
	hiddenSame(t, "n of one", b.TopSpenders(ts+3, 1), []string{"acc-b:200"})
	hiddenSame(t, "n of zero", b.TopSpenders(ts+4, 0), []string{})
}

func Test_l2_failed_moves_dont_count(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{300, 100})
	b.Withdraw(ts, "acc-a", 301)
	b.Transfer(ts+1, "acc-a", "acc-z", 50)
	b.Transfer(ts+2, "acc-a", "acc-a", 50)
	b.Transfer(ts+3, "acc-b", "acc-a", 60)
	hiddenSame(t, "only the sender's successful move counts", b.TopSpenders(ts+4, 2), []string{"acc-b:60", "acc-a:0"})
}

func Test_l2_spending_accumulates(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{1000, 1000})
	b.Withdraw(ts, "acc-a", 300)
	b.Withdraw(ts+1, "acc-b", 200)
	hiddenSame(t, "first", b.TopSpenders(ts+2, 2), []string{"acc-a:300", "acc-b:200"})
	b.Transfer(ts+3, "acc-b", "acc-a", 150)
	b.Deposit(ts+4, "acc-b", 5000)
	hiddenSame(t, "deposits never reduce spending", b.TopSpenders(ts+5, 2), []string{"acc-b:350", "acc-a:300"})
	b.Withdraw(ts+6, "acc-b", 1)
	hiddenSame(t, "overtakes", b.TopSpenders(ts+7, 2), []string{"acc-b:351", "acc-a:300"})
}

func Test_l2_accounts_above(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-c", "acc-a", "acc-b", "acc-d"}, []int{700, 300, 700, 0})
	hiddenSame(t, "threshold is inclusive", b.AccountsAbove(ts, 300), []string{"acc-b:700", "acc-c:700", "acc-a:300"})
	hiddenSame(t, "zero takes everyone", b.AccountsAbove(ts+1, 0), []string{"acc-b:700", "acc-c:700", "acc-a:300", "acc-d:0"})
	b.Transfer(ts+2, "acc-b", "acc-a", 500)
	hiddenSame(t, "after a transfer", b.AccountsAbove(ts+3, 500), []string{"acc-a:800", "acc-c:700"})
}

func Test_l2_empty_results(t *testing.T) {
	b := NewBank()
	hiddenSame(t, "no accounts, no spenders", b.TopSpenders(1, 3), []string{})
	hiddenFunded(b, 2, []string{"acc-a"}, []int{50})
	hiddenSame(t, "nobody that rich", b.AccountsAbove(10, 51), []string{})
	hiddenSame(t, "no accounts above", NewBank().AccountsAbove(11, 0), []string{})
}

// ---------------------------------------------------------------- level 3

func Test_l3_payment_runs_when_due(t *testing.T) {
	b := NewBank()
	hiddenFunded(b, 1, []string{"acc-a"}, []int{500})
	hiddenEq(t, "schedule", hiddenPid(b.SchedulePayment(10, "acc-a", 120, 5)), "pay1")
	hiddenEq(t, "not yet", hiddenAmt(b.Balance(13, "acc-a")), "500")
	hiddenEq(t, "pending", b.PaymentStatus(14, "pay1"), "pending")
	hiddenEq(t, "taken at its due time", hiddenAmt(b.Balance(15, "acc-a")), "380")
	hiddenEq(t, "paid", b.PaymentStatus(16, "pay1"), "paid")
	hiddenEq(t, "runs once", hiddenAmt(b.Balance(30, "acc-a")), "380")
}

func Test_l3_payment_before_same_time_call(t *testing.T) {
	b := NewBank()
	hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{100, 300})
	b.SchedulePayment(10, "acc-a", 150, 10)
	b.SchedulePayment(11, "acc-b", 200, 11)
	hiddenEq(t, "deposit at the due time comes too late", hiddenAmt(b.Deposit(20, "acc-a", 100)), "200")
	hiddenEq(t, "failed", b.PaymentStatus(21, "pay1"), "failed")
	hiddenEq(t, "withdraw at the due time sees the payment", hiddenAmt(b.Withdraw(22, "acc-b", 150)), "(none)")
	hiddenEq(t, "paid", b.PaymentStatus(23, "pay2"), "paid")
}

func Test_l3_failed_payment_not_retried(t *testing.T) {
	b := NewBank()
	hiddenFunded(b, 1, []string{"acc-a"}, []int{100})
	b.SchedulePayment(10, "acc-a", 250, 5)
	b.SchedulePayment(11, "acc-a", 80, 9)
	hiddenEq(t, "nothing taken", hiddenAmt(b.Balance(16, "acc-a")), "100")
	b.Deposit(17, "acc-a", 500)
	hiddenEq(t, "still failed", b.PaymentStatus(19, "pay1"), "failed")
	hiddenEq(t, "later payment runs", hiddenAmt(b.Balance(20, "acc-a")), "520")
	hiddenEq(t, "later payment paid", b.PaymentStatus(21, "pay2"), "paid")
}

func Test_l3_earliest_due_first(t *testing.T) {
	b := NewBank()
	hiddenFunded(b, 1, []string{"acc-a"}, []int{100})
	b.SchedulePayment(10, "acc-a", 70, 20)
	b.SchedulePayment(11, "acc-a", 60, 4)
	b.SchedulePayment(12, "acc-a", 30, 3)
	b.SchedulePayment(13, "acc-a", 20, 2)
	hiddenEq(t, "all due by now", hiddenAmt(b.Balance(40, "acc-a")), "10")
	hiddenEq(t, "pay1", b.PaymentStatus(41, "pay1"), "failed")
	hiddenEq(t, "pay2", b.PaymentStatus(42, "pay2"), "paid")
	hiddenEq(t, "pay3", b.PaymentStatus(43, "pay3"), "paid")
	hiddenEq(t, "pay4", b.PaymentStatus(44, "pay4"), "failed")
}

func Test_l3_cancel(t *testing.T) {
	b := NewBank()
	hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{500, 500})
	b.SchedulePayment(10, "acc-a", 100, 10)
	b.SchedulePayment(11, "acc-a", 100, 9)
	hiddenEq(t, "someone else's payment", b.CancelPayment(12, "acc-b", "pay1"), false)
	hiddenEq(t, "cancel", b.CancelPayment(13, "acc-a", "pay1"), true)
	hiddenEq(t, "cancel twice", b.CancelPayment(14, "acc-a", "pay1"), false)
	hiddenEq(t, "cancel at the due time is too late", b.CancelPayment(20, "acc-a", "pay2"), false)
	hiddenEq(t, "cancelled", b.PaymentStatus(21, "pay1"), "cancelled")
	hiddenEq(t, "only pay2 taken", hiddenAmt(b.Balance(22, "acc-a")), "400")
	hiddenEq(t, "unknown payment", b.PaymentStatus(23, "pay9"), "")
	hiddenEq(t, "cancel unknown", b.CancelPayment(24, "acc-a", "pay9"), false)
}

func Test_l3_ids_and_spending(t *testing.T) {
	b := NewBank()
	hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{400, 400})
	hiddenEq(t, "first id", hiddenPid(b.SchedulePayment(10, "acc-a", 300, 5)), "pay1")
	hiddenEq(t, "missing account", hiddenPid(b.SchedulePayment(11, "acc-z", 10, 5)), "(none)")
	hiddenEq(t, "ids count across accounts", hiddenPid(b.SchedulePayment(12, "acc-b", 50, 5)), "pay2")
	b.Withdraw(13, "acc-b", 100)
	hiddenSame(t, "ranking settles due payments first", b.TopSpenders(17, 2), []string{"acc-a:300", "acc-b:150"})
	hiddenSame(t, "balances too", b.AccountsAbove(18, 0), []string{"acc-b:250", "acc-a:100"})
}

// ---------------------------------------------------------------- level 4

func Test_l4_merge_balances(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{300, 450})
	hiddenEq(t, "merge", b.MergeAccounts(ts, "acc-a", "acc-b"), true)
	hiddenEq(t, "kept account holds both", hiddenAmt(b.Balance(ts+1, "acc-a")), "750")
	hiddenEq(t, "absorbed account is closed", hiddenAmt(b.Balance(ts+2, "acc-b")), "(none)")
	hiddenEq(t, "no deposits to it", hiddenAmt(b.Deposit(ts+3, "acc-b", 10)), "(none)")
	hiddenEq(t, "merge again", b.MergeAccounts(ts+4, "acc-a", "acc-b"), false)
	hiddenEq(t, "merge with itself", b.MergeAccounts(ts+5, "acc-a", "acc-a"), false)
	hiddenEq(t, "id can be opened again", b.OpenAccount(ts+6, "acc-b"), true)
	hiddenEq(t, "fresh and empty", hiddenAmt(b.Balance(ts+7, "acc-b")), "0")
}

func Test_l4_merge_combines_spending(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a", "acc-b", "acc-c"}, []int{1000, 1000, 1000})
	b.Withdraw(ts, "acc-a", 300)
	b.Withdraw(ts+1, "acc-b", 250)
	b.Withdraw(ts+2, "acc-c", 400)
	b.MergeAccounts(ts+3, "acc-b", "acc-a")
	hiddenSame(t, "spending follows the money", b.TopSpenders(ts+4, 3), []string{"acc-b:550", "acc-c:400"})
	b.OpenAccount(ts+5, "acc-a")
	hiddenSame(t, "reopened id starts from zero", b.TopSpenders(ts+6, 3), []string{"acc-b:550", "acc-c:400", "acc-a:0"})
}

func Test_l4_merge_moves_payments(t *testing.T) {
	b := NewBank()
	hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{100, 400})
	b.SchedulePayment(10, "acc-b", 300, 20)
	b.SchedulePayment(11, "acc-b", 50, 20)
	b.MergeAccounts(12, "acc-a", "acc-b")
	hiddenEq(t, "cancel through the closed id", b.CancelPayment(13, "acc-b", "pay2"), false)
	hiddenEq(t, "cancel through the kept id", b.CancelPayment(14, "acc-a", "pay2"), true)
	hiddenEq(t, "taken from the kept account", hiddenAmt(b.Balance(30, "acc-a")), "200")
	hiddenEq(t, "paid", b.PaymentStatus(31, "pay1"), "paid")
	hiddenSame(t, "counts as the kept account's spending", b.TopSpenders(32, 1), []string{"acc-a:300"})
}

func Test_l4_balance_at(t *testing.T) {
	b := NewBank()
	b.OpenAccount(5, "acc-a")
	b.Deposit(10, "acc-a", 500)
	b.Withdraw(20, "acc-a", 120)
	b.OpenAccount(25, "acc-b")
	b.Transfer(30, "acc-a", "acc-b", 80)
	hiddenEq(t, "before it opened", hiddenAmt(b.BalanceAt(40, "acc-a", 4)), "(none)")
	hiddenEq(t, "just opened", hiddenAmt(b.BalanceAt(41, "acc-a", 5)), "0")
	hiddenEq(t, "at a deposit's own time", hiddenAmt(b.BalanceAt(42, "acc-a", 10)), "500")
	hiddenEq(t, "between changes", hiddenAmt(b.BalanceAt(43, "acc-a", 19)), "500")
	hiddenEq(t, "after the withdraw", hiddenAmt(b.BalanceAt(44, "acc-a", 29)), "380")
	hiddenEq(t, "receiver at the transfer", hiddenAmt(b.BalanceAt(45, "acc-b", 30)), "80")
	hiddenEq(t, "now", hiddenAmt(b.BalanceAt(46, "acc-a", 46)), "300")
	hiddenEq(t, "never opened", hiddenAmt(b.BalanceAt(47, "acc-z", 30)), "(none)")
}

func Test_l4_balance_at_payment_time(t *testing.T) {
	b := NewBank()
	b.OpenAccount(1, "acc-a")
	b.Deposit(2, "acc-a", 200)
	b.SchedulePayment(3, "acc-a", 150, 12)
	b.SchedulePayment(4, "acc-a", 100, 16)
	hiddenEq(t, "before the payment", hiddenAmt(b.BalanceAt(50, "acc-a", 14)), "200")
	hiddenEq(t, "at its due time", hiddenAmt(b.BalanceAt(51, "acc-a", 15)), "50")
	hiddenEq(t, "failed payment changes nothing", hiddenAmt(b.BalanceAt(52, "acc-a", 20)), "50")
}

func Test_l4_balance_at_across_merge(t *testing.T) {
	b := NewBank()
	ts := hiddenFunded(b, 1, []string{"acc-a", "acc-b"}, []int{300, 450})
	b.MergeAccounts(10, "acc-a", "acc-b")
	b.OpenAccount(20, "acc-b")
	b.Deposit(21, "acc-b", 75)
	hiddenEq(t, "absorbed account before the merge", hiddenAmt(b.BalanceAt(30, "acc-b", ts)), "450")
	hiddenEq(t, "kept account before the merge", hiddenAmt(b.BalanceAt(31, "acc-a", 9)), "300")
	hiddenEq(t, "kept account at the merge", hiddenAmt(b.BalanceAt(32, "acc-a", 10)), "750")
	hiddenEq(t, "closed between merge and reopening", hiddenAmt(b.BalanceAt(33, "acc-b", 15)), "(none)")
	hiddenEq(t, "reopened", hiddenAmt(b.BalanceAt(34, "acc-b", 21)), "75")
}
