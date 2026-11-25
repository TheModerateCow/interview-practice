// An example to copy. Write your own tests in this style and run them with My tests.
public class ExampleTest {
    static void test_example_earn() {
        var a = new Account();
        Expect.eq(20, a.earn(1, 2000)); // a 20.00 purchase
        Expect.eq(20, a.balance(1));
    }
}
