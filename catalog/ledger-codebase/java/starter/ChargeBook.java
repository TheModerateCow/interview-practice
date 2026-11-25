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
    private final Map<String, List<String>> pending = new HashMap<>();

    void add(Charge c) {
        c.seq = byId.size();
        byId.put(c.id, c);
        pending.computeIfAbsent(c.merchant, k -> new ArrayList<>()).add(c.id);
    }

    Charge get(String chargeId) {
        return byId.get(chargeId);
    }

    /**
     * The merchant's unsettled charges whose funds are available at ts, earliest availableOn first
     * (capture order breaks ties). A charge counts as settled once its batch is set.
     */
    List<Charge> due(String merchant, long ts) {
        List<Charge> out = new ArrayList<>();
        for (String id : pending.getOrDefault(merchant, List.of())) {
            Charge c = byId.get(id);
            if (c.batch.isEmpty() && c.availableOn <= ts) out.add(c);
        }
        out.sort(ORDER);
        return out;
    }
}
