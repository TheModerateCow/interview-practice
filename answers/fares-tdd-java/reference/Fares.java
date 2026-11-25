public final class Fares {
    static final int DAY = 1440;
    private static final int[] BASE = {250, 320, 410, 480, 550, 620}; // by number of zones, 1..6

    private Fares() {}

    /** True when a ride at {@code time} (minutes since Monday 00:00 of week 0) is in a peak window. */
    public static boolean isPeak(int time) {
        boolean weekday = (time / DAY) % 7 <= 4;
        int m = time % DAY;
        return weekday && ((m >= 420 && m < 570) || (m >= 960 && m < 1140));
    }

    /** Fare in cents for a journey covering {@code zones} zones (1-6), after the peak uplift and the concession discount. */
    public static int journeyFare(int zones, boolean peak, Concession c) {
        int fare = BASE[zones - 1];
        if (peak) fare = (fare * 130 + 999) / 1000 * 10;
        return fare * c.payPercent / 500 * 5;
    }
}
