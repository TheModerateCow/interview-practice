/** Moves {@code amount} minor units of {@code currency} into (positive) or out of (negative) {@code account}. */
public record Posting(String account, String currency, long amount) {}
