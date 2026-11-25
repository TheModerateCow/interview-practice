import java.util.List;

final class Replenish {
    private Replenish() {}

    /**
     * One Suggestion for each SKU with a Rule in the warehouse whose stock position has fallen to the
     * rule's min, sorted by SKU. It only plans; nothing is moved or ordered. See problem.md for the full rules.
     */
    static List<Suggestion> plan(Inventory s, String warehouse, long now) {
        throw new UnsupportedOperationException("not implemented");
    }
}
