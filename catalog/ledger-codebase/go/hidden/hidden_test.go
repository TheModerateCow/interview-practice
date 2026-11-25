package ledger

import (
	"errors"
	"fmt"
	"strconv"
	"testing"
	"time"
)

// The app compiles one phase's tests at a time: keep every import used outside them.
var (
	_ = errors.Is
	_ = fmt.Sprint
	_ = strconv.Itoa
	_ = time.Second
)

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenIsErr(t *testing.T, what string, err, want error) {
	t.Helper()
	if !errors.Is(err, want) {
		t.Fatalf("%s: got error %v want %v", what, err, want)
	}
}

func hiddenMust(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}

func hiddenMerchant(t *testing.T, l *Ledger, id string, bps int64, fixed map[string]int64) {
	t.Helper()
	hiddenMust(t, l.AddMerchant(id, Pricing{Bps: bps, Fixed: fixed}))
}

func hiddenCapture(t *testing.T, l *Ledger, id, m, cur string, amount int64, method string, ts int64) {
	t.Helper()
	if _, err := l.Capture(id, m, cur, amount, method, ts); err != nil {
		t.Fatalf("capture %s: %v", id, err)
	}
}

func hiddenLines(ls []Line) string { return fmt.Sprintf("%v", ls) }

func hiddenBatches(bs []Batch) string { return fmt.Sprintf("%+v", bs) }

// fund puts amount straight into a merchant's available balance, as an ops adjustment.
func hiddenFund(t *testing.T, l *Ledger, m, cur string, amount, ts int64) {
	t.Helper()
	_, err := l.Post(Entry{TS: ts, Memo: "adjustment", Postings: []Posting{
		{AvailableAccount(m), cur, amount}, {ClearingAccount, cur, -amount}}})
	hiddenMust(t, err)
}

// ---------------------------------------------------------------- phase 1

func hiddenStatementLedger(t *testing.T) *Ledger {
	l := New()
	hiddenMerchant(t, l, "m1", 250, nil)
	hiddenCapture(t, l, "c1", "m1", "USD", 1000, "card", 10)
	hiddenCapture(t, l, "c2", "m1", "USD", 2500, "card", 20)
	hiddenCapture(t, l, "c3", "m1", "USD", 400, "card", 30)
	hiddenMust(t, l.Refund("c2", 500, 40))
	return l
}

func Test_p1_statement_leaves_balances_alone(t *testing.T) {
	l := hiddenStatementLedger(t)
	acct := PendingAccount("m1")
	hiddenEq(t, "statement", hiddenLines(l.Statement(acct, "USD", 0, 100)),
		"[{40 e4 -500 3400} {30 e3 400 3900} {20 e2 2500 3500} {10 e1 1000 1000}]")
	hiddenEq(t, "balance after statement", l.Balance(acct, "USD"), 3400)
	hiddenEq(t, "balance at 25", l.BalanceAt(acct, "USD", 25), 3500)
	hiddenEq(t, "balance at 5", l.BalanceAt(acct, "USD", 5), 0)
	hiddenEq(t, "balance at 40", l.BalanceAt(acct, "USD", 40), 3400)
	hiddenEq(t, "trial balance", l.TrialBalance("USD"), 0)
}

func Test_p1_repeated_statements_agree(t *testing.T) {
	l := hiddenStatementLedger(t)
	acct := PendingAccount("m1")
	first := hiddenLines(l.Statement(acct, "USD", 15, 35))
	hiddenEq(t, "first statement", first, "[{30 e3 400 3900} {20 e2 2500 3500}]")
	hiddenEq(t, "second statement", hiddenLines(l.Statement(acct, "USD", 15, 35)), first)
	hiddenEq(t, "third statement", hiddenLines(l.Statement(acct, "USD", 0, 100)),
		"[{40 e4 -500 3400} {30 e3 400 3900} {20 e2 2500 3500} {10 e1 1000 1000}]")
	hiddenEq(t, "balance at 30", l.BalanceAt(acct, "USD", 30), 3900)
	hiddenEq(t, "balance", l.Balance(acct, "USD"), 3400)
}

