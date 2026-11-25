import java.util.List;

/** Payouts of available funds to the merchant's bank. */
final class Payouts {
    private Payouts() {}

    /** Moves amount from the merchant's available balance to in-transit. */
    static Payout request(Ledger l, String payoutId, String merchant, String cur, long amount, long ts) {
        if (payoutId.isEmpty() || amount <= 0) throw new LedgerError.Invalid("payout '" + payoutId + "'");
        if (l.store.payouts.containsKey(payoutId)) throw new LedgerError.Duplicate("payout '" + payoutId + "'");
        if (l.balance(Journal.availableAccount(merchant), cur) < amount) {
            throw new LedgerError.InsufficientFunds("insufficient available balance");
        }
        l.post(new Entry(ts, List.of(new Posting(Journal.availableAccount(merchant), cur, -amount),
                new Posting(Journal.IN_TRANSIT_ACCOUNT, cur, amount)), "payout " + payoutId));
        Payout p = new Payout(payoutId, merchant, cur, amount, "pending", ts);
        l.store.payouts.put(payoutId, p);
        return p.copy();
    }

    /** The bank's webhook: "paid" or "failed". The bank retries webhooks, so a repeat of the same outcome changes nothing. */
    static void finish(Ledger l, String payoutId, String to, long ts) {
        l.store.updatePayout(payoutId, p -> {
            if (p.status.equals(to)) return;
            if (!p.status.equals("pending")) {
                throw new LedgerError.PayoutState(p.status + " payout '" + payoutId + "' cannot become " + to);
            }
            String dest = to.equals("failed") ? Journal.availableAccount(p.merchant) : Journal.BANK_ACCOUNT;
            l.post(new Entry(ts, List.of(new Posting(Journal.IN_TRANSIT_ACCOUNT, p.currency, -p.amount),
                    new Posting(dest, p.currency, p.amount)), "payout " + payoutId + " " + to));
            p.status = to;
            p.updatedAt = ts;
        });
    }
}
