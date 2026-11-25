/**
 * One customer order from one restaurant. The dispatcher owns these objects; callers only ever
 * see copies (see {@link Dispatcher#order}).
 */
public final class Order {
    final String id;
    final Point restaurant;
    final Point customer;
    final int placedAt;      // minute of the shift the order was placed
    final int prepMinutes;   // kitchen's estimate until the food is ready

    State state = State.PLACED;
    String courierId = "";   // set once assigned

    Order(String id, Point restaurant, Point customer, int placedAt, int prepMinutes) {
        this.id = id;
        this.restaurant = restaurant;
        this.customer = customer;
        this.placedAt = placedAt;
        this.prepMinutes = prepMinutes;
    }

    public String id() { return id; }
    public Point restaurant() { return restaurant; }
    public Point customer() { return customer; }
    public int placedAt() { return placedAt; }
    public int prepMinutes() { return prepMinutes; }
    public State state() { return state; }
    public String courierId() { return courierId; }

    /** The minute of the shift the kitchen expects the food to be ready. */
    public int readyAt() {
        return placedAt + prepMinutes;
    }

    Order copy() {
        Order c = new Order(id, restaurant, customer, placedAt, prepMinutes);
        c.state = state;
        c.courierId = courierId;
        return c;
    }
}
