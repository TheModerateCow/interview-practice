import java.util.ArrayList;
import java.util.List;

public class Account {
    private static final int SILVER_FROM = 50_000; // lifetime spend in cents
    private static final int GOLD_FROM = 200_000;
    private static final int CAP_PER_BUY = 500; // points
    private static final int LIFETIME_DAYS = 365;

    private static final class Lot {
        final int day;
        int points;
        Lot(int day, int points) { this.day = day; this.points = points; }
    }

    private int spent; // lifetime spend in cents
    private final List<Lot> lots = new ArrayList<>(); // oldest first, minus what was redeemed

    public Account() {}

    public String tier() { return tierOf(spent); }

    private static String tierOf(int spent) {
        if (spent >= GOLD_FROM) return "gold";
        if (spent >= SILVER_FROM) return "silver";
        return "base";
    }

    private static int rate(int spent) {
        switch (tierOf(spent)) {
            case "gold": return 150;
            case "silver": return 125;
            default: return 100;
        }
    }

    public int earn(int day, int spendCents) {
        if (spendCents <= 0) throw new InvalidAmountException("amount must be positive");
        int pts = (spendCents * rate(spent) + 5_000) / 10_000;
        pts = Math.min(pts, CAP_PER_BUY);
        spent += spendCents;
        if (pts > 0) lots.add(new Lot(day, pts));
        return pts;
    }

    private static boolean usable(Lot l, int day) { return day < l.day + LIFETIME_DAYS; }

    public int balance(int day) {
        int n = 0;
        for (Lot l : lots) if (usable(l, day)) n += l.points;
        return n;
    }

    public void redeem(int day, int points) {
        if (points <= 0) throw new InvalidAmountException("amount must be positive");
        if (points > balance(day)) throw new InsufficientPointsException("not enough points");
        for (Lot l : lots) {
            if (points == 0) break;
            if (!usable(l, day)) continue;
            int take = Math.min(points, l.points);
            l.points -= take;
            points -= take;
        }
    }
}
