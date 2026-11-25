import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Settlement: moving available charges from pending to available, minus fees. */
final class Settlement {
    private Settlement() {}

    /**
     * Moves every charge of merchant whose funds are available at ts from pending to available, minus
     * fees, as one batch per currency (sorted by currency code).
     */
    static List<Batch> settle(Ledger l, String merchant, long ts) {
        Pricing pricing = l.merchants.get(merchant);
        if (pricing == null) throw new LedgerError.UnknownMerchant("'" + merchant + "'");
        if (ts < l.store.headTs) throw new LedgerError.Backdated("settle at " + ts);
        List<Charge> due = l.charges.due(merchant, ts);
        Map<String, List<Charge>> groups = new TreeMap<>();
        for (Charge c : due) groups.computeIfAbsent(c.currency, k -> new ArrayList<>()).add(c);
        List<Batch> out = new ArrayList<>();
        for (Map.Entry<String, List<Charge>> g : groups.entrySet()) {
            String cur = g.getKey();
            Batch b = new Batch("b" + (++l.batchSeq), merchant, cur, ts);
            for (Charge c : g.getValue()) {
                b.charges.add(c.id);
                b.gross += c.amount - c.refunded;
                b.fees += pricing.fee(c.amount, cur);
                c.batch = b.id;
            }
            b.net = b.gross - b.fees;
            List<Posting> ps = new ArrayList<>();
            for (Posting p : List.of(
                    new Posting(Journal.pendingAccount(merchant), cur, -b.gross),
                    new Posting(Journal.availableAccount(merchant), cur, b.net),
                    new Posting(Journal.FEES_ACCOUNT, cur, b.fees))) {
                if (p.amount() != 0) ps.add(p);
            }
            if (!ps.isEmpty()) l.post(new Entry(ts, ps, "settlement " + b.id));
            out.add(b);
        }
        return out;
    }
}
