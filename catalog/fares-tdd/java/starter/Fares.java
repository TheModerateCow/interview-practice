public final class Fares {
    private Fares() {}

    /** True when a ride at {@code time} (minutes since Monday 00:00 of week 0) is in a peak window. */
    public static boolean isPeak(int time) {
        throw new UnsupportedOperationException("not implemented");
    }

    /** Fare in cents for a journey covering {@code zones} zones (1-6), after the peak uplift and the concession discount; concession is "adult", "child" or "senior". */
    public static int journeyFare(int zones, boolean peak, String concession) {
        throw new UnsupportedOperationException("not implemented");
    }
}
