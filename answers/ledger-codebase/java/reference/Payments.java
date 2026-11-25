import java.util.List;

/** Captures and refunds. */
final class Payments {
    private Payments() {}

    /**
     * Books a captured payment: the platform is now owed amount by the card network or bank (clearing),
     * and owes it to the merchant once it settles (pending).
     */
    static Charge capture(Ledger l, String chargeId, String merchant, String cur, long amount, String method, long ts) {
        if (!l.merchants.containsKey(merchant)) throw new LedgerError.UnknownMerchant("'" + merchant + "'");
        Long hold = ChargeBook.HOLDS.get(method);
        if (hold == null || amount <= 0 || chargeId.isEmpty()) throw new LedgerError.Invalid("capture '" + chargeId + "'");
        if (l.charges.get(chargeId) != null) throw new LedgerError.Duplicate("charge '" + chargeId + "'");
        l.post(new Entry(ts, List.of(new Posting(Journal.CLEARING_ACCOUNT, cur, -amount),
                new Posting(Journal.pendingAccount(merchant), cur, amount)), "capture " + chargeId));
        Charge c = new Charge(chargeId, merchant, cur, method, amount, ts, ts + hold);
        l.charges.add(c);
        return c.copy();
    }

    /**
     * Sends amount of a charge back to the customer. Before the charge settles the money comes out of the
     * merchant's pending balance; after, out of available, which may go negative. Fees are not returned.
     */
    static void refund(Ledger l, String chargeId, long amount, long ts) {
        Charge c = l.charges.get(chargeId);
        if (c == null) throw new LedgerError.NotFound("charge '" + chargeId + "'");
        if (amount <= 0 || amount > c.amount - c.refunded) {
            throw new LedgerError.Invalid("refund " + amount + " of '" + chargeId + "'");
        }
        String source = Journal.pendingAccount(c.merchant);
        if (!c.batch.isEmpty()) source = Journal.availableAccount(c.merchant);
        l.post(new Entry(ts, List.of(new Posting(source, c.currency, -amount),
                new Posting(Journal.CLEARING_ACCOUNT, c.currency, amount)), "refund " + chargeId));
        c.refunded += amount;
    }
}
