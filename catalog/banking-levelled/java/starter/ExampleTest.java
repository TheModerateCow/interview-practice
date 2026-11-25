// An example to copy. Run your tests with the My tests button.
public class ExampleTest {
    static void test_example_deposit_balance() {
        var b = new Bank();
        Expect.isTrue(b.openAccount(1, "acc-x"));
        b.deposit(2, "acc-x", 40);
        Expect.eq(40, b.balance(3, "acc-x"));
    }
}
