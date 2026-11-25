/** A warehouse's replenishment rule for one SKU: when its stock position falls to {@code min} or below, restock up to {@code max}, ordering in multiples of {@code pack} (0 or 1: single units). */
public record Rule(int min, int max, int pack) {}
