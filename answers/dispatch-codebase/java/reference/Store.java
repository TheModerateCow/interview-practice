import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Holds orders and couriers in memory. */
final class Store {
    private final Map<String, Order> orders = new HashMap<>();
    private final Map<String, Courier> couriers = new HashMap<>();
    private final List<Courier> roster = new ArrayList<>();  // couriers in the order they joined the shift

    void addOrder(Order o) {
        if (orders.containsKey(o.id)) {
            throw new DispatchException(DispatchException.Code.DUPLICATE_ORDER, "order already exists");
        }
        orders.put(o.id, o);
    }

    void addCourier(Courier c) {
        if (couriers.containsKey(c.id)) {
            throw new DispatchException(DispatchException.Code.DUPLICATE_COURIER, "courier already exists");
        }
        couriers.put(c.id, c);
        roster.add(c);
    }

    Order order(String id) {
        Order o = orders.get(id);
        if (o == null) throw new DispatchException(DispatchException.Code.UNKNOWN_ORDER, "unknown order");
        return o;
    }

    Courier courier(String id) {
        Courier c = couriers.get(id);
        if (c == null) throw new DispatchException(DispatchException.Code.UNKNOWN_COURIER, "unknown courier");
        return c;
    }

    /** Every courier on shift, in the order they joined. */
    List<Courier> couriers() {
        return new ArrayList<>(roster);
    }

    /** The orders still waiting for a courier, oldest first; orders placed in the same minute are sorted by id. */
    List<Order> pendingOrders() {
        List<Order> out = new ArrayList<>();
        for (Order o : orders.values()) {
            if (o.state == State.PLACED) out.add(o);
        }
        out.sort(Comparator.comparingInt((Order o) -> o.placedAt).thenComparing(o -> o.id));
        return out;
    }

    /** The unfinished orders assigned to a courier, sorted by id. */
    List<Order> activeOrdersOf(String courierId) {
        List<Order> out = new ArrayList<>();
        for (Order o : orders.values()) {
            if (o.courierId.equals(courierId) && !o.state.terminal()) out.add(o);
        }
        out.sort(Comparator.comparing((Order o) -> o.id));
        return out;
    }
}
