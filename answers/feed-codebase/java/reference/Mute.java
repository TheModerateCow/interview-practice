/** A viewer's mute of one account. {@code until} is null for a permanent mute. */
public record Mute(String target, Long until) {
    /** A mute set at {@code now} lasting {@code hours} hours (forever if null). */
    static Mute starting(String target, long now, Double hours) {
        if (hours == null) return new Mute(target, null);
        return new Mute(target, now + Math.round(hours * 60 * 60));
    }

    boolean active(long now) {
        return until == null || now < until;
    }
}
