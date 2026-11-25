/** A pricing tier's rate limit: {@code limit} units per fixed window of {@code window} seconds, plus up to
 *  {@code burst} units the key left unused in the window before. */
public record Plan(String name, long limit, long window, long burst) {
    public Plan(String name, long limit, long window) {
        this(name, limit, window, 0);
    }
}
