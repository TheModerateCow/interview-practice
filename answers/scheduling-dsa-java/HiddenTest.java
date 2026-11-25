import java.util.ArrayList;
import java.util.List;

public class HiddenTest {
    static Attendee hiddenAt(int offset, int workStart, int workEnd, int[]... busy) {
        return new Attendee(offset, workStart, workEnd, busy);
    }

    static int hiddenF(int days, int duration, int quorum, Attendee... team) {
        return Scheduler.earliestQuorumSlot(List.of(team), days, duration, quorum);
    }

    static void test_p1_worked_example() {
        Expect.eq(630, hiddenF(1, 60, 2,
                hiddenAt(0, 540, 1020, new int[]{540, 610}, new int[]{660, 720}),
                hiddenAt(60, 540, 1020, new int[]{500, 630}),
                hiddenAt(-120, 480, 720)));
    }

    static void test_p1_east_of_utc_starts_earlier() {
        Expect.eq(210, hiddenF(1, 45, 1, hiddenAt(330, 540, 1020)));
    }

    static void test_p1_west_of_utc_previous_local_day() {
        // local day -1 shows up as UTC [0, 360); busy leaves only 30 minutes of it
        Expect.eq(1080, hiddenF(1, 60, 1, hiddenAt(-600, 480, 1200, new int[]{0, 330})));
    }

    static void test_p1_same_people_for_whole_meeting() {
        Attendee[] three = {
            hiddenAt(0, 0, 1440, new int[]{60, 1440}),
            hiddenAt(0, 0, 1440, new int[]{0, 30}, new int[]{90, 1440}),
            hiddenAt(0, 0, 1440, new int[]{0, 60}, new int[]{120, 1440}),
        };
        Expect.eq(-1, hiddenF(1, 60, 2, three));
        Expect.eq(0, hiddenF(1, 60, 1, three));
    }

    static void test_p1_exact_fit() {
        Expect.eq(600, hiddenF(1, 60, 1, hiddenAt(0, 600, 660)));
        Expect.eq(-1, hiddenF(1, 61, 1, hiddenAt(0, 600, 660)));
    }

    static void test_p1_unsorted_nested_busy_blocks() {
        Expect.eq(800, hiddenF(1, 60, 1,
                hiddenAt(0, 540, 1020, new int[]{700, 720}, new int[]{550, 560}, new int[]{540, 800})));
    }

    static void test_p1_busy_block_spans_days() {
        Expect.eq(2040, hiddenF(2, 400, 1, hiddenAt(0, 540, 1020, new int[]{500, 2040})));
    }

    static void test_p1_meeting_across_midnight() {
        Expect.eq(1400, hiddenF(2, 120, 1, hiddenAt(0, 0, 1440, new int[]{0, 1400})));
        Expect.eq(1300, hiddenF(2, 200, 1, hiddenAt(60, 0, 1440, new int[]{0, 1300})));
    }

    static void test_p1_meeting_must_end_inside_horizon() {
        Expect.eq(1080, hiddenF(1, 360, 1, hiddenAt(-600, 480, 1200, new int[]{0, 360})));
        Expect.eq(-1, hiddenF(1, 361, 1, hiddenAt(-600, 480, 1200, new int[]{0, 360})));
    }

    static void test_p1_impossible() {
        Expect.eq(-1, hiddenF(1, 30, 2, hiddenAt(0, 540, 1020)));
        Expect.eq(-1, hiddenF(3, 481, 1, hiddenAt(0, 540, 1020), hiddenAt(0, 540, 1020)));
    }

    static void test_p1_mixed_time_zones() {
        Attendee[] team = {
            hiddenAt(0, 540, 1020, new int[]{600, 720}),
            hiddenAt(60, 480, 960, new int[]{540, 560}),
            hiddenAt(-300, 540, 1020),
            hiddenAt(330, 600, 1080, new int[]{300, 420}),
            hiddenAt(540, 540, 1140, new int[]{1000, 1200}),
        };
        Expect.eq(420, hiddenF(2, 30, 3, team));
        Expect.eq(560, hiddenF(2, 30, 4, team));
        Expect.eq(420, hiddenF(2, 90, 3, team));
        Expect.eq(-1, hiddenF(2, 30, 5, team));
    }

    static long hiddenSeed;
    static int hiddenRnd(int n) {
        hiddenSeed = (hiddenSeed * 1103515245L + 12345) % 2147483648L;
        return (int) (hiddenSeed / 65536 % n);
    }

    static List<Attendee> hiddenLargeOrg() {
        hiddenSeed = 12345;
        List<Attendee> big = new ArrayList<>();
        for (int i = 0; i < 1000; i++) {
            int ws = 420 + hiddenRnd(180), we = ws + 420 + hiddenRnd(180);
            int[][] busy = new int[200][];
            for (int j = 0; j < 200; j++) { int s = hiddenRnd(30 * 1440 - 60); busy[j] = new int[]{s, s + 15 + hiddenRnd(180)}; }
            big.add(new Attendee(-300 + 15 * hiddenRnd(41), ws, we, busy));
        }
        return big;
    }

    static void test_p1_large_org() {
        List<Attendee> big = hiddenLargeOrg();
        long start = System.nanoTime();
        Expect.eq(33623, Scheduler.earliestQuorumSlot(big, 30, 45, 500));
        Expect.eq(-1, Scheduler.earliestQuorumSlot(big, 30, 45, 800));
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.isTrue(ms <= 2000, "took " + ms + " ms for 1000 attendees and 200000 busy blocks; aim for about O(N log N) in the total number of busy blocks");
    }
}
