import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;

/**
 * Every captured charge by id, plus each merchant's unsettled charges in a min-heap keyed on when their
 * funds become available (capture order breaks ties).
 */
final class ChargeBook {
    /** How long captured funds wait before they can be settled, by payment method. */
    static final Map<String, Long> HOLDS = Map.of("card", 2 * Ledger.DAY, "bank", 5 * Ledger.DAY);

    private static final Comparator<Charge> ORDER =
            Comparator.comparingLong((Charge c) -> c.availableOn).thenComparingLong(c -> c.seq);

    private final Map<String, Charge> byId = new HashMap<>();
    private final Map<String, PriorityQueue<Charge>> pending = new HashMap<>();

    void add(Charge c) {
        c.seq = byId.size();
        byId.put(c.id, c);
        pending.computeIfAbsent(c.merchant, k -> new PriorityQueue<>(ORDER)).add(c);
    }

    Charge get(String chargeId) {
        return byId.get(chargeId);
    }

    /**
     * The merchant's unsettled charges whose funds are available at ts, earliest availableOn first
     * (capture order breaks ties). Takes them off the pending set.
     */
    List<Charge> due(String merchant, long ts) {
        PriorityQueue<Charge> q = pending.get(merchant);
        List<Charge> out = new ArrayList<>();
        while (q != null && !q.isEmpty() && q.peek().availableOn <= ts) out.add(q.poll());
        return out;
    }
}
