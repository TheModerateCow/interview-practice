import java.util.List;

// An example to copy. My tests runs every static void test...() method in *Test.java files.
// Expect.eq(expected, actual), Expect.isTrue(cond) and Expect.raises(Type.class, () -> ...) are provided.
// Note: Expect.eq compares boxed values, so write a long expected value with an L: 2500L.
public class ExampleTest {
    static void test_example_cart() {
        Shop shop = new Shop();
        Expect.eq(true, shop.addProduct(1, "scarf", 1250, 4));
        Expect.eq(true, shop.addToCart(2, "cart-9", "scarf", 2));
        Expect.eq(2500L, shop.cartTotal(3, "cart-9"));
        Expect.eq(List.of("scarf:2"), shop.items(4, "cart-9"));
    }
}
