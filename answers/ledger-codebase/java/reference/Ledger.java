import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** The Ledger service the payment flows call. Not safe for concurrent use. */
public final class Ledger {
    /** One day in ledger time (seconds). */
    public static final long DAY = 86400;

    final Store store = new Store();
    final ChargeBook charges = new ChargeBook();
    final Map<String, Pricing> merchants = new HashMap<>();
    long batchSeq;

    /** Onboards a merchant with its pricing. */
    public void addMerchant(String merchantId, Pricing pricing) {
        if (merchantId.isEmpty() || pricing.bps() < 0) throw new LedgerError.Invalid("merchant '" + merchantId + "'");
        if (merchants.containsKey(merchantId)) throw new LedgerError.Duplicate("merchant '" + merchantId + "'");
        merchants.put(merchantId, pricing);
    }

    /** Validates and books a journal entry. Entries must arrive in time order. */
    public Entry post(Entry e) {
        e.validate();
        if (e.ts < store.headTs) throw new LedgerError.Backdated("entry at " + e.ts);
        return store.append(new Entry(e.ts, e.postings, e.memo));
    }

    /** The current balance of account in cur. */
    public long balance(String account, String cur) {
        return store.balance(new Store.Acct(account, cur));
    }

    /** The balance of account in cur as of time ts (inclusive). */
    public long balanceAt(String account, String cur, long ts) {
        return store.balanceAt(new Store.Acct(account, cur), ts);
    }

    /** The account's lines with start <= ts <= end, newest first, as the merchant dashboard shows them. */
    public List<Line> statement(String account, String cur, long start, long end) {
        List<Line> lines = store.history(new Store.Acct(account, cur));
        Collections.reverse(lines);
        List<Line> out = new ArrayList<>();
        for (Line x : lines) {
            if (start <= x.ts() && x.ts() <= end) out.add(x);
        }
        return out;
    }

    /** Sum of every account's balance in cur. A healthy ledger always returns 0. */
    public long trialBalance(String cur) {
        long sum = 0;
        for (Store.Acct b : store.lines.keySet()) {
            if (b.currency().equals(cur)) sum += store.balance(b);
        }
        return sum;
    }

    public Charge capture(String chargeId, String merchant, String cur, long amount, String method, long ts) {
        return Payments.capture(this, chargeId, merchant, cur, amount, method, ts);
    }

    public void refund(String chargeId, long amount, long ts) {
        Payments.refund(this, chargeId, amount, ts);
    }

    /** A copy of the charge with this id, or null. */
    public Charge charge(String chargeId) {
        Charge c = charges.get(chargeId);
        return c == null ? null : c.copy();
    }

    public Payout requestPayout(String payoutId, String merchant, String cur, long amount, long ts) {
        return Payouts.request(this, payoutId, merchant, cur, amount, ts);
    }

    public void payoutPaid(String payoutId, long ts) {
        Payouts.finish(this, payoutId, "paid", ts);
    }

    public void payoutFailed(String payoutId, long ts) {
        Payouts.finish(this, payoutId, "failed", ts);
    }

    /** A copy of the payout with this id, or null. */
    public Payout payout(String payoutId) {
        Payout p = store.payouts.get(payoutId);
        return p == null ? null : p.copy();
    }

    public List<Batch> settle(String merchant, long ts) {
        return Settlement.settle(this, merchant, ts);
    }
}
