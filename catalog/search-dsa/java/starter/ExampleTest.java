import java.util.List;

public class ExampleTest {
    static void test_example() {
        Expect.eq(2, SearchBox.fewestKeystrokes(List.of("pizza"), "pizzas"));
    }
}
