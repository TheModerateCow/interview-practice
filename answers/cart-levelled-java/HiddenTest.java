import java.util.List;

public class HiddenTest {
    static List<String> hiddenList(String... s) { return List.of(s); }

    /** A shop with the given products added as sku, price, stock triples at ts 1, 2, ... */
    static Shop hiddenShop(Object... p) {
        Shop s = new Shop();
        for (int i = 0; i + 2 < p.length; i += 3)
            Expect.isTrue(s.addProduct(i / 3 + 1, (String) p[i], ((Number) p[i + 1]).longValue(), ((Number) p[i + 2]).intValue()), "addProduct " + p[i] + " failed");
        return s;
    }

    // ---------------------------------------------------------------- level 1

    static void test_l1_add_product_rules() {
        Shop s = new Shop();
        Expect.eq(true, s.addProduct(1, "mug", 1200, 5));
        Expect.eq(false, s.addProduct(2, "mug", 900, 9));
        Expect.eq(false, s.addProduct(3, "pen", 0, 5));
        Expect.eq(false, s.addProduct(4, "pen", 150, -1));
        Expect.eq(true, s.addProduct(5, "sold-out", 300, 0));
        Expect.eq(false, s.addToCart(6, "c1", "sold-out", 1));
        Expect.eq(false, s.addToCart(7, "c1", "pen", 1));
        Expect.eq(true, s.addToCart(8, "c1", "mug", 1));
        Expect.eq(1200L, s.cartTotal(9, "c1"));
    }

    static void test_l1_add_accumulates() {
        Shop s = hiddenShop("tee", 1999, 10, "cap", 1250, 10);
        Expect.eq(true, s.addToCart(5, "c1", "tee", 2));
        Expect.eq(true, s.addToCart(6, "c1", "tee", 3));
        Expect.eq(true, s.addToCart(7, "c1", "cap", 1));
        Expect.eq(false, s.addToCart(8, "c1", "cap", 0));
        Expect.eq(false, s.addToCart(9, "c1", "cap", -2));
        Expect.eq(hiddenList("cap:1", "tee:5"), s.items(10, "c1"));
        Expect.eq(11245L, s.cartTotal(11, "c1"));
    }

    static void test_l1_stock_limit() {
        Shop s = hiddenShop("lamp", 4500, 3);
        Expect.eq(true, s.addToCart(5, "c1", "lamp", 2));
        Expect.eq(false, s.addToCart(6, "c1", "lamp", 2));
        Expect.eq(true, s.addToCart(7, "c1", "lamp", 1));
        Expect.eq(false, s.addToCart(8, "c1", "lamp", 1));
        Expect.eq(true, s.addToCart(9, "c2", "lamp", 3));
        Expect.eq(false, s.addToCart(10, "c3", "lamp", 4));
        Expect.eq(hiddenList("lamp:3"), s.items(11, "c1"));
        Expect.eq(hiddenList(), s.items(12, "c3"));
        Expect.eq(13500L, s.cartTotal(13, "c2"));
    }

    static void test_l1_remove() {
        Shop s = hiddenShop("mug", 800, 10, "pen", 150, 10);
        s.addToCart(5, "c1", "mug", 4);
        s.addToCart(6, "c1", "pen", 2);
        Expect.eq(1, s.removeFromCart(7, "c1", "mug", 3));
        Expect.eq(0, s.removeFromCart(8, "c1", "pen", 5));
        Expect.eq(-1, s.removeFromCart(9, "c1", "pen", 1));
        Expect.eq(-1, s.removeFromCart(10, "c1", "mug", 0));
        Expect.eq(-1, s.removeFromCart(11, "nobody", "mug", 1));
        Expect.eq(hiddenList("mug:1"), s.items(12, "c1"));
        Expect.eq(800L, s.cartTotal(13, "c1"));
        Expect.eq(true, s.addToCart(14, "c1", "mug", 9));
        Expect.eq(hiddenList("mug:10"), s.items(15, "c1"));
    }

