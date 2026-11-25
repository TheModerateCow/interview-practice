import java.util.List;

public class ExampleTest {
    static void test_example_two_job_chain() {
        Expect.eq(11, Pipeline.fastestRelease(List.of(new Job(-1, 7, 1), new Job(0, 4, 2)), 0));
    }
}
