import java.util.EnumSet;
import java.util.Set;

/** Where an order is in its lifecycle. */
public enum State {
    PLACED("placed"),        // waiting for a courier
    ASSIGNED("assigned"),    // a courier is riding to the restaurant
    PICKED_UP("picked_up"),  // the courier has the food
    DELIVERED("delivered"),  // handed to the customer
    CANCELLED("cancelled");  // cancelled by the customer or support

    private final String label;

    State(String label) {
        this.label = label;
    }

    @Override
    public String toString() {
        return label;
    }

    /** Turns a name such as "picked_up" back into a State; null if there is none. */
    public static State parse(String name) {
        for (State s : values()) {
            if (s.label.equals(name)) return s;
        }
        return null;
    }

    /** The states this state may move to. */
    private Set<State> next() {
        return switch (this) {
            case PLACED -> EnumSet.of(ASSIGNED, CANCELLED);
            case ASSIGNED -> EnumSet.of(PICKED_UP, CANCELLED);
            case PICKED_UP -> EnumSet.of(DELIVERED);
            default -> EnumSet.noneOf(State.class);
        };
    }

    public boolean canMoveTo(State next) {
        return next().contains(next);
    }

    /** Whether the order is finished: the courier no longer carries it. */
    public boolean terminal() {
        return this == DELIVERED;
    }
}
