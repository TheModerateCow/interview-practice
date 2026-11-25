import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** The dispatch loop's tick. */
final class Batch {
    /** How many minutes before its food is ready an order may be handed to a courier by dispatchPending. */
    static final int DISPATCH_WINDOW = 10;

    private Batch() { }

    /** Hands out the waiting orders that are due at minute now. See problem.md for the rules. */
    static List<Assignment> dispatchPending(Dispatcher d, int now) {
        List<Order> due = new ArrayList<>();
        for (Order o : d.store.pendingOrders()) {
            if (o.readyAt() - now <= DISPATCH_WINDOW) due.add(o);
        }
        due.sort(Comparator.comparingInt((Order o) -> o.readyAt()).thenComparing(o -> o.id));
        List<Assignment> out = new ArrayList<>();
        for (Order o : due) {
            Courier c = d.nearestCourier(o.restaurant);
            if (c != null) {
                d.assignTo(o, c);
                out.add(new Assignment(o.id, c.id));
            }
        }
        return out;
    }
}
