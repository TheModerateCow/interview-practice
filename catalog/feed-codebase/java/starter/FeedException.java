/** Every error the feed service reports. Callers branch on {@link #code}. */
public class FeedException extends RuntimeException {
    public enum Code {
        /** The user id has never been registered. */
        UNKNOWN_USER,
        /** The post id does not exist. */
        UNKNOWN_POST,
        /** A post with this id was already published. */
        DUPLICATE_POST,
        /** The pagination cursor was not produced by this service. */
        BAD_CURSOR,
        /** A page or carousel size below 1. */
        BAD_LIMIT,
        /** A user tried to follow themselves. */
        SELF_FOLLOW
    }

    public final Code code;

    public FeedException(Code code, String message) {
        super(message);
        this.code = code;
    }
}