    static void test_l1_items_sorted_and_total() {
        Shop s = hiddenShop("mug", 1200, 9, "lamp", 4500, 9, "desk", 25000, 9);
        s.addToCart(5, "c1", "mug", 3);
        s.addToCart(6, "c1", "lamp", 2);
        s.addToCart(7, "c1", "desk", 1);
        Expect.eq(hiddenList("desk:1", "lamp:2", "mug:3"), s.items(8, "c1"));
        Expect.eq(37600L, s.cartTotal(9, "c1"));
        Expect.eq(0L, s.cartTotal(10, "ghost"));
        Expect.eq(hiddenList(), s.items(11, "ghost"));
        s.addToCart(12, "c2", "mug", 1);
        Expect.eq(1200L, s.cartTotal(13, "c2"));
        Expect.eq(37600L, s.cartTotal(14, "c1"));
    }

    // ---------------------------------------------------------------- level 2

    static void test_l2_checkout_charges_and_takes_stock() {
        Shop s = hiddenShop("tee", 1999, 10, "cap", 1250, 4);
        s.addToCart(5, "c1", "tee", 3);
        s.addToCart(6, "c1", "cap", 2);
        Expect.eq(8497L, s.checkout(7, "c1"));
        Expect.eq(7, s.stockOf(8, "tee"));
        Expect.eq(2, s.stockOf(9, "cap"));
        Expect.eq(hiddenList(), s.items(10, "c1"));
        Expect.eq(0L, s.cartTotal(11, "c1"));
        Expect.eq(-1L, s.checkout(12, "c1"));
        Expect.eq(false, s.addToCart(13, "c1", "cap", 3));
        Expect.eq(true, s.addToCart(14, "c1", "cap", 2));
    }

    static void test_l2_checkout_all_or_nothing() {
        Shop s = hiddenShop("lamp", 4500, 3, "bulb", 300, 10);
        s.addToCart(5, "a", "lamp", 2);
        s.addToCart(6, "b", "lamp", 2);
        s.addToCart(7, "b", "bulb", 4);
        Expect.eq(9000L, s.checkout(8, "a"));
        Expect.eq(-1L, s.checkout(9, "b"));
        Expect.eq(1, s.stockOf(10, "lamp"));
        Expect.eq(10, s.stockOf(11, "bulb"));
        Expect.eq(hiddenList("bulb:4", "lamp:2"), s.items(12, "b"));
        Expect.eq(1, s.removeFromCart(13, "b", "lamp", 1));
        Expect.eq(5700L, s.checkout(14, "b"));
        Expect.eq(0, s.stockOf(15, "lamp"));
    }

    static void test_l2_checkout_rejects() {
        Shop s = hiddenShop("mug", 800, 5);
        s.addToCart(5, "c1", "mug", 2);
        s.removeFromCart(6, "c1", "mug", 2);
        Expect.eq(-1L, s.checkout(7, "c1"));
        Expect.eq(-1L, s.checkout(8, "nobody"));
        Expect.eq(5, s.stockOf(9, "mug"));
        Expect.eq(-1, s.stockOf(10, "pen"));
        Expect.eq(hiddenList(), s.topSellers(11, 3));
    }

    static void test_l2_top_sellers_order() {
        Shop s = hiddenShop("tee", 1999, 50, "cap", 1250, 50, "mug", 800, 50, "pen", 150, 50);
        s.addToCart(5, "a", "mug", 3);
        s.addToCart(6, "a", "pen", 5);
        s.checkout(7, "a");
        s.addToCart(8, "b", "tee", 3);
        s.addToCart(9, "b", "cap", 1);
        s.checkout(10, "b");
        s.addToCart(11, "c", "cap", 2);
        s.checkout(12, "c");
        Expect.eq(hiddenList("pen(5)", "cap(3)", "mug(3)", "tee(3)"), s.topSellers(13, 10));
        Expect.eq(hiddenList("pen(5)", "cap(3)"), s.topSellers(14, 2));
        Expect.eq(hiddenList(), s.topSellers(15, 0));
    }

