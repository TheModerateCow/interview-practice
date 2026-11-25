import java.util.Comparator;
import java.util.PriorityQueue;

/**
 * Reservation expiry: a min-heap of reservations ordered by when their hold runs out, then by
 * placement order. Released and committed holds stay in it until their time comes.
 */
final class Expiry {
    private final PriorityQueue<Reservation> holds =
            new PriorityQueue<>(Comparator.comparingLong((Reservation r) -> r.expiresAt).thenComparingInt(r -> r.seq));

    /** Registers a newly placed reservation for expiry. */
    void track(Reservation r) {
        holds.add(r);
    }

    /** Ends every active reservation whose hold has run out by now (expiresAt <= now) and returns its stock to available. */
    void expire(long now, Store s) {
        while (!holds.isEmpty() && holds.peek().expiresAt <= now) {
            Reservation r = holds.poll();
            if (r.status == Reservation.Status.ACTIVE) {
                s.endHold(r, Reservation.Status.EXPIRED, r.expiresAt);
            }
        }
    }
}
