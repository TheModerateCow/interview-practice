import java.util.List;

// An example to copy. Run your tests with the My tests button: every static void method whose
// name starts with "test" runs; use Expect.eq, Expect.isTrue and Expect.raises to check things.
public class ExampleTest {
    static void testSendGoesToEmail() {
        Service s = new Service();
        s.addUser("ana", 0);
        Result res = s.send(new Notification("ana", "welcome", "welcome-1", "Hi", 1000));
        Expect.eq(Notify.SENT, res.status());
        Expect.eq(List.of(Notify.EMAIL), res.channels());
    }
}