    static void test_l2_top_sellers_count_checkouts_only() {
        Shop s = hiddenShop("lamp", 4500, 2, "bulb", 300, 20);
        s.addToCart(5, "a", "bulb", 7);
        s.addToCart(6, "b", "lamp", 2);
        s.addToCart(7, "c", "lamp", 1);
        s.addToCart(8, "c", "bulb", 1);
        s.checkout(9, "b");
        Expect.eq(-1L, s.checkout(10, "c"));
        Expect.eq(hiddenList("lamp(2)"), s.topSellers(11, 5));
        s.removeFromCart(12, "c", "lamp", 1);
        Expect.eq(300L, s.checkout(13, "c"));
        Expect.eq(2100L, s.checkout(14, "a"));
        Expect.eq(hiddenList("bulb(8)", "lamp(2)"), s.topSellers(15, 5));
    }

    // ---------------------------------------------------------------- level 3

    static void test_l3_cart_expires() {
        Shop s = hiddenShop("mug", 800, 10);
        s.addToCart(10, "c1", "mug", 2);
        Expect.eq(1600L, s.cartTotal(67, "c1"));
        Expect.eq(hiddenList("mug:2"), s.items(68, "c1"));
        Expect.eq(1, s.activeCarts(69));
        Expect.eq(0L, s.cartTotal(70, "c1"));
        Expect.eq(hiddenList(), s.items(71, "c1"));
        Expect.eq(0, s.activeCarts(72));
        Expect.eq(-1L, s.checkout(73, "c1"));
        Expect.eq(-1, s.removeFromCart(74, "c1", "mug", 1));
        Expect.eq(10, s.stockOf(75, "mug"));
    }

    static void test_l3_touch_restarts_clock() {
        Shop s = hiddenShop("mug", 800, 10, "pen", 150, 10);
        s.addToCart(10, "c1", "mug", 2);
        Expect.eq(1, s.removeFromCart(50, "c1", "mug", 1));
        Expect.eq(800L, s.cartTotal(100, "c1"));
        s.cartTotal(105, "c1");
        Expect.eq(hiddenList("mug:1"), s.items(109, "c1"));
        Expect.eq(hiddenList(), s.items(110, "c1"));
        Expect.eq(true, s.addToCart(111, "c1", "pen", 1));
        Expect.eq(hiddenList("pen:1"), s.items(112, "c1"));
        s.addToCart(113, "c2", "mug", 1);
        s.addToCart(114, "c3", "mug", 1);
        s.removeFromCart(115, "c3", "mug", 1);
        Expect.eq(2, s.activeCarts(116));
        Expect.eq(1, s.activeCarts(171));
        Expect.eq(0, s.activeCarts(173));
    }

    static void test_l3_promo_discount() {
        Shop s = hiddenShop("tee", 999, 10, "cap", 1250, 10);
        Expect.eq(true, s.addPromo(5, "SAVE15", 15, 0, 100));
        s.addToCart(6, "c1", "tee", 1);
        Expect.eq(true, s.applyPromo(7, "c1", "SAVE15"));
        Expect.eq(850L, s.cartTotal(8, "c1"));
        s.addToCart(9, "c1", "cap", 1);
        Expect.eq(1912L, s.cartTotal(10, "c1"));
        Expect.eq(1912L, s.checkout(11, "c1"));
        Expect.eq(true, s.addPromo(12, "HALF", 50, 0, 100));
        s.addToCart(13, "c2", "cap", 1);
        Expect.eq(true, s.applyPromo(14, "c2", "SAVE15"));
        Expect.eq(true, s.applyPromo(15, "c2", "HALF"));
        Expect.eq(625L, s.cartTotal(16, "c2"));
    }