func Test_p1_failed_payout_webhook_retry_credits_once(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 250, nil)
	hiddenFund(t, l, "m1", "USD", 5000, 1)
	_, err := l.RequestPayout("p1", "m1", "USD", 3000, 2)
	hiddenMust(t, err)
	hiddenEq(t, "available after request", l.Balance(AvailableAccount("m1"), "USD"), 2000)
	hiddenEq(t, "in transit after request", l.Balance(InTransitAccount, "USD"), 3000)
	hiddenMust(t, l.PayoutFailed("p1", 3))
	hiddenMust(t, l.PayoutFailed("p1", 4)) // the bank retries the webhook
	hiddenEq(t, "available after failure", l.Balance(AvailableAccount("m1"), "USD"), 5000)
	hiddenEq(t, "in transit after failure", l.Balance(InTransitAccount, "USD"), 0)
	p, ok := l.Payout("p1")
	hiddenEq(t, "payout found", ok, true)
	hiddenEq(t, "status", p.Status, PayoutFailed)
	hiddenEq(t, "updated at", p.UpdatedAt, int64(3))
	_, err = l.RequestPayout("p2", "m1", "USD", 5001, 5)
	hiddenIsErr(t, "overdraw", err, ErrInsufficientFunds)
	hiddenEq(t, "trial balance", l.TrialBalance("USD"), 0)
}

func Test_p1_paid_payout_cannot_then_fail(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 250, nil)
	hiddenFund(t, l, "m1", "EUR", 8000, 1)
	_, err := l.RequestPayout("p1", "m1", "EUR", 3000, 2)
	hiddenMust(t, err)
	hiddenMust(t, l.PayoutPaid("p1", 3))
	hiddenMust(t, l.PayoutPaid("p1", 4))
	hiddenIsErr(t, "failed after paid", l.PayoutFailed("p1", 5), ErrPayoutState)
	hiddenEq(t, "bank", l.Balance(BankAccount, "EUR"), 3000)
	hiddenEq(t, "in transit", l.Balance(InTransitAccount, "EUR"), 0)
	hiddenEq(t, "available", l.Balance(AvailableAccount("m1"), "EUR"), 5000)
	p, _ := l.Payout("p1")
	hiddenEq(t, "status", p.Status, PayoutPaid)
}

func Test_p1_payout_requests(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 250, nil)
	hiddenFund(t, l, "m1", "USD", 1000, 1)
	_, err := l.RequestPayout("p1", "m1", "USD", 1000, 2)
	hiddenMust(t, err)
	_, err = l.RequestPayout("p1", "m1", "USD", 1, 3)
	hiddenIsErr(t, "duplicate id", err, ErrDuplicate)
	_, err = l.RequestPayout("p2", "m1", "USD", 0, 3)
	hiddenIsErr(t, "zero amount", err, ErrInvalid)
	_, err = l.RequestPayout("p3", "m1", "USD", 1, 3)
	hiddenIsErr(t, "nothing left", err, ErrInsufficientFunds)
	hiddenIsErr(t, "unknown payout", l.PayoutPaid("nope", 4), ErrNotFound)
	hiddenEq(t, "available", l.Balance(AvailableAccount("m1"), "USD"), 0)
}

func Test_p1_entries_balance_in_every_currency(t *testing.T) {
	l := New()
	_, err := l.Post(Entry{TS: 1, Memo: "bad adjustment", Postings: []Posting{
		{"ops:suspense", "USD", 100}, {"ops:suspense", "EUR", -100}}})
	hiddenIsErr(t, "cross-currency entry", err, ErrUnbalanced)
	hiddenEq(t, "USD trial balance", l.TrialBalance("USD"), 0)
	hiddenEq(t, "EUR trial balance", l.TrialBalance("EUR"), 0)
	hiddenEq(t, "suspense USD", l.Balance("ops:suspense", "USD"), 0)
	_, err = l.Post(Entry{TS: 2, Memo: "fx conversion", Postings: []Posting{
		{"customer:9", "USD", -1000}, {"platform:fx", "USD", 1000},
		{"platform:fx", "EUR", -920}, {"customer:9", "EUR", 920}}})
	hiddenMust(t, err)
	hiddenEq(t, "fx USD", l.Balance("platform:fx", "USD"), 1000)
	hiddenEq(t, "customer EUR", l.Balance("customer:9", "EUR"), 920)
	_, err = l.Post(Entry{TS: 3, Postings: []Posting{
		{"a", "JPY", 500}, {"b", "JPY", -400}, {"c", "KWD", 1000}, {"d", "KWD", -1100}}})
	hiddenIsErr(t, "two currencies off by opposite amounts", err, ErrUnbalanced)
	hiddenEq(t, "JPY trial balance", l.TrialBalance("JPY"), 0)
}

