/** Every error the notification service reports. Callers branch on {@link #code}. */
public class NotifyException extends RuntimeException {
    public enum Code {
        UNKNOWN_USER,
        DUPLICATE_USER,
        /** Channels must be email, push or sms, each at most once. */
        BAD_CHANNEL,
        /** Quiet hours must be between 0 and 23. */
        BAD_QUIET_HOURS,
        /** UTC offset must be between -720 and 840 minutes. */
        BAD_OFFSET,
        /** A notification needs a topic and a dedupe key. */
        BAD_NOTIFICATION
    }

    public final Code code;

    public NotifyException(Code code, String message) {
        super(code + ": " + message);
        this.code = code;
    }
}
