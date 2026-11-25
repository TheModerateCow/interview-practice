import java.util.Map;

/**
 * What the platform charges a merchant on each settled charge: {@code bps} basis points of the captured
 * amount, rounded half up to a whole minor unit, plus a fixed fee per currency in that currency's minor units.
 */
public record Pricing(long bps, Map<String, Long> fixed) {
    public Pricing(long bps) {
        this(bps, Map.of());
    }

    /** The platform fee on one charge of amount minor units in cur. */
    public long fee(long amount, String cur) {
        return Math.floorDiv(amount * bps + 5000, 10000) + fixed.getOrDefault(cur, 0L);
    }
}
