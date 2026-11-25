// An example to copy. My tests runs every *Test.java: each static void test... method is a test.
// Expect.eq(expected, actual), Expect.isTrue(cond), Expect.raises(Exception.class, () -> ...) are provided.
import java.util.List;

public class ExampleTest {
    static void test_one_attendee_in_utc_with_a_free_calendar() {
        Attendee alex = new Attendee(0, 540, 1020, new int[][]{});
        Expect.eq(540, Scheduler.earliestQuorumSlot(List.of(alex), 1, 30, 1));
    }
}
