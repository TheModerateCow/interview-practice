/**
 * One message a product team wants a user to get.
 *
 * @param topic  e.g. "billing", "security"
 * @param key    dedupe key chosen by the sender
 * @param at     seconds since the epoch, UTC
 * @param urgent ignores quiet hours (but not caps)
 */
public record Notification(String user, String topic, String key, String title, long at, boolean urgent) {
    public Notification(String user, String topic, String key, String title, long at) {
        this(user, topic, key, title, at, false);
    }
}
