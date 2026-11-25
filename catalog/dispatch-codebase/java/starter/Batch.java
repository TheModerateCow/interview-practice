import java.util.List;

/** The dispatch loop's tick. */
final class Batch {
    /** How many minutes before its food is ready an order may be handed to a courier by dispatchPending. */
    static final int DISPATCH_WINDOW = 10;

    private Batch() { }

    /** Hands out the waiting orders that are due at minute now. See problem.md for the rules. */
    static List<Assignment> dispatchPending(Dispatcher d, int now) {
        throw new UnsupportedOperationException("not implemented");
    }
}
