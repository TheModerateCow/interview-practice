import java.util.ArrayList;
import java.util.List;

/** Reservation expiry: every reservation in the order it was placed. */
final class Expiry {
    private final List<Reservation> holds = new ArrayList<>();

    /** Registers a newly placed reservation for expiry. */
    void track(Reservation r) {
        holds.add(r);
    }

    /** Ends every active reservation whose hold has run out by now (expiresAt <= now) and returns its stock to available. */
    void expire(long now, Store s) {
        for (Reservation r : holds) {
            if (r.status == Reservation.Status.ACTIVE && r.expiresAt <= now) {
                s.endHold(r, Reservation.Status.EXPIRED, r.expiresAt);
            }
        }
    }
}