    static void test_l3_promo_min_total() {
        Shop s = hiddenShop("mug", 1000, 10, "pen", 1, 10);
        Expect.eq(true, s.addPromo(5, "BIG", 10, 5000, 500));
        s.addToCart(6, "c1", "mug", 4);
        s.addToCart(7, "c1", "pen", 9);
        Expect.eq(true, s.applyPromo(8, "c1", "BIG"));
        Expect.eq(4009L, s.cartTotal(9, "c1"));
        s.addToCart(10, "c1", "mug", 1);
        s.removeFromCart(11, "c1", "pen", 9);
        Expect.eq(4500L, s.cartTotal(12, "c1"));
        s.removeFromCart(13, "c1", "mug", 1);
        Expect.eq(4000L, s.cartTotal(14, "c1"));
    }

    static void test_l3_promo_expiry_and_rules() {
        Shop s = hiddenShop("mug", 1000, 10);
        Expect.eq(true, s.addPromo(5, "FLASH", 20, 0, 30));
        Expect.eq(false, s.addPromo(6, "FLASH", 30, 0, 30));
        Expect.eq(false, s.addPromo(7, "ZERO", 0, 0, 30));
        Expect.eq(false, s.addPromo(8, "OVER", 101, 0, 30));
        Expect.eq(false, s.addPromo(9, "NEG", 10, -1, 30));
        Expect.eq(false, s.addPromo(10, "NOW", 10, 0, 0));
        Expect.eq(false, s.applyPromo(11, "c1", "FLASH"));
        s.addToCart(12, "c1", "mug", 1);
        Expect.eq(false, s.applyPromo(13, "c1", "NOPE"));
        Expect.eq(true, s.applyPromo(14, "c1", "FLASH"));
        Expect.eq(800L, s.cartTotal(34, "c1"));
        Expect.eq(1000L, s.cartTotal(35, "c1"));
        s.addToCart(36, "c2", "mug", 1);
        Expect.eq(false, s.applyPromo(37, "c2", "FLASH"));
        Expect.eq(true, s.addPromo(38, "ALL", 100, 0, 10));
        Expect.eq(true, s.applyPromo(39, "c2", "ALL"));
        Expect.eq(0L, s.cartTotal(40, "c2"));
        Expect.eq(2, s.activeCarts(41));
    }

    // ---------------------------------------------------------------- level 4

    static void test_l4_merge_sums_lines() {
        Shop s = hiddenShop("tee", 1999, 10, "cap", 1250, 10, "mug", 800, 10);
        s.addToCart(5, "guest-1", "tee", 2);
        s.addToCart(6, "guest-1", "mug", 1);
        s.addToCart(7, "ana", "tee", 1);
        s.addToCart(8, "ana", "cap", 1);
        Expect.eq(true, s.merge(9, "guest-1", "ana"));
        Expect.eq(hiddenList("cap:1", "mug:1", "tee:3"), s.items(10, "ana"));
        Expect.eq(hiddenList(), s.items(11, "guest-1"));
        Expect.eq(false, s.merge(12, "guest-1", "ana"));
        Expect.eq(false, s.merge(13, "ana", "ana"));
        Expect.eq(1, s.activeCarts(14));
        Expect.eq(8047L, s.cartTotal(15, "ana"));
    }

    static void test_l4_merge_caps_at_stock() {
        Shop s = hiddenShop("lamp", 4500, 3, "bulb", 300, 10);
        s.addToCart(5, "guest", "lamp", 2);
        s.addToCart(6, "guest", "bulb", 4);
        s.addToCart(7, "ana", "lamp", 1);
        s.addToCart(8, "bo", "bulb", 8);
        s.checkout(9, "bo");
        Expect.eq(true, s.merge(10, "guest", "ana"));
        Expect.eq(hiddenList("bulb:2", "lamp:3"), s.items(11, "ana"));
        s.addToCart(12, "g2", "lamp", 1);
        s.addToCart(13, "cy", "lamp", 1);
        s.checkout(14, "cy");
        Expect.eq(true, s.merge(15, "g2", "ana"));
        Expect.eq(hiddenList("bulb:2", "lamp:3"), s.items(16, "ana"));
    }

