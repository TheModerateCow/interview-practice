import java.util.ArrayList;
import java.util.List;

/** Runs dispatch for one delivery zone. */
public class Dispatcher {
    /** The furthest, in metres, a courier may be from the restaurant to be offered an order. */
    public static final int MAX_PICKUP_DISTANCE = 4000;

    final Store store = new Store();

    /** Puts a courier on shift at a location. */
    public void addCourier(String id, Point at, int capacity) {
        if (capacity < 1) {
            throw new DispatchException(DispatchException.Code.INVALID_COURIER, "courier capacity must be at least 1");
        }
        store.addCourier(new Courier(id, at, capacity));
    }

    /** Records a new order, waiting for a courier. */
    public void placeOrder(String id, Point restaurant, Point customer, int placedAt, int prepMinutes) {
        store.addOrder(new Order(id, restaurant, customer, placedAt, prepMinutes));
    }

    /** A copy of an order. */
    public Order order(String id) {
        return store.order(id).copy();
    }

    /** Hands a waiting order to the nearest courier with room, right away; returns the courier's id. */
    public String assign(String orderId) {
        Order o = store.order(orderId);
        if (o.state != State.PLACED) {
            throw new DispatchException(DispatchException.Code.BAD_TRANSITION, "order cannot move to that state");
        }
        Courier c = nearestCourier(o.restaurant);
        if (c == null) throw new DispatchException(DispatchException.Code.NO_COURIER, "no courier available");
        assignTo(o, c);
        return c.id;
    }

    /**
     * Moves an order along its lifecycle: PICKED_UP, DELIVERED or CANCELLED. Orders become assigned
     * only through {@link #assign} or {@link #dispatchPending}.
     */
    public void advance(String orderId, State to) {
        Order o = store.order(orderId);
        if (to == State.ASSIGNED || !o.state.canMoveTo(to)) {
            throw new DispatchException(DispatchException.Code.BAD_TRANSITION, "order cannot move to that state");
        }
        o.state = to;
        if (o.courierId.isEmpty()) return;
        Courier c = store.courier(o.courierId);
        switch (to) {
            case PICKED_UP -> c.location = o.restaurant;
            case DELIVERED -> c.location = o.customer;
            default -> { }
        }
        if (to.terminal()) c.active--;
    }

    /** The ids of the unfinished orders a courier holds. */
    public List<String> courierOrders(String courierId) {
        store.courier(courierId);
        List<String> ids = new ArrayList<>();
        for (Order o : store.activeOrdersOf(courierId)) ids.add(o.id);
        return ids;
    }

    public int eta(String orderId, int now) {
        return Eta.eta(store, orderId, now);
    }

    public List<Assignment> dispatchPending(int now) {
        return Batch.dispatchPending(this, now);
    }

    /**
     * The courier closest to a restaurant who has room for another order and is within
     * MAX_PICKUP_DISTANCE. Ties go to the lower id.
     */
    Courier nearestCourier(Point restaurant) {
        Courier best = null;
        int bestDist = 0;
        for (Courier c : store.couriers()) {
            if (store.activeOrdersOf(c.id).size() >= c.capacity) continue;
            int dist = Geo.distance(c.location, restaurant);
            if (dist > MAX_PICKUP_DISTANCE) continue;
            if (best == null || dist < bestDist || (dist == bestDist && c.id.compareTo(best.id) < 0)) {
                best = c;
                bestDist = dist;
            }
        }
        return best;
    }

    void assignTo(Order o, Courier c) {
        o.state = State.ASSIGNED;
        o.courierId = c.id;
        c.active++;
    }
}
