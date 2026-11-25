/** Local-time arithmetic. */
final class Clock {
    private Clock() {}

    static final long DAY_SECONDS = 24 * 60 * 60;

    /** The hour (0-23) on the user's wall clock at UTC time {@code at}. */
    static int localHour(long at, int offsetMin) {
        long wall = at + offsetMin * 60L;
        return (int) (Math.floorMod(wall, DAY_SECONDS) / 3600);
    }

    /** Whether {@code at} falls in the user's quiet hours. A range like 22 -> 7 wraps past midnight. */
    static boolean inQuietHours(User u, long at) {
        if (u.quietFrom == u.quietTo) return false;
        int h = localHour(at, u.offsetMin);
        if (u.quietFrom < u.quietTo) {
            return u.quietFrom <= h && h < u.quietTo;
        }
        return h >= u.quietFrom || h < u.quietTo;
    }

    /** The UTC time at which the user's local day containing {@code at} began. */
    static long localMidnight(long at, int offsetMin) {
        long shift = offsetMin * 60L;
        return at - Math.floorMod(at + shift, DAY_SECONDS);
    }
}
