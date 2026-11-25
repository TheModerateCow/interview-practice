import java.util.ArrayList;
import java.util.List;

public class HiddenTest {
    static final Concession A = Concession.ADULT, C = Concession.CHILD, S = Concession.SENIOR;

    // minutes since Monday 00:00 of week 0; day 0-4 Mon-Fri, 5 Sat, 6 Sun, 7 next Monday
    static int hiddenAt(int day, int h, int m) { return day * 1440 + h * 60 + m; }
    static int hiddenAt(int day, int h) { return hiddenAt(day, h, 0); }

    static List<Integer> hiddenRides(Concession c, int[]... rides) {
        FareCard card = new FareCard(c);
        List<Integer> out = new ArrayList<>();
        for (int[] r : rides) out.add(card.ride(r[0], r[1], r[2]));
        return out;
    }

    static int[] hiddenR(int time, int from, int to) { return new int[] {time, from, to}; }

    static void test_p1_peak_windows() {
        int[] times = {hiddenAt(0, 6, 59), hiddenAt(0, 7), hiddenAt(0, 9, 29), hiddenAt(0, 9, 30),
            hiddenAt(2, 15, 59), hiddenAt(2, 16), hiddenAt(2, 18, 59), hiddenAt(2, 19),
            hiddenAt(4, 8), hiddenAt(5, 8), hiddenAt(6, 17), hiddenAt(7, 8), hiddenAt(12, 17), hiddenAt(14, 7, 30)};
        boolean[] want = {false, true, true, false, false, true, true, false, true, false, false, true, false, true};
        for (int i = 0; i < times.length; i++) Expect.eq(want[i], Fares.isPeak(times[i]));
    }

    static void test_p1_journey_fare_table() {
        Expect.eq(250, Fares.journeyFare(1, false, A));
        Expect.eq(410, Fares.journeyFare(3, false, A));
        Expect.eq(620, Fares.journeyFare(6, false, A));
        Expect.eq(330, Fares.journeyFare(1, true, A));
        Expect.eq(420, Fares.journeyFare(2, true, A));
        Expect.eq(540, Fares.journeyFare(3, true, A));
        Expect.eq(630, Fares.journeyFare(4, true, A));
        Expect.eq(810, Fares.journeyFare(6, true, A));
    }

    static void test_p1_concession_rounding() {
        Expect.eq(125, Fares.journeyFare(1, false, C));
        Expect.eq(165, Fares.journeyFare(1, true, C));
        Expect.eq(270, Fares.journeyFare(3, true, C));
        Expect.eq(275, Fares.journeyFare(5, false, C));
        Expect.eq(175, Fares.journeyFare(1, false, S));
        Expect.eq(230, Fares.journeyFare(1, true, S));
        Expect.eq(290, Fares.journeyFare(2, true, S));
        Expect.eq(335, Fares.journeyFare(4, false, S));
        Expect.eq(565, Fares.journeyFare(6, true, S));
    }

    static void test_p1_single_rides_any_direction() {
        Expect.eq(List.of(480, 480, 620, 250), hiddenRides(A, hiddenR(hiddenAt(0, 11), 5, 2), hiddenR(hiddenAt(1, 14), 2, 5), hiddenR(hiddenAt(2, 20), 6, 1), hiddenR(hiddenAt(3, 12), 3, 3)));
        Expect.eq(List.of(540, 630), hiddenRides(A, hiddenR(hiddenAt(0, 8), 2, 4), hiddenR(hiddenAt(1, 17, 30), 4, 1)));
    }

    static void test_p1_transfer_pays_the_difference() {
        Expect.eq(List.of(250, 160, 70), hiddenRides(A, hiddenR(hiddenAt(1, 10), 2, 2), hiddenR(hiddenAt(1, 10, 30), 2, 4), hiddenR(hiddenAt(1, 11), 1, 3)));
        Expect.eq(List.of(480, 0), hiddenRides(A, hiddenR(hiddenAt(1, 10), 1, 4), hiddenR(hiddenAt(1, 10, 40), 3, 2)));
    }

    static void test_p1_transfer_window_from_journey_start() {
        Expect.eq(List.of(250, 70, 250, 320), hiddenRides(A, hiddenR(hiddenAt(2, 12), 1, 1), hiddenR(hiddenAt(2, 13, 29), 1, 2), hiddenR(hiddenAt(2, 14), 1, 1), hiddenR(hiddenAt(2, 15, 30), 1, 2)));
        Expect.eq(List.of(250, 0, 320), hiddenRides(A, hiddenR(hiddenAt(2, 12), 1, 1), hiddenR(hiddenAt(2, 13), 1, 1), hiddenR(hiddenAt(2, 14), 1, 2)));
        Expect.eq(List.of(250, 160), hiddenRides(A, hiddenR(hiddenAt(0, 23, 50), 1, 1), hiddenR(hiddenAt(1, 0, 30), 1, 3)));
    }

    static void test_p1_at_most_three_rides_per_journey() {
        Expect.eq(List.of(250, 70, 90, 250), hiddenRides(A, hiddenR(hiddenAt(3, 12), 1, 1), hiddenR(hiddenAt(3, 12, 10), 1, 2), hiddenR(hiddenAt(3, 12, 20), 2, 3), hiddenR(hiddenAt(3, 12, 30), 3, 3)));
    }

