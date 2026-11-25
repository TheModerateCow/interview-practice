import java.util.HashMap;
import java.util.Map;

/** One rider's travel card. Rides arrive in time order. */
public class FareCard {
    private static final int TRANSFER_WINDOW = 90;
    private static final int MAX_RIDES = 3;

    private final Concession concession;
    private int lastTime = -1;
    private int rides; // rides in the current journey; 0 = no journey yet
    private int start, lo, hi;
    private boolean peak;
    private final Map<Integer, Integer> spentByDay = new HashMap<>();
    private final Map<Integer, Integer> spentByWeek = new HashMap<>();

    public FareCard(Concession concession) {
        if (concession == null) throw new IllegalArgumentException("unknown concession");
        this.concession = concession;
    }

    /** Records a ride and returns the cents charged for it. */
    public int ride(int time, int fromZone, int toZone) {
        if (time < 0 || time < lastTime) throw new IllegalArgumentException("invalid time");
        if (fromZone < 1 || fromZone > 6 || toZone < 1 || toZone > 6) throw new IllegalArgumentException("invalid zone");
        lastTime = time;

        int rideLo = Math.min(fromZone, toZone), rideHi = Math.max(fromZone, toZone);
        int before = 0;
        if (rides > 0 && time - start < TRANSFER_WINDOW && rides < MAX_RIDES) {
            before = Fares.journeyFare(hi - lo + 1, peak, concession);
            lo = Math.min(lo, rideLo);
            hi = Math.max(hi, rideHi);
            rides++;
        } else {
            start = time;
            peak = Fares.isPeak(time);
            lo = rideLo;
            hi = rideHi;
            rides = 1;
        }
        int due = Fares.journeyFare(hi - lo + 1, peak, concession) - before;

        int day = Math.floorDiv(time - 240, Fares.DAY), week = Math.floorDiv(day, 7);
        int today = spentByDay.getOrDefault(day, 0), thisWeek = spentByWeek.getOrDefault(week, 0);
        int charge = Math.max(0, Math.min(due, Math.min(concession.dailyCap - today, concession.weeklyCap - thisWeek)));
        spentByDay.put(day, today + charge);
        spentByWeek.put(week, thisWeek + charge);
        return charge;
    }
}
