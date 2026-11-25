import java.util.List;

public class ExampleTest {
    static void test_example() {
        Expect.eq(12, Route.fastestDelivery(2, 5, 5, new int[]{0, 0}, List.of(new Road(0, 1, 12, 3))));
    }
}
