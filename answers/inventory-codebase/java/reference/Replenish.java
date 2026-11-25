import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

final class Replenish {
    private Replenish() {}

    /**
     * One Suggestion for each SKU with a Rule in the warehouse whose stock position has fallen to the
     * rule's min, sorted by SKU. It only plans; nothing is moved or ordered. See problem.md for the full rules.
     */
    static List<Suggestion> plan(Inventory s, String warehouse, long now) {
        s.checkWarehouse(warehouse);
        s.advance(now);
        List<String> skus = new ArrayList<>();
        for (StockKey k : s.store.rules.keySet()) {
            if (k.warehouse().equals(warehouse)) skus.add(k.sku());
        }
        Collections.sort(skus);
        List<Suggestion> out = new ArrayList<>();
        for (String sku : skus) {
            StockKey k = new StockKey(warehouse, sku);
            Rule rule = s.store.rules.get(k);
            int pos = s.avail(k) + s.store.inbound(k);
            if (pos > rule.min()) continue;
            int qty = rule.max() - pos;
            if (rule.pack() > 1) {
                qty = (qty + rule.pack() - 1) / rule.pack() * rule.pack();
            }
            out.add(new Suggestion(sku, pos, qty, source(s, warehouse, sku, qty)));
        }
        return out;
    }

    /**
     * The other warehouse that can best spare qty units of sku: the largest surplus (available minus its
     * own rule's min) that covers qty, lowest ID on a tie.
     */
    private static String source(Inventory s, String dest, String sku, int qty) {
        String best = "";
        int bestSurplus = 0;
        for (String w : s.warehouseIds()) {
            if (w.equals(dest)) continue;
            StockKey k = new StockKey(w, sku);
            Rule rule = s.store.rules.get(k);
            int surplus = s.avail(k) - (rule == null ? 0 : rule.min());
            if (surplus >= qty && (best.isEmpty() || surplus > bestSurplus)) {
                best = w;
                bestSurplus = surplus;
            }
        }
        return best;
    }
}
