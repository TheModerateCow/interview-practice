# Settlement ledger

You've joined the team that owns the **merchant ledger** of a payment platform. Merchants take card and bank payments; the ledger books each captured payment into the merchant's *pending* balance, settles it into their *available* balance minus the platform's fees, and pays available funds out to the merchant's bank. Every movement is a balanced double entry, and every amount is an integer number of minor units (cents, yen, fils).

The code is Go package `ledger` (standard library only): a journal with an in-memory store and per-account running balances, the `Ledger` service, the payment flows (captures and refunds, payouts, settlement), and a small stdin driver in `cmd/run`. Read around before you change anything.

The round has **3 phases**: fix the bugs below, build settlement, then a third part that opens once phase 2 passes (or with 15 minutes left, or when you press **Next part**).

## Phase 1: bug report

> **LEDGER-412 · three reports from support and finance this week**
>
> 1. **Dashboard balances go wrong after viewing a statement.** A merchant opened the statement for their pending account and the balance widget next to it then showed an old figure; `BalanceAt` for earlier dates came back wrong too. When they reloaded the statement, the lines came back oldest first instead of newest first. Balances are right again if nobody looks at a statement.
> 2. **Bank webhook retries.** A payout failed and the bank delivered the "failed" webhook twice. The merchant's available balance was credited back twice. Finance also found a payout the bank had confirmed as paid that later accepted a "failed" webhook. `Payout(id)` still shows these payouts as `pending`.
> 3. **Unbalanced adjustment accepted.** Ops booked an adjustment of +1.00 USD and −1.00 EUR against the suspense account. It should have been rejected, but it posted, and the USD trial balance is now off by 1.00.

This test reproduces item 2 and fails today. Paste it into a `_test.go` file to use it:

```go
func TestPayoutWebhookRetry(t *testing.T) {
	l := New()
	l.AddMerchant("m1", Pricing{Bps: 250})
	l.Post(Entry{TS: 1, Postings: []Posting{
		{AvailableAccount("m1"), "USD", 2000}, {ClearingAccount, "USD", -2000}}})
	l.RequestPayout("p1", "m1", "USD", 1500, 2)
	l.PayoutFailed("p1", 3)
	l.PayoutFailed("p1", 4) // the bank retries the webhook
	if got := l.Balance(AvailableAccount("m1"), "USD"); got != 2000 {
		t.Fatalf("available: got %d want 2000", got)
	}
}
```

Fix the cause of each one, not just the symptom.

## Phase 2: settlement

Implement `Settle` in `settlement.go`:

```go
func (l *Ledger) Settle(merchant string, ts int64) ([]Batch, error)
```

It settles every charge of `merchant` whose funds are available at time `ts`.

- **Errors.** An unknown merchant returns `ErrUnknownMerchant`. A `ts` older than the newest entry in the ledger returns `ErrBackdated`. Either way nothing changes.
- **Which charges.** A charge is due when it hasn't been settled yet and `AvailableOn <= ts`. `Capture` already sets `AvailableOn` (capture time plus a hold: 2 days for `card`, 5 days for `bank`). `l.charges.due(merchant, ts)` returns the due charges, earliest `AvailableOn` first, with capture order breaking ties. A charge counts as settled once its `Batch` field is set, so `Settle` must set it. `Refund` reads it to decide whether money comes out of pending or available.
- **Batches.** One `Batch` per currency, returned sorted by currency code. If nothing is due, return no batches and post nothing. Batch IDs are `b1`, `b2`, … numbered across the whole ledger in the order batches are created. `TS` is `ts`, and `Charges` lists the charge IDs in due order.
- **Amounts.** `Gross` is the sum of each charge's `Amount - Refunded`. `Fees` is the sum of the merchant's `Pricing` fee on each charge's original captured `Amount` (`Pricing.fee` already does the rounding). Fees are charged even on fully refunded charges. `Net = Gross - Fees`, which can be negative.
- **Booking.** For each batch, post one entry at `ts`: pending `-Gross`, available `+Net`, `platform:fees` `+Fees`, all in the batch's currency. Leave out zero-amount postings, since the journal rejects them. If all three are zero, post nothing.

### Example

Merchant `m1` pays 290 bps plus a fixed 30 (USD cents) or 40 (yen) per charge:

```
Capture("c1", "m1", "USD", 10000, "card", 0)     // available from 172800
Capture("c2", "m1", "JPY", 5000, "card", 60)     // available from 172860
Capture("c3", "m1", "USD", 2500, "bank", 120)    // available from 432120
Refund("c1", 1000, 180)
Settle("m1", 172860) ->
  {ID: b1, Currency: JPY, Charges: [c2], Gross: 5000, Fees: 185, Net: 4815}
  {ID: b2, Currency: USD, Charges: [c1], Gross: 9000, Fees: 320, Net: 8680}
```

After this, m1's USD pending balance is 2500 (c3), USD available is 8680 and `platform:fees` holds 320 USD.

## Checking your work

- **Run** runs `cmd/run/main.go`, which reads commands from stdin (`merchant`, `capture`, `refund`, `settle`, `post`, `payout`, `paid`, `failed`, `balance`; see the top of the file). Extend it as you like.
- **My tests** runs your own `*_test.go` files. `ledger_example_test.go` is an example to copy.
- **Submit** runs the hidden tests for every phase you've unlocked.
