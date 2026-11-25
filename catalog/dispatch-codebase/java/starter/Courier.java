/** A rider on shift. */
final class Courier {
    final String id;
    Point location;
    final int capacity;  // most orders carried at once
    int active;          // orders currently assigned to or carried by the courier

    Courier(String id, Point location, int capacity) {
        this.id = id;
        this.location = location;
        this.capacity = capacity;
    }
}