    static void test_l4_merge_new_cart_and_promos() {
        Shop s = hiddenShop("mug", 1000, 10);
        s.addPromo(5, "TEN", 10, 0, 500);
        s.addPromo(6, "TWENTY", 20, 0, 50);
        s.addToCart(7, "guest", "mug", 2);
        s.applyPromo(8, "guest", "TEN");
        Expect.eq(true, s.merge(9, "guest", "ana"));
        Expect.eq(1800L, s.cartTotal(10, "ana"));
        s.addToCart(11, "g2", "mug", 1);
        s.applyPromo(12, "g2", "TWENTY");
        Expect.eq(true, s.merge(13, "g2", "ana"));
        Expect.eq(2700L, s.cartTotal(14, "ana"));
        s.addToCart(15, "bo", "mug", 2);
        s.applyPromo(16, "bo", "TWENTY");
        s.addToCart(57, "g3", "mug", 1);
        s.applyPromo(58, "g3", "TEN");
        Expect.eq(true, s.merge(59, "g3", "bo"));
        Expect.eq(hiddenList("mug:3"), s.items(60, "bo"));
        Expect.eq(2700L, s.cartTotal(61, "bo"));
        s.addToCart(62, "old", "mug", 1);
        Expect.eq(true, s.addToCart(100, "bo", "mug", 1));
        Expect.eq(false, s.merge(122, "old", "bo"));
        Expect.eq(hiddenList("mug:4"), s.items(123, "bo"));
    }

    static void test_l4_order_history_follows_merge() {
        Shop s = hiddenShop("mug", 800, 50, "pen", 150, 50);
        s.addToCart(5, "ana", "mug", 1);
        s.checkout(6, "ana");
        s.addToCart(7, "guest", "pen", 2);
        s.checkout(8, "guest");
        s.addToCart(9, "ana", "pen", 1);
        s.checkout(10, "ana");
        s.addToCart(11, "guest", "mug", 2);
        Expect.eq(hiddenList("6:800", "10:150"), s.orderHistory(12, "ana"));
        Expect.eq(hiddenList("8:300"), s.orderHistory(13, "guest"));
        Expect.eq(true, s.merge(14, "guest", "ana"));
        Expect.eq(hiddenList("6:800", "8:300", "10:150"), s.orderHistory(15, "ana"));
        Expect.eq(hiddenList(), s.orderHistory(16, "guest"));
        Expect.eq(1600L, s.checkout(17, "ana"));
        Expect.eq(hiddenList("6:800", "8:300", "10:150", "17:1600"), s.orderHistory(18, "ana"));
        Expect.eq(hiddenList(), s.orderHistory(19, "nobody"));
    }

    static void test_l4_cancel_order() {
        Shop s = hiddenShop("lamp", 4500, 5, "bulb", 300, 20);
        s.addToCart(5, "ana", "lamp", 2);
        s.addToCart(6, "ana", "bulb", 4);
        Expect.eq(10200L, s.checkout(7, "ana"));
        s.addToCart(8, "ana", "bulb", 3);
        s.checkout(9, "ana");
        s.addToCart(10, "bo", "lamp", 1);
        s.checkout(11, "bo");
        Expect.eq(hiddenList("bulb(7)", "lamp(3)"), s.topSellers(12, 5));
        Expect.eq(true, s.cancelOrder(13, "ana", 7));
        Expect.eq(4, s.stockOf(14, "lamp"));
        Expect.eq(17, s.stockOf(15, "bulb"));
        Expect.eq(hiddenList("bulb(3)", "lamp(1)"), s.topSellers(16, 5));
        Expect.eq(hiddenList("7:cancelled", "9:900"), s.orderHistory(17, "ana"));
        Expect.eq(false, s.cancelOrder(18, "ana", 7));
        Expect.eq(false, s.cancelOrder(19, "ana", 11));
        Expect.eq(false, s.cancelOrder(20, "ana", 8));
        Expect.eq(true, s.cancelOrder(21, "bo", 11));
        Expect.eq(hiddenList("bulb(3)"), s.topSellers(22, 5));
        Expect.eq(true, s.addToCart(23, "cy", "lamp", 5));
    }
}
