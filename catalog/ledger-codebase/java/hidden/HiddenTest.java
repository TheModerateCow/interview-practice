import java.util.ArrayList;
import java.util.List;
import java.util.Map;

// The app compiles one phase's tests at a time: helpers use only the phase-1 API.
public class HiddenTest {
    static final long DAY = Ledger.DAY;

    static void hiddenMerchant(Ledger l, String id, long bps, Map<String, Long> fixed) {
        l.addMerchant(id, new Pricing(bps, fixed));
    }

    static void hiddenMerchant(Ledger l, String id, long bps) {
        l.addMerchant(id, new Pricing(bps));
    }

    static String hiddenLines(List<Line> ls) {
        List<String> out = new ArrayList<>();
        for (Line x : ls) out.add(x.ts() + "/" + x.entryId() + "/" + x.amount() + "/" + x.balance());
        return String.join(";", out);
    }

    static String hiddenBatches(List<Batch> bs) {
        List<String> out = new ArrayList<>();
        for (Batch b : bs) {
            out.add(b.id + " " + b.merchant + " " + b.currency + " " + b.ts + " " + b.charges + " " + b.gross + " " + b.fees + " " + b.net);
        }
        return String.join(" | ", out);
    }

    /** Puts amount straight into a merchant's available balance, as an ops adjustment. */
    static void hiddenFund(Ledger l, String m, String cur, long amount, long ts) {
        l.post(new Entry(ts, List.of(new Posting(Journal.availableAccount(m), cur, amount),
                new Posting(Journal.CLEARING_ACCOUNT, cur, -amount)), "adjustment"));
    }

