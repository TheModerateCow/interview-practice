import java.util.Map;

public class Subscription {
    private static final int MAX_SEATS = 500;
    // Per-seat price of one period, in cents.
    private static final Map<String, Map<String, Integer>> PRICES = Map.of(
        "monthly", Map.of("starter", 1_299, "team", 2_499, "business", 5_999),
        "annual", Map.of("starter", 12_990, "team", 24_990, "business", 59_990));
    private static final Map<String, Integer> CYCLE_DAYS = Map.of("monthly", 30, "annual", 360);

    private String cycle, plan;
    private int seats, start, end, credit;

    public Subscription() {}

    public void start(int day, String plan, String cycle, int seats) {
        Integer days = CYCLE_DAYS.get(cycle);
        if (days == null) throw new UnknownCycleException();
        check(cycle, plan, seats);
        this.cycle = cycle;
        this.plan = plan;
        this.seats = seats;
        this.start = day;
        this.end = day + days;
        this.credit = 0;
    }

    private static void check(String cycle, String plan, int seats) {
        if (!PRICES.get(cycle).containsKey(plan)) throw new UnknownPlanException();
        if (seats < 1 || seats > MAX_SEATS) throw new InvalidSeatsException();
    }

    public int periodPrice() {
        return PRICES.get(cycle).get(plan) * seats;
    }

    public int periodEnd() { return end; }

    public int credit() { return credit; }

    // Applies credit to a charge and returns what is left to charge.
    private int pay(int amount) {
        int used = Math.min(amount, credit);
        credit -= used;
        return amount - used;
    }

    public int change(int day, String plan, int seats) {
        if (day < start || day >= end) throw new OutsidePeriodException();
        check(cycle, plan, seats);
        int old = periodPrice();
        this.plan = plan;
        this.seats = seats;
        int diff = periodPrice() - old, left = end - day, length = end - start;
        if (diff > 0) return pay((diff * left + length / 2) / length);
        credit += (-diff) * left / length;
        return 0;
    }

    public int renew() {
        int length = end - start;
        start = end;
        end += length;
        return pay(periodPrice());
    }
}