func Test_p1_entry_validation(t *testing.T) {
	l := New()
	_, err := l.Post(Entry{TS: 1, Postings: []Posting{{"a", "USD", 0}, {"b", "USD", 0}}})
	hiddenIsErr(t, "zero amounts", err, ErrInvalid)
	_, err = l.Post(Entry{TS: 1, Postings: []Posting{{"a", "USD", 5}}})
	hiddenIsErr(t, "one posting", err, ErrInvalid)
	_, err = l.Post(Entry{TS: 1, Postings: []Posting{{"a", "XYZ", 5}, {"b", "XYZ", -5}}})
	hiddenIsErr(t, "unknown currency", err, ErrUnknownCurrency)
	e, err := l.Post(Entry{TS: 10, Postings: []Posting{{"a", "USD", 5}, {"b", "USD", -5}}})
	hiddenMust(t, err)
	hiddenEq(t, "entry id", e.ID, "e1")
	_, err = l.Post(Entry{TS: 9, Postings: []Posting{{"a", "USD", 5}, {"b", "USD", -5}}})
	hiddenIsErr(t, "backdated", err, ErrBackdated)
}

func Test_p1_refund_limits(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 250, nil)
	hiddenCapture(t, l, "c1", "m1", "GBP", 1000, "card", 1)
	hiddenMust(t, l.Refund("c1", 600, 2))
	hiddenIsErr(t, "over-refund", l.Refund("c1", 401, 3), ErrInvalid)
	hiddenMust(t, l.Refund("c1", 400, 4))
	hiddenIsErr(t, "refund of nothing left", l.Refund("c1", 1, 5), ErrInvalid)
	hiddenIsErr(t, "unknown charge", l.Refund("c9", 1, 5), ErrNotFound)
	_, err := l.Capture("c1", "m1", "GBP", 1000, "card", 6)
	hiddenIsErr(t, "duplicate charge", err, ErrDuplicate)
	_, err = l.Capture("c2", "m9", "GBP", 1000, "card", 6)
	hiddenIsErr(t, "unknown merchant", err, ErrUnknownMerchant)
	hiddenEq(t, "pending", l.Balance(PendingAccount("m1"), "GBP"), 0)
	c, _ := l.Charge("c1")
	hiddenEq(t, "refunded", c.Refunded, int64(1000))
}

// ---------------------------------------------------------------- phase 2

func Test_p2_settles_available_charges_minus_fees(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 290, map[string]int64{"USD": 30})
	hiddenCapture(t, l, "c1", "m1", "USD", 10000, "card", 0)
	hiddenCapture(t, l, "c2", "m1", "USD", 2500, "card", 100)
	bs, err := l.Settle("m1", 2*Day+50)
	hiddenMust(t, err)
	hiddenEq(t, "batches", hiddenBatches(bs), "[{ID:b1 Merchant:m1 Currency:USD TS:172850 Charges:[c1] Gross:10000 Fees:320 Net:9680}]")
	hiddenEq(t, "pending", l.Balance(PendingAccount("m1"), "USD"), 2500)
	hiddenEq(t, "available", l.Balance(AvailableAccount("m1"), "USD"), 9680)
	hiddenEq(t, "fees", l.Balance(FeesAccount, "USD"), 320)
	hiddenEq(t, "trial balance", l.TrialBalance("USD"), 0)
	c, _ := l.Charge("c1")
	hiddenEq(t, "c1 batch", c.Batch, "b1")
	c, _ = l.Charge("c2")
	hiddenEq(t, "c2 batch", c.Batch, "")
}

func Test_p2_cutoff_is_inclusive_and_charges_settle_once(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 100, nil)
	hiddenCapture(t, l, "c1", "m1", "USD", 5000, "bank", 0)
	hiddenCapture(t, l, "c2", "m1", "USD", 3000, "card", Day)
	bs, err := l.Settle("m1", 3*Day-1)
	hiddenMust(t, err)
	hiddenEq(t, "one second early", len(bs), 0)
	bs, _ = l.Settle("m1", 3*Day)
	hiddenEq(t, "exactly at AvailableOn", hiddenBatches(bs), "[{ID:b1 Merchant:m1 Currency:USD TS:259200 Charges:[c2] Gross:3000 Fees:30 Net:2970}]")
	bs, _ = l.Settle("m1", 3*Day+10)
	hiddenEq(t, "settle again", len(bs), 0)
	bs, _ = l.Settle("m1", 5*Day)
	hiddenEq(t, "bank charge", hiddenBatches(bs), "[{ID:b2 Merchant:m1 Currency:USD TS:432000 Charges:[c1] Gross:5000 Fees:50 Net:4950}]")
	hiddenEq(t, "pending", l.Balance(PendingAccount("m1"), "USD"), 0)
	hiddenEq(t, "available", l.Balance(AvailableAccount("m1"), "USD"), 7920)
	hiddenEq(t, "fees", l.Balance(FeesAccount, "USD"), 80)
}

