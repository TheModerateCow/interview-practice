// An example to copy. Run your tests with the My tests button: every static void method whose
// name starts with "test" runs; use Expect.eq, Expect.isTrue and Expect.raises to check things.
public class ExampleTest {
    static void testExampleCapture() {
        Ledger l = new Ledger();
        l.addMerchant("m1", new Pricing(250));
        l.capture("ch1", "m1", "USD", 1999, "card", 100);
        Expect.eq(1999L, l.balance(Journal.pendingAccount("m1"), "USD"));
        Expect.eq(0L, l.trialBalance("USD"));
    }
}
