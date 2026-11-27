import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/** Fleet desk for a car-rental company: cars by class and branch, rentals with daily rates and late fees, one-way drop-offs, and reservations made ahead of time. Every method takes ts first: the time of the call in hours. */
public class RentalDesk {
    private static final Map<String, Integer> RATES = Map.of("economy", 3000, "compact", 4500, "suv", 7000); // cents per day
    private static final int DROP_FEE = 5000;
    private static final int DAY = 24; // hours

    /** Whole days started: 1 to 24 hours is 1 day, 25 is 2. */
    private static int daysStarted(int hours) { return (hours + DAY - 1) / DAY; }

    private record Rental(String customer, int start, int due) {}

    private static final class Car {
        final String carClass;
        String branch;
        Rental out;
        Car(String carClass, String branch) { this.carClass = carClass; this.branch = branch; }
    }

    private static final class Reservation {
        final String customer, branch, carClass;
        final int start, end;
        boolean used;
        Reservation(String customer, String branch, String carClass, int start, int end) {
            this.customer = customer; this.branch = branch; this.carClass = carClass; this.start = start; this.end = end;
        }
    }

    private final Map<String, Car> cars = new HashMap<>();
    private final Set<String> branches = new HashSet<>();
    private final Map<String, Integer> paid = new HashMap<>();
    private final Map<String, Reservation> reservations = new HashMap<>();
    private int nextRes;

    public RentalDesk() {}

    /** Ids of the cars of carClass parked at branch, lowest first. */
    private List<String> free(String branch, String carClass) {
        List<String> ids = new ArrayList<>();
        for (var e : cars.entrySet()) {
            Car c = e.getValue();
            if (c.out == null && c.branch.equals(branch) && c.carClass.equals(carClass)) ids.add(e.getKey());
        }
        ids.sort(null);
        return ids;
    }

    private boolean hasCar(String customer) {
        for (Car c : cars.values()) if (c.out != null && c.out.customer().equals(customer)) return true;
        return false;
    }

    /** Reservations not yet picked up that overlap [start, end); start >= ts, so a lapsed one never does. */
    private int pending(String branch, String carClass, int start, int end) {
        int n = 0;
        for (Reservation r : reservations.values())
            if (!r.used && r.branch.equals(branch) && r.carClass.equals(carClass) && r.start < end && start < r.end) n++;
        return n;
    }

    // ---------------------------------------------------------------- level 1

    public boolean addCar(int ts, String carId, String carClass, String branch) {
        if (cars.containsKey(carId) || !RATES.containsKey(carClass)) return false;
        cars.put(carId, new Car(carClass, branch));
        branches.add(branch);
        return true;
    }

    public String rent(int ts, String customer, String branch, String carClass, int days) {
        if (!RATES.containsKey(carClass) || days <= 0 || hasCar(customer)) return "";
        int due = ts + DAY * days;
        List<String> free = free(branch, carClass);
        if (free.size() <= pending(branch, carClass, ts, due)) return "";
        cars.get(free.get(0)).out = new Rental(customer, ts, due);
        return free.get(0);
    }

    public boolean returnCar(int ts, String carId) {
        Car c = cars.get(carId);
        if (c == null || c.out == null) return false;
        return dropOff(ts, carId, c.branch);
    }

    public String status(int ts, String carId) {
        Car c = cars.get(carId);
        if (c == null) return "";
        if (c.out != null) return "rented:" + c.out.customer();
        return "available:" + c.branch;
    }

    // ---------------------------------------------------------------- level 2

    public int charges(int ts, String customer) {
        return paid.getOrDefault(customer, 0);
    }

    public List<String> overdue(int ts) {
        List<String> ids = new ArrayList<>();
        for (var e : cars.entrySet()) if (e.getValue().out != null && e.getValue().out.due() < ts) ids.add(e.getKey());
        ids.sort((a, b) -> {
            int c = Integer.compare(cars.get(a).out.due(), cars.get(b).out.due());
            return c != 0 ? c : a.compareTo(b);
        });
        List<String> out = new ArrayList<>();
        for (String id : ids) out.add(id + "(" + cars.get(id).out.customer() + ")");
        return out;
    }

    // ---------------------------------------------------------------- level 3

    public boolean dropOff(int ts, String carId, String branch) {
        Car c = cars.get(carId);
        if (c == null || c.out == null || !branches.contains(branch)) return false;
        Rental out = c.out;
        int n = Math.max(1, daysStarted(ts - out.start())) + daysStarted(Math.max(0, ts - out.due()));
        int fee = n * RATES.get(c.carClass) + (branch.equals(c.branch) ? 0 : DROP_FEE);
        paid.merge(out.customer(), fee, Integer::sum);
        c.branch = branch;
        c.out = null;
        return true;
    }

    public List<String> available(int ts, String branch) {
        Map<String, Integer> counts = new TreeMap<>();
        for (Car c : cars.values()) if (c.out == null && c.branch.equals(branch)) counts.merge(c.carClass, 1, Integer::sum);
        List<String> out = new ArrayList<>();
        for (var e : counts.entrySet()) out.add(e.getKey() + "(" + e.getValue() + ")");
        return out;
    }

    // ---------------------------------------------------------------- level 4

    public String reserve(int ts, String customer, String branch, String carClass, int start, int days) {
        if (!RATES.containsKey(carClass) || days <= 0 || start < ts) return "";
        int end = start + DAY * days;
        int fleet = 0;
        for (Car c : cars.values()) if (c.branch.equals(branch) && c.carClass.equals(carClass)) fleet++;
        if (pending(branch, carClass, start, end) >= fleet) return "";
        String id = "r" + (++nextRes);
        reservations.put(id, new Reservation(customer, branch, carClass, start, end));
        return id;
    }

    public String pickUp(int ts, String reservationId) {
        Reservation r = reservations.get(reservationId);
        if (r == null || r.used || ts < r.start || ts >= r.end || hasCar(r.customer)) return "";
        List<String> free = free(r.branch, r.carClass);
        if (free.isEmpty()) return "";
        r.used = true;
        cars.get(free.get(0)).out = new Rental(r.customer, ts, r.end);
        return free.get(0);
    }
}
