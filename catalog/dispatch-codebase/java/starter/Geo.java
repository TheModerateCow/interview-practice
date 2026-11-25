/** Distances and riding times on the street grid. */
final class Geo {
    /** The planning speed of a bike courier, in metres per minute (15 km/h). */
    static final int COURIER_SPEED = 250;

    private Geo() { }

    /** The street distance between two points. The zone is a street grid, so this is the Manhattan distance. */
    static int distance(Point a, Point b) {
        return Math.abs(a.x() - b.x()) + Math.abs(a.y() - b.y());
    }

    /** Converts a street distance into whole minutes of riding. */
    static int travelMinutes(int metres) {
        return metres / COURIER_SPEED;
    }
}
