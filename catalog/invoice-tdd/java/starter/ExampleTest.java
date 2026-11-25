// An example to copy. Write your own tests in this style and run them with My tests.
public class ExampleTest {
    static void test_example_single_line() {
        var inv = new Invoice(0, "net30");
        Expect.eq(2000, inv.addLine(1000, 2, "standard")); // 2 x 10.00, no discount
        Expect.eq(2400, inv.total()); // plus 20% tax
    }

    static void test_example_unknown_terms() {
        try {
            new Invoice(0, "net7");
        } catch (InvalidTermsException e) {
            return;
        }
        throw new AssertionError("expected InvalidTermsException");
    }
}
