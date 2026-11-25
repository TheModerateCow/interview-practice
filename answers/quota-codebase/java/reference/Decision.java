/**
 * The limiter's answer to one request.
 *
 * @param remaining  units left in the current window after this request
 * @param retryAfter seconds until the window resets; 0 when allowed
 */
public record Decision(boolean allowed, long remaining, long retryAfter) {
    public Decision(boolean allowed, long remaining) {
        this(allowed, remaining, 0);
    }
}