    static void test_p1_journey_keeps_peak_status_of_first_ride() {
        Expect.eq(List.of(330, 210), hiddenRides(A, hiddenR(hiddenAt(0, 9, 20), 1, 1), hiddenR(hiddenAt(0, 9, 40), 1, 3)));
        Expect.eq(List.of(250, 70), hiddenRides(A, hiddenR(hiddenAt(0, 15, 50), 2, 2), hiddenR(hiddenAt(0, 16, 10), 2, 3)));
        Expect.eq(List.of(330, 90, 210), hiddenRides(A, hiddenR(hiddenAt(4, 18, 50), 1, 1), hiddenR(hiddenAt(4, 19, 10), 1, 2), hiddenR(hiddenAt(4, 19, 40), 1, 4)));
    }

    static void test_p1_concession_transfers() {
        Expect.eq(List.of(210, 150), hiddenRides(C, hiddenR(hiddenAt(0, 8), 1, 2), hiddenR(hiddenAt(0, 8, 30), 2, 5)));
        Expect.eq(List.of(290, 210), hiddenRides(S, hiddenR(hiddenAt(0, 8), 1, 2), hiddenR(hiddenAt(0, 8, 30), 2, 5)));
    }

    static void test_p1_daily_cap() {
        Expect.eq(List.of(810, 390, 0, 0), hiddenRides(A, hiddenR(hiddenAt(0, 8), 1, 6), hiddenR(hiddenAt(0, 12), 1, 3), hiddenR(hiddenAt(0, 17), 1, 1), hiddenR(hiddenAt(0, 21), 1, 1)));
        Expect.eq(List.of(810, 250, 140, 0), hiddenRides(A, hiddenR(hiddenAt(0, 8), 1, 6), hiddenR(hiddenAt(0, 12), 1, 1), hiddenR(hiddenAt(0, 17), 1, 2), hiddenR(hiddenAt(0, 18), 1, 4)));
        Expect.eq(List.of(565, 275), hiddenRides(S, hiddenR(hiddenAt(0, 8), 1, 6), hiddenR(hiddenAt(0, 17), 1, 4)));
    }

    static void test_p1_service_day_starts_at_four() {
        Expect.eq(List.of(810, 390, 0, 250), hiddenRides(A, hiddenR(hiddenAt(0, 8), 1, 6), hiddenR(hiddenAt(0, 17), 1, 4), hiddenR(hiddenAt(1, 2), 1, 1), hiddenR(hiddenAt(1, 4), 1, 1)));
        Expect.eq(List.of(810, 390, 0, 160), hiddenRides(A, hiddenR(hiddenAt(0, 8), 1, 6), hiddenR(hiddenAt(0, 17), 1, 4), hiddenR(hiddenAt(1, 3, 30), 1, 1), hiddenR(hiddenAt(1, 4, 10), 1, 3)));
        Expect.eq(List.of(405, 195, 0, 205), hiddenRides(C, hiddenR(hiddenAt(0, 17), 1, 6), hiddenR(hiddenAt(0, 18, 45), 1, 6), hiddenR(hiddenAt(1, 2, 20), 1, 3), hiddenR(hiddenAt(1, 4, 30), 1, 3)));
    }

    static void test_p1_weekly_cap() {
        FareCard card = new FareCard(A);
        List<Integer> got = new ArrayList<>();
        for (int d = 0; d < 5; d++) { got.add(card.ride(hiddenAt(d, 8), 1, 6)); got.add(card.ride(hiddenAt(d, 17), 1, 6)); }
        got.add(card.ride(hiddenAt(7, 2), 1, 1));
        got.add(card.ride(hiddenAt(7, 4), 1, 1));
        Expect.eq(List.of(810, 390, 810, 390, 810, 390, 810, 390, 0, 0, 0, 250), got);
        FareCard child = new FareCard(C);
        List<Integer> kid = new ArrayList<>();
        for (int d = 0; d < 4; d++) { kid.add(child.ride(hiddenAt(d, 8), 1, 6)); kid.add(child.ride(hiddenAt(d, 17), 1, 6)); }
        kid.add(child.ride(hiddenAt(4, 8), 1, 6));
        Expect.eq(List.of(405, 195, 405, 195, 405, 195, 405, 195, 0), kid);
    }

    static void test_p1_weekend_and_next_week() {
        Expect.eq(List.of(320, 320, 420), hiddenRides(A, hiddenR(hiddenAt(5, 8), 1, 2), hiddenR(hiddenAt(6, 17), 1, 2), hiddenR(hiddenAt(7, 8), 1, 2)));
    }

    static void hiddenRaises(String message, Runnable r) {
        try {
            r.run();
        } catch (IllegalArgumentException e) {
            Expect.eq(message, e.getMessage());
            return;
        }
        throw new AssertionError("expected IllegalArgumentException(\"" + message + "\") but nothing was thrown");
    }

    static void test_p1_errors() {
        hiddenRaises("unknown concession", () -> new FareCard(null));
        FareCard card = new FareCard(A);
        hiddenRaises("invalid zone", () -> card.ride(hiddenAt(0, 10), 0, 2));
        hiddenRaises("invalid zone", () -> card.ride(hiddenAt(0, 10), 2, 7));
        hiddenRaises("invalid time", () -> card.ride(-1, 1, 1));
        hiddenRaises("invalid time", () -> card.ride(-5, 0, 9));
        Expect.eq(250, card.ride(hiddenAt(0, 10), 1, 1));
        Expect.eq(70, card.ride(hiddenAt(0, 10), 1, 2));
        hiddenRaises("invalid time", () -> card.ride(hiddenAt(0, 9, 59), 1, 1));
        hiddenRaises("invalid zone", () -> card.ride(hiddenAt(0, 10, 20), 1, 9));
        Expect.eq(90, card.ride(hiddenAt(0, 10, 30), 1, 3));
    }
}