    static Ledger hiddenStatementLedger() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 250);
        l.capture("c1", "m1", "USD", 1000, "card", 10);
        l.capture("c2", "m1", "USD", 2500, "card", 20);
        l.capture("c3", "m1", "USD", 400, "card", 30);
        l.refund("c2", 500, 40);
        return l;
    }

    static final String HIDDEN_FULL = "40/e4/-500/3400;30/e3/400/3900;20/e2/2500/3500;10/e1/1000/1000";

    // ---------------------------------------------------------------- phase 1

    static void test_p1_statement_leaves_balances_alone() {
        Ledger l = hiddenStatementLedger();
        String acct = Journal.pendingAccount("m1");
        Expect.eq(HIDDEN_FULL, hiddenLines(l.statement(acct, "USD", 0, 100)));
        Expect.eq(3400L, l.balance(acct, "USD"));
        Expect.eq(3500L, l.balanceAt(acct, "USD", 25));
        Expect.eq(0L, l.balanceAt(acct, "USD", 5));
        Expect.eq(3400L, l.balanceAt(acct, "USD", 40));
        Expect.eq(0L, l.trialBalance("USD"));
    }

    static void test_p1_repeated_statements_agree() {
        Ledger l = hiddenStatementLedger();
        String acct = Journal.pendingAccount("m1");
        String first = hiddenLines(l.statement(acct, "USD", 15, 35));
        Expect.eq("30/e3/400/3900;20/e2/2500/3500", first);
        Expect.eq(first, hiddenLines(l.statement(acct, "USD", 15, 35)));
        Expect.eq(HIDDEN_FULL, hiddenLines(l.statement(acct, "USD", 0, 100)));
        Expect.eq(3900L, l.balanceAt(acct, "USD", 30));
        Expect.eq(3400L, l.balance(acct, "USD"));
    }

    static void test_p1_failed_payout_webhook_retry_credits_once() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 250);
        hiddenFund(l, "m1", "USD", 5000, 1);
        l.requestPayout("p1", "m1", "USD", 3000, 2);
        Expect.eq(2000L, l.balance(Journal.availableAccount("m1"), "USD"));
        Expect.eq(3000L, l.balance(Journal.IN_TRANSIT_ACCOUNT, "USD"));
        l.payoutFailed("p1", 3);
        l.payoutFailed("p1", 4); // the bank retries the webhook
        Expect.eq(5000L, l.balance(Journal.availableAccount("m1"), "USD"));
        Expect.eq(0L, l.balance(Journal.IN_TRANSIT_ACCOUNT, "USD"));
        Payout p = l.payout("p1");
        Expect.isTrue(p != null);
        Expect.eq("failed", p.status);
        Expect.eq(3L, p.updatedAt);
        Expect.raises(LedgerError.InsufficientFunds.class, () -> l.requestPayout("p2", "m1", "USD", 5001, 5));
        Expect.eq(0L, l.trialBalance("USD"));
    }

    static void test_p1_paid_payout_cannot_then_fail() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 250);
        hiddenFund(l, "m1", "EUR", 8000, 1);
        l.requestPayout("p1", "m1", "EUR", 3000, 2);
        l.payoutPaid("p1", 3);
        l.payoutPaid("p1", 4);
        Expect.raises(LedgerError.PayoutState.class, () -> l.payoutFailed("p1", 5));
        Expect.eq(3000L, l.balance(Journal.BANK_ACCOUNT, "EUR"));
        Expect.eq(0L, l.balance(Journal.IN_TRANSIT_ACCOUNT, "EUR"));
        Expect.eq(5000L, l.balance(Journal.availableAccount("m1"), "EUR"));
        Expect.eq("paid", l.payout("p1").status);
    }

    static void test_p1_payout_requests() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 250);
        hiddenFund(l, "m1", "USD", 1000, 1);
        l.requestPayout("p1", "m1", "USD", 1000, 2);
        Expect.raises(LedgerError.Duplicate.class, () -> l.requestPayout("p1", "m1", "USD", 1, 3));
        Expect.raises(LedgerError.Invalid.class, () -> l.requestPayout("p2", "m1", "USD", 0, 3));
        Expect.raises(LedgerError.InsufficientFunds.class, () -> l.requestPayout("p3", "m1", "USD", 1, 3));
        Expect.raises(LedgerError.NotFound.class, () -> l.payoutPaid("nope", 4));
        Expect.eq(0L, l.balance(Journal.availableAccount("m1"), "USD"));
    }

    static void test_p1_entries_balance_in_every_currency() {
        Ledger l = new Ledger();
        Expect.raises(LedgerError.Unbalanced.class, () -> l.post(new Entry(1,
                List.of(new Posting("ops:suspense", "USD", 100), new Posting("ops:suspense", "EUR", -100)), "bad adjustment")));
        Expect.eq(0L, l.trialBalance("USD"));
        Expect.eq(0L, l.trialBalance("EUR"));
        Expect.eq(0L, l.balance("ops:suspense", "USD"));
        l.post(new Entry(2, List.of(new Posting("customer:9", "USD", -1000), new Posting("platform:fx", "USD", 1000),
                new Posting("platform:fx", "EUR", -920), new Posting("customer:9", "EUR", 920)), "fx conversion"));
        Expect.eq(1000L, l.balance("platform:fx", "USD"));
        Expect.eq(920L, l.balance("customer:9", "EUR"));
        Expect.raises(LedgerError.Unbalanced.class, () -> l.post(new Entry(3,
                List.of(new Posting("a", "JPY", 500), new Posting("b", "JPY", -400),
                        new Posting("c", "KWD", 1000), new Posting("d", "KWD", -1100)))));
        Expect.eq(0L, l.trialBalance("JPY"));
    }

    static void test_p1_entry_validation() {
        Ledger l = new Ledger();
        Expect.raises(LedgerError.Invalid.class, () -> l.post(new Entry(1,
                List.of(new Posting("a", "USD", 0), new Posting("b", "USD", 0)))));
        Expect.raises(LedgerError.Invalid.class, () -> l.post(new Entry(1, List.of(new Posting("a", "USD", 5)))));
        Expect.raises(LedgerError.UnknownCurrency.class, () -> l.post(new Entry(1,
                List.of(new Posting("a", "XYZ", 5), new Posting("b", "XYZ", -5)))));
        Entry e = l.post(new Entry(10, List.of(new Posting("a", "USD", 5), new Posting("b", "USD", -5))));
        Expect.eq("e1", e.id());
        Expect.raises(LedgerError.Backdated.class, () -> l.post(new Entry(9,
                List.of(new Posting("a", "USD", 5), new Posting("b", "USD", -5)))));
    }

    static void test_p1_refund_limits() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 250);
        l.capture("c1", "m1", "GBP", 1000, "card", 1);
        l.refund("c1", 600, 2);
        Expect.raises(LedgerError.Invalid.class, () -> l.refund("c1", 401, 3));
        l.refund("c1", 400, 4);
        Expect.raises(LedgerError.Invalid.class, () -> l.refund("c1", 1, 5));
        Expect.raises(LedgerError.NotFound.class, () -> l.refund("c9", 1, 5));
        Expect.raises(LedgerError.Duplicate.class, () -> l.capture("c1", "m1", "GBP", 1000, "card", 6));
        Expect.raises(LedgerError.UnknownMerchant.class, () -> l.capture("c2", "m9", "GBP", 1000, "card", 6));
        Expect.eq(0L, l.balance(Journal.pendingAccount("m1"), "GBP"));
        Expect.eq(1000L, l.charge("c1").refunded);
    }

    // ---------------------------------------------------------------- phase 2

    static void test_p2_settles_available_charges_minus_fees() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 290, Map.of("USD", 30L));
        l.capture("c1", "m1", "USD", 10000, "card", 0);
        l.capture("c2", "m1", "USD", 2500, "card", 100);
        List<Batch> bs = l.settle("m1", 2 * DAY + 50);
        Expect.eq("b1 m1 USD 172850 [c1] 10000 320 9680", hiddenBatches(bs));
        Expect.eq(2500L, l.balance(Journal.pendingAccount("m1"), "USD"));
        Expect.eq(9680L, l.balance(Journal.availableAccount("m1"), "USD"));
        Expect.eq(320L, l.balance(Journal.FEES_ACCOUNT, "USD"));
        Expect.eq(0L, l.trialBalance("USD"));
        Expect.eq("b1", l.charge("c1").batch);
        Expect.eq("", l.charge("c2").batch);
    }

    static void test_p2_cutoff_is_inclusive_and_charges_settle_once() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 100);
        l.capture("c1", "m1", "USD", 5000, "bank", 0);
        l.capture("c2", "m1", "USD", 3000, "card", DAY);
        Expect.eq(0, l.settle("m1", 3 * DAY - 1).size());
        Expect.eq("b1 m1 USD 259200 [c2] 3000 30 2970", hiddenBatches(l.settle("m1", 3 * DAY)));
        Expect.eq(0, l.settle("m1", 3 * DAY + 10).size());
        Expect.eq("b2 m1 USD 432000 [c1] 5000 50 4950", hiddenBatches(l.settle("m1", 5 * DAY)));
        Expect.eq(0L, l.balance(Journal.pendingAccount("m1"), "USD"));
        Expect.eq(7920L, l.balance(Journal.availableAccount("m1"), "USD"));
        Expect.eq(80L, l.balance(Journal.FEES_ACCOUNT, "USD"));
    }

    static void test_p2_one_batch_per_currency_with_half_up_fees() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 100, Map.of("USD", 30L, "JPY", 40L, "EUR", 25L));
        l.capture("u1", "m1", "USD", 150, "card", 0);
        l.capture("j1", "m1", "JPY", 12345, "card", 10);
        l.capture("e1", "m1", "EUR", 249, "card", 20);
        l.capture("u2", "m1", "USD", 2049, "card", 30);
        l.capture("j2", "m1", "JPY", 50, "card", 40);
        List<Batch> bs = l.settle("m1", 3 * DAY);
        Expect.eq("b1 m1 EUR 259200 [e1] 249 27 222 | b2 m1 JPY 259200 [j1, j2] 12395 204 12191 | b3 m1 USD 259200 [u1, u2] 2199 82 2117",
                hiddenBatches(bs));
        for (String cur : List.of("EUR", "JPY", "USD")) {
            Expect.eq(0L, l.balance(Journal.pendingAccount("m1"), cur));
            Expect.eq(0L, l.trialBalance(cur));
        }
        Expect.eq(12191L, l.balance(Journal.availableAccount("m1"), "JPY"));
        Expect.eq(82L, l.balance(Journal.FEES_ACCOUNT, "USD"));
    }

    static void test_p2_refunds_before_settlement_reduce_gross() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 300, Map.of("USD", 30L));
        l.capture("c1", "m1", "USD", 10000, "card", 0);
        l.capture("c2", "m1", "USD", 800, "card", 10);
        l.refund("c1", 2500, 20);
        l.refund("c2", 800, 30);
        Expect.eq("b1 m1 USD 172810 [c1, c2] 7500 384 7116", hiddenBatches(l.settle("m1", 2 * DAY + 10)));
        Expect.eq(7116L, l.balance(Journal.availableAccount("m1"), "USD"));
        Expect.eq(0L, l.balance(Journal.pendingAccount("m1"), "USD"));

        Ledger l2 = new Ledger();
        hiddenMerchant(l2, "m2", 300, Map.of("USD", 30L));
        l2.capture("x1", "m2", "USD", 500, "card", 0);
        l2.refund("x1", 500, 5);
        Expect.eq("b1 m2 USD 172800 [x1] 0 45 -45", hiddenBatches(l2.settle("m2", 2 * DAY)));
        Expect.eq(-45L, l2.balance(Journal.availableAccount("m2"), "USD"));
        Expect.eq(45L, l2.balance(Journal.FEES_ACCOUNT, "USD"));
        Expect.eq(0L, l2.trialBalance("USD"));
    }

    static void test_p2_refund_after_settlement_comes_from_available() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 200, Map.of("USD", 20L));
        l.capture("c1", "m1", "USD", 4000, "card", 0);
        l.capture("c2", "m1", "USD", 1000, "bank", 0);
        Expect.eq("b1 m1 USD 172800 [c1] 4000 100 3900", hiddenBatches(l.settle("m1", 2 * DAY)));
        l.refund("c1", 1500, 2 * DAY + 1);
        Expect.eq(2400L, l.balance(Journal.availableAccount("m1"), "USD"));
        Expect.eq(1000L, l.balance(Journal.pendingAccount("m1"), "USD"));
        l.refund("c2", 1000, 2 * DAY + 2);
        Expect.eq(0L, l.balance(Journal.pendingAccount("m1"), "USD"));
        Expect.eq("b1", l.charge("c1").batch);
        Expect.eq("b2 m1 USD 432000 [c2] 0 40 -40", hiddenBatches(l.settle("m1", 5 * DAY)));
        Expect.eq(2360L, l.balance(Journal.availableAccount("m1"), "USD"));
        Expect.eq(140L, l.balance(Journal.FEES_ACCOUNT, "USD"));
        Expect.eq(0L, l.trialBalance("USD"));
    }

    static void test_p2_charge_order_and_merchant_isolation() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "m1", 100);
        hiddenMerchant(l, "m2", 100);
        l.capture("a", "m1", "USD", 1000, "bank", 0);
        l.capture("c", "m1", "USD", 1200, "card", 2 * DAY);
        l.capture("b", "m1", "USD", 1300, "card", 3 * DAY);
        l.capture("z", "m2", "USD", 7000, "card", 3 * DAY + 1);
        l.capture("d", "m1", "USD", 1400, "card", 3 * DAY + 5);
        Expect.eq("b1 m1 USD 432000 [c, a, b] 3500 35 3465", hiddenBatches(l.settle("m1", 5 * DAY)));
        Expect.eq("b2 m1 USD 432005 [d] 1400 14 1386", hiddenBatches(l.settle("m1", 5 * DAY + 5)));
        Expect.eq(4851L, l.balance(Journal.availableAccount("m1"), "USD"));
        Expect.eq(7000L, l.balance(Journal.pendingAccount("m2"), "USD"));
        Expect.eq(0L, l.balance(Journal.availableAccount("m2"), "USD"));
        Expect.raises(LedgerError.UnknownMerchant.class, () -> l.settle("nobody", 6 * DAY));
        Expect.raises(LedgerError.Backdated.class, () -> l.settle("m2", 4 * DAY));
        Expect.eq("b3 m2 USD 518400 [z] 7000 70 6930", hiddenBatches(l.settle("m2", 6 * DAY)));
    }

    // ---------------------------------------------------------------- phase 3

    static void test_p3_settlement_polling_at_scale() {
        Ledger l = new Ledger();
        hiddenMerchant(l, "big", 250, Map.of("USD", 25L));
        int n = 15000, polls = 8;
        long settled = 0, nb = 0;
        long start = System.nanoTime();
        for (int i = 0; i < n; i++) {
            long ts = i * 60L;
            String method = i % 4 == 0 ? "bank" : "card";
            l.capture("ch" + i, "big", "USD", 500 + i % 1000, method, ts);
            for (int j = 0; j < polls; j++) {
                List<Batch> bs = l.settle("big", ts + j * 60 / polls);
                nb += bs.size();
                for (Batch b : bs) settled += b.charges.size();
            }
        }
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.eq("settled=11040 batches=11040 available=10425990 pending=4016000 fees=550510",
                "settled=" + settled + " batches=" + nb + " available=" + l.balance(Journal.availableAccount("big"), "USD")
                        + " pending=" + l.balance(Journal.pendingAccount("big"), "USD")
                        + " fees=" + l.balance(Journal.FEES_ACCOUNT, "USD"));
        Expect.isTrue(ms < BUDGET_MS, n + " captures with " + polls + " settlement polls each took " + ms + " ms (budget " + BUDGET_MS + " ms)");
    }

    static final long BUDGET_MS = 1000;
}
