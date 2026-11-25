/** The tracking page's arrival estimate. */
final class Eta {
    private Eta() { }

    /**
     * How many minutes from now the order should reach the customer.
     *
     * An assigned order: the courier rides to the restaurant, waits there if the food is not ready
     * yet (see {@link Order#readyAt}), then rides to the customer. A picked-up order: the courier
     * rides from where they are to the customer. Each leg's riding time counts in whole minutes,
     * rounded up.
     */
    static int eta(Store store, String orderId, int now) {
        Order o = store.order(orderId);
        switch (o.state) {
            case PLACED -> throw new DispatchException(DispatchException.Code.NOT_ASSIGNED, "order has no courier yet");
            case DELIVERED, CANCELLED -> throw new DispatchException(DispatchException.Code.ORDER_CLOSED, "order is already finished");
            default -> { }
        }
        Courier c = store.courier(o.courierId);
        if (o.state == State.PICKED_UP) {
            return Geo.travelMinutes(Geo.distance(c.location, o.customer));
        }
        int pickup = Math.max(now + Geo.travelMinutes(Geo.distance(c.location, o.restaurant)), o.readyAt());
        return pickup + Geo.travelMinutes(Geo.distance(o.restaurant, o.customer)) - now;
    }
}