func Test_p2_one_batch_per_currency_with_half_up_fees(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 100, map[string]int64{"USD": 30, "JPY": 40, "EUR": 25})
	hiddenCapture(t, l, "u1", "m1", "USD", 150, "card", 0)
	hiddenCapture(t, l, "j1", "m1", "JPY", 12345, "card", 10)
	hiddenCapture(t, l, "e1", "m1", "EUR", 249, "card", 20)
	hiddenCapture(t, l, "u2", "m1", "USD", 2049, "card", 30)
	hiddenCapture(t, l, "j2", "m1", "JPY", 50, "card", 40)
	bs, err := l.Settle("m1", 3*Day)
	hiddenMust(t, err)
	hiddenEq(t, "batches", hiddenBatches(bs), "[{ID:b1 Merchant:m1 Currency:EUR TS:259200 Charges:[e1] Gross:249 Fees:27 Net:222} "+
		"{ID:b2 Merchant:m1 Currency:JPY TS:259200 Charges:[j1 j2] Gross:12395 Fees:204 Net:12191} "+
		"{ID:b3 Merchant:m1 Currency:USD TS:259200 Charges:[u1 u2] Gross:2199 Fees:82 Net:2117}]")
	for _, cur := range []string{"EUR", "JPY", "USD"} {
		hiddenEq(t, cur+" pending", l.Balance(PendingAccount("m1"), cur), 0)
		hiddenEq(t, cur+" trial balance", l.TrialBalance(cur), 0)
	}
	hiddenEq(t, "JPY available", l.Balance(AvailableAccount("m1"), "JPY"), 12191)
	hiddenEq(t, "USD fees", l.Balance(FeesAccount, "USD"), 82)
}

func Test_p2_refunds_before_settlement_reduce_gross(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 300, map[string]int64{"USD": 30})
	hiddenCapture(t, l, "c1", "m1", "USD", 10000, "card", 0)
	hiddenCapture(t, l, "c2", "m1", "USD", 800, "card", 10)
	hiddenMust(t, l.Refund("c1", 2500, 20))
	hiddenMust(t, l.Refund("c2", 800, 30))
	bs, err := l.Settle("m1", 2*Day+10)
	hiddenMust(t, err)
	hiddenEq(t, "batches", hiddenBatches(bs), "[{ID:b1 Merchant:m1 Currency:USD TS:172810 Charges:[c1 c2] Gross:7500 Fees:384 Net:7116}]")
	hiddenEq(t, "available", l.Balance(AvailableAccount("m1"), "USD"), 7116)
	hiddenEq(t, "pending", l.Balance(PendingAccount("m1"), "USD"), 0)

	l = New()
	hiddenMerchant(t, l, "m2", 300, map[string]int64{"USD": 30})
	hiddenCapture(t, l, "x1", "m2", "USD", 500, "card", 0)
	hiddenMust(t, l.Refund("x1", 500, 5))
	bs, _ = l.Settle("m2", 2*Day)
	hiddenEq(t, "fully refunded charge", hiddenBatches(bs), "[{ID:b1 Merchant:m2 Currency:USD TS:172800 Charges:[x1] Gross:0 Fees:45 Net:-45}]")
	hiddenEq(t, "available goes negative", l.Balance(AvailableAccount("m2"), "USD"), -45)
	hiddenEq(t, "fees", l.Balance(FeesAccount, "USD"), 45)
	hiddenEq(t, "trial balance", l.TrialBalance("USD"), 0)
}

