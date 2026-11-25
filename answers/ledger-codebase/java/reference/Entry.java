import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** One double-entry journal entry. {@code id} is assigned when the entry is posted. */
public final class Entry {
    public final long ts;
    public final List<Posting> postings;
    public final String memo;
    String id = "";

    public Entry(long ts, List<Posting> postings, String memo) {
        this.ts = ts;
        this.postings = new ArrayList<>(postings);
        this.memo = memo;
    }

    public Entry(long ts, List<Posting> postings) {
        this(ts, postings, "");
    }

    public String id() {
        return id;
    }

    /**
     * Checks that this is a well-formed double entry: at least two postings, no empty accounts or zero
     * amounts, only booked currencies, and debits equal to credits.
     */
    void validate() {
        if (postings.size() < 2) throw new LedgerError.Invalid("an entry needs at least two postings");
        Map<String, Long> sums = new HashMap<>();
        for (Posting p : postings) {
            if (p.account().isEmpty() || p.amount() == 0) throw new LedgerError.Invalid("empty account or zero amount");
            if (!Money.validCurrency(p.currency())) throw new LedgerError.UnknownCurrency("'" + p.currency() + "'");
            sums.merge(p.currency(), p.amount(), Long::sum);
        }
        for (Posting p : postings) {
            long s = sums.get(p.currency());
            if (s != 0) throw new LedgerError.Unbalanced("entry does not balance: off by " + Money.formatAmount(s, p.currency()));
        }
    }
}
