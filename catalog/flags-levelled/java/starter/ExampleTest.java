// An example to copy. Run your tests with the My tests button.
public class ExampleTest {
    static void test_example_flag_on_in_dev() {
        var o = new FlagService();
        Expect.eq(true, o.createFlag(1, "new-nav"));
        Expect.eq(true, o.setEnabled(2, "new-nav", "dev", true));
        Expect.eq(true, o.isEnabled(3, "new-nav", "dev", "riya"));
    }
}