func Test_p2_refund_after_settlement_comes_from_available(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 200, map[string]int64{"USD": 20})
	hiddenCapture(t, l, "c1", "m1", "USD", 4000, "card", 0)
	hiddenCapture(t, l, "c2", "m1", "USD", 1000, "bank", 0)
	bs, err := l.Settle("m1", 2*Day)
	hiddenMust(t, err)
	hiddenEq(t, "first batch", hiddenBatches(bs), "[{ID:b1 Merchant:m1 Currency:USD TS:172800 Charges:[c1] Gross:4000 Fees:100 Net:3900}]")
	hiddenMust(t, l.Refund("c1", 1500, 2*Day+1))
	hiddenEq(t, "available after refund", l.Balance(AvailableAccount("m1"), "USD"), 2400)
	hiddenEq(t, "pending after refund", l.Balance(PendingAccount("m1"), "USD"), 1000)
	hiddenMust(t, l.Refund("c2", 1000, 2*Day+2))
	hiddenEq(t, "pending after unsettled refund", l.Balance(PendingAccount("m1"), "USD"), 0)
	c, _ := l.Charge("c1")
	hiddenEq(t, "c1 batch", c.Batch, "b1")
	bs, _ = l.Settle("m1", 5*Day)
	hiddenEq(t, "second batch", hiddenBatches(bs), "[{ID:b2 Merchant:m1 Currency:USD TS:432000 Charges:[c2] Gross:0 Fees:40 Net:-40}]")
	hiddenEq(t, "available", l.Balance(AvailableAccount("m1"), "USD"), 2360)
	hiddenEq(t, "fees", l.Balance(FeesAccount, "USD"), 140)
	hiddenEq(t, "trial balance", l.TrialBalance("USD"), 0)
}

func Test_p2_charge_order_and_merchant_isolation(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "m1", 100, nil)
	hiddenMerchant(t, l, "m2", 100, nil)
	hiddenCapture(t, l, "a", "m1", "USD", 1000, "bank", 0)
	hiddenCapture(t, l, "c", "m1", "USD", 1200, "card", 2*Day)
	hiddenCapture(t, l, "b", "m1", "USD", 1300, "card", 3*Day)
	hiddenCapture(t, l, "z", "m2", "USD", 7000, "card", 3*Day+1)
	hiddenCapture(t, l, "d", "m1", "USD", 1400, "card", 3*Day+5)
	bs, err := l.Settle("m1", 5*Day)
	hiddenMust(t, err)
	hiddenEq(t, "first batch", hiddenBatches(bs), "[{ID:b1 Merchant:m1 Currency:USD TS:432000 Charges:[c a b] Gross:3500 Fees:35 Net:3465}]")
	bs, _ = l.Settle("m1", 5*Day+5)
	hiddenEq(t, "second batch", hiddenBatches(bs), "[{ID:b2 Merchant:m1 Currency:USD TS:432005 Charges:[d] Gross:1400 Fees:14 Net:1386}]")
	hiddenEq(t, "m1 available", l.Balance(AvailableAccount("m1"), "USD"), 4851)
	hiddenEq(t, "m2 pending untouched", l.Balance(PendingAccount("m2"), "USD"), 7000)
	hiddenEq(t, "m2 available untouched", l.Balance(AvailableAccount("m2"), "USD"), 0)
	_, err = l.Settle("nobody", 6*Day)
	hiddenIsErr(t, "unknown merchant", err, ErrUnknownMerchant)
	_, err = l.Settle("m2", 4*Day)
	hiddenIsErr(t, "backdated settle", err, ErrBackdated)
	bs, _ = l.Settle("m2", 6*Day)
	hiddenEq(t, "m2 batch", hiddenBatches(bs), "[{ID:b3 Merchant:m2 Currency:USD TS:518400 Charges:[z] Gross:7000 Fees:70 Net:6930}]")
}

// ---------------------------------------------------------------- phase 3

func Test_p3_settlement_polling_at_scale(t *testing.T) {
	l := New()
	hiddenMerchant(t, l, "big", 250, map[string]int64{"USD": 25})
	const n, polls = 30000, 30
	settled, nb := 0, 0
	start := time.Now()
	for i := 0; i < n; i++ {
		ts := int64(i) * 60
		method := "card"
		if i%4 == 0 {
			method = "bank"
		}
		if _, err := l.Capture("ch"+strconv.Itoa(i), "big", "USD", int64(500+i%1000), method, ts); err != nil {
			t.Fatal(err)
		}
		for j := 0; j < polls; j++ {
			bs, err := l.Settle("big", ts+int64(j*60/polls))
			if err != nil {
				t.Fatal(err)
			}
			nb += len(bs)
			for _, b := range bs {
				settled += len(b.Charges)
			}
		}
	}
	elapsed := time.Since(start)
	hiddenEq(t, "charges settled", settled, 26040)
	hiddenEq(t, "batches", nb, 26040)
	hiddenEq(t, "available", l.Balance(AvailableAccount("big"), "USD"), 24668490)
	hiddenEq(t, "pending", l.Balance(PendingAccount("big"), "USD"), 4016000)
	hiddenEq(t, "fees", l.Balance(FeesAccount, "USD"), 1300510)
	if elapsed > 2*time.Second {
		t.Fatalf("too slow: %d captures with %d settlement polls each took %v (budget 2s)", n, polls, elapsed)
	}
}
