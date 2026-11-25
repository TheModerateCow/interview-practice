import java.util.Map;

/** Constants shared by the notification fan-out. */
public final class Notify {
    private Notify() {}

    public static final String EMAIL = "email";
    public static final String PUSH = "push";
    public static final String SMS = "sms";

    public static final String SENT = "sent"; // delivered on at least one channel
    public static final String HELD = "held"; // kept for the user's daily digest
    public static final String DUPLICATE = "duplicate"; // dropped: same key within DEDUPE_WINDOW

    /** How long, in seconds, a dedupe key blocks a repeat notification to the same user. */
    public static final long DEDUPE_WINDOW = 3600;

    /** The rolling span, in seconds, that HOURLY_CAP counts over. */
    public static final long CAP_WINDOW = 3600;

    /** The most deliveries a user may get on a channel in any CAP_WINDOW seconds. */
    public static final Map<String, Integer> HOURLY_CAP = Map.of(EMAIL, 6, PUSH, 4, SMS, 2);
}
