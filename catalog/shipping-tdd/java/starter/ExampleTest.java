// An example to copy. Write your own tests first, run them with My tests,
// then implement Shipping.java.
public class ExampleTest {
    static void test_example_billable_grams() {
        Expect.eq(1500, Shipping.billableGrams(new Parcel(400, 30, 20, 10)));
    }
}
