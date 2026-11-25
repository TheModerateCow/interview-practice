# Settlement ledger

You've joined the team that owns the **merchant ledger** of a payment platform. Merchants take card and bank payments; the ledger books each captured payment into the merchant's *pending* balance, settles it into their *available* balance minus the platform's fees, and pays available funds out to the merchant's bank. Every movement is a balanced double entry, and every amount is an integer number of minor units (cents, yen, fils).

The code is a small Java 21 package (default package, standard library only): the journal types (`Entry`, `Posting`) with an in-memory `Store` of per-account running balances, the `Ledger` service, the payment flows (`Payments`, `Payouts`, `Settlement`), and a small stdin driver in `Main.java`. Read around before you change anything.

The round has **3 phases**: fix the bugs below, build settlement, then a third part that opens once phase 2 passes (or with 15 minutes left, or when you press **Next part**).

## Phase 1: bug report

> **LEDGER-412 · three reports from support and finance this week**
>
> 1. **Dashboard balances go wrong after viewing a statement.** A merchant opened the statement for their pending account and the balance widget next to it then showed an old figure; `balanceAt` for earlier dates came back wrong too. When they reloaded the statement, the lines came back oldest first instead of newest first. Balances are right again if nobody looks at a statement.
> 2. **Bank webhook retries.** A payout failed and the bank delivered the "failed" webhook twice. The merchant's available balance was credited back twice. Finance also found a payout the bank had confirmed as paid that later accepted a "failed" webhook. `payout(id)` still shows these payouts as `pending`.
> 3. **Unbalanced adjustment accepted.** Ops booked an adjustment of +1.00 USD and −1.00 EUR against the suspense account. It should have been rejected, but it posted, and the USD trial balance is now off by 1.00.

This test reproduces item 2 and fails today. Paste it into a `*Test.java` file (with `import java.util.List;`) to use it:

```java
public class PayoutRetryTest {
    static void testPayoutWebhookRetry() {
        Ledger l = new Ledger();
        l.addMerchant("m1", new Pricing(250));
        l.post(new Entry(1, List.of(new Posting(Journal.availableAccount("m1"), "USD", 2000),
                new Posting(Journal.CLEARING_ACCOUNT, "USD", -2000))));
        l.requestPayout("p1", "m1", "USD", 1500, 2);
        l.payoutFailed("p1", 3);
        l.payoutFailed("p1", 4);  // the bank retries the webhook
        Expect.eq(2000L, l.balance(Journal.availableAccount("m1"), "USD"));
    }
}
```

Fix the cause of each one, not just the symptom.

## Phase 2: settlement

Implement `Settlement.settle` in `Settlement.java` (it backs `Ledger.settle`):

```java
static List<Batch> settle(Ledger l, String merchant, long ts)
```

It settles every charge of `merchant` whose funds are available at time `ts`.

- **Errors.** An unknown merchant throws `LedgerError.UnknownMerchant`. A `ts` older than the newest entry in the ledger throws `LedgerError.Backdated`. Either way nothing changes.
- **Which charges.** A charge is due when it hasn't been settled yet and `availableOn <= ts`. `capture` already sets `availableOn` (capture time plus a hold: 2 days for `card`, 5 days for `bank`). `l.charges.due(merchant, ts)` returns the due charges, earliest `availableOn` first, with capture order breaking ties. A charge counts as settled once its `batch` field is set, so `settle` must set it. `refund` reads it to decide whether money comes out of pending or available.
- **Batches.** One `Batch` per currency, returned sorted by currency code. If nothing is due, return no batches and post nothing. Batch ids are `b1`, `b2`, ... numbered across the whole ledger in the order batches are created. `ts` is `ts`, and `charges` lists the charge ids in due order.
- **Amounts.** `gross` is the sum of each charge's `amount - refunded`. `fees` is the sum of the merchant's `Pricing` fee on each charge's original captured `amount` (`Pricing.fee` already does the rounding). Fees are charged even on fully refunded charges. `net = gross - fees`, which can be negative.
- **Booking.** For each batch, post one entry at `ts`: pending `-gross`, available `+net`, `platform:fees` `+fees`, all in the batch's currency. Leave out zero-amount postings, since the journal rejects them. If all three are zero, post nothing.

### Example

Merchant `m1` pays 290 bps plus a fixed 30 (USD cents) or 40 (yen) per charge:

```
capture("c1", "m1", "USD", 10000, "card", 0)     // available from 172800
capture("c2", "m1", "JPY", 5000, "card", 60)     // available from 172860
capture("c3", "m1", "USD", 2500, "bank", 120)    // available from 432120
refund("c1", 1000, 180)
settle("m1", 172860) ->
  Batch(id=b1, currency=JPY, charges=[c2], gross=5000, fees=185, net=4815)
  Batch(id=b2, currency=USD, charges=[c1], gross=9000, fees=320, net=8680)
```

After this, m1's USD pending balance is 2500 (c3), USD available is 8680 and `platform:fees` holds 320 USD.

## Checking your work

- **Run** runs `Main.java`, which reads commands from stdin (`merchant`, `capture`, `refund`, `settle`, `post`, `payout`, `paid`, `failed`, `balance`; see the top of the file). Extend it as you like.
- **My tests** runs your own `*Test.java` files: every `static void` method whose name starts with `test`, checked with `Expect.eq`, `Expect.isTrue` and `Expect.raises` (no JUnit). `ExampleTest.java` is an example to copy.
- **Submit** runs the hidden tests for every phase you've unlocked.
