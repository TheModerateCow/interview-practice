import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

/**
 * In-memory journal: every entry in posting order, plus a per-account index of lines with running
 * balances so balance queries don't replay the journal.
 */
final class Store {
    record Acct(String account, String currency) {}

    final List<Entry> entries = new ArrayList<>();
    final Map<Acct, List<Line>> lines = new HashMap<>();
    long headTs;
    final Map<String, Payout> payouts = new HashMap<>();

    /** Records an already-validated entry and sets its id. */
    Entry append(Entry e) {
        e.id = "e" + (entries.size() + 1);
        entries.add(e);
        for (Posting p : e.postings) {
            List<Line> ls = lines.computeIfAbsent(new Acct(p.account(), p.currency()), k -> new ArrayList<>());
            long bal = p.amount() + (ls.isEmpty() ? 0 : ls.get(ls.size() - 1).balance());
            ls.add(new Line(e.ts, e.id, p.amount(), bal));
        }
        headTs = e.ts;
        return e;
    }

    /** An account's lines, oldest first. */
    List<Line> history(Acct b) {
        return new ArrayList<>(lines.getOrDefault(b, List.of()));
    }

    /** The account's balance after every posting with ts <= the given ts. */
    long balanceAt(Acct b, long ts) {
        List<Line> ls = lines.getOrDefault(b, List.of());
        int lo = 0, hi = ls.size();
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (ls.get(mid).ts() <= ts) lo = mid + 1;
            else hi = mid;
        }
        return lo == 0 ? 0 : ls.get(lo - 1).balance();
    }

    /** The account's current balance. */
    long balance(Acct b) {
        List<Line> ls = lines.get(b);
        return ls == null || ls.isEmpty() ? 0 : ls.get(ls.size() - 1).balance();
    }

    /**
     * Runs fn on a copy of the stored payout and keeps the copy only if fn succeeds, so a rejected
     * transition leaves the payout as it was.
     */
    void updatePayout(String payoutId, Consumer<Payout> fn) {
        Payout p = payouts.get(payoutId);
        if (p == null) throw new LedgerError.NotFound("payout '" + payoutId + "'");
        Payout nxt = p.copy();
        fn.accept(nxt);
        payouts.put(payoutId, nxt);
    }
}
