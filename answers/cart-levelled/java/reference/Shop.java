import java.util.*;

/** An online shop's catalog, shopping carts, promo codes and order history. Timestamps only ever increase. */
public class Shop {
    /** A cart untouched for this many minutes is abandoned. */
    static final int CART_TTL = 60;

    private static final class Product {
        final long price;
        int stock;
        int sold;
        Product(long price, int stock) { this.price = price; this.stock = stock; }
    }

    private static final class Cart {
        final TreeMap<String, Integer> lines = new TreeMap<>();
        int touched;
        String promo;
    }

    private static final class Promo {
        final int percent;
        final long minTotal;
        final int expiresAt;
        Promo(int percent, long minTotal, int expiresAt) { this.percent = percent; this.minTotal = minTotal; this.expiresAt = expiresAt; }
    }

    private static final class Order {
        final int ts;
        final long total;
        final Map<String, Integer> lines;
        boolean cancelled;
        Order(int ts, long total, Map<String, Integer> lines) { this.ts = ts; this.total = total; this.lines = lines; }
    }

    private final Map<String, Product> products = new HashMap<>();
    private final Map<String, Cart> carts = new HashMap<>();
    private final Map<String, Promo> promos = new HashMap<>();
    private final Map<String, List<Order>> history = new HashMap<>();

    public Shop() {}

    private static boolean live(Cart c, int ts) { return ts < c.touched + CART_TTL; }

    /** The cart if it exists and hasn't been abandoned; an abandoned cart is dropped. */
    private Cart cart(int ts, String cartId) {
        Cart c = carts.get(cartId);
        if (c != null && !live(c, ts)) { carts.remove(cartId); c = null; }
        return c;
    }

    // ---------------------------------------------------------------- level 1

    public boolean addProduct(int ts, String sku, long priceCents, int stock) {
        if (products.containsKey(sku) || priceCents <= 0 || stock < 0) return false;
        products.put(sku, new Product(priceCents, stock));
        return true;
    }

    public boolean addToCart(int ts, String cartId, String sku, int qty) {
        Product p = products.get(sku);
        if (p == null || qty <= 0) return false;
        Cart c = cart(ts, cartId);
        int have = c == null ? 0 : c.lines.getOrDefault(sku, 0);
        if (have + qty > p.stock) return false;
        if (c == null) { c = new Cart(); carts.put(cartId, c); }
        c.lines.put(sku, have + qty);
        c.touched = ts;
        return true;
    }

    public int removeFromCart(int ts, String cartId, String sku, int qty) {
        Cart c = cart(ts, cartId);
        if (c == null || qty <= 0 || !c.lines.containsKey(sku)) return -1;
        int left = Math.max(0, c.lines.get(sku) - qty);
        if (left == 0) c.lines.remove(sku); else c.lines.put(sku, left);
        c.touched = ts;
        return left;
    }

    public long cartTotal(int ts, String cartId) {
        Cart c = cart(ts, cartId);
        if (c == null) return 0;
        long sub = 0;
        for (Map.Entry<String, Integer> e : c.lines.entrySet()) sub += products.get(e.getKey()).price * e.getValue();
        Promo pr = c.promo == null ? null : promos.get(c.promo);
        if (pr != null && ts < pr.expiresAt && sub >= pr.minTotal) sub -= sub * pr.percent / 100;
        return sub;
    }

    public List<String> items(int ts, String cartId) {
        Cart c = cart(ts, cartId);
        List<String> out = new ArrayList<>();
        if (c != null) for (Map.Entry<String, Integer> e : c.lines.entrySet()) out.add(e.getKey() + ":" + e.getValue());
        return out;
    }

    // ---------------------------------------------------------------- level 2

    public long checkout(int ts, String cartId) {
        Cart c = cart(ts, cartId);
        if (c == null || c.lines.isEmpty()) return -1;
        for (Map.Entry<String, Integer> e : c.lines.entrySet())
            if (products.get(e.getKey()).stock < e.getValue()) return -1;
        long total = cartTotal(ts, cartId);
        for (Map.Entry<String, Integer> e : c.lines.entrySet()) {
            Product p = products.get(e.getKey());
            p.stock -= e.getValue();
            p.sold += e.getValue();
        }
        history.computeIfAbsent(cartId, k -> new ArrayList<>()).add(new Order(ts, total, new TreeMap<>(c.lines)));
        carts.remove(cartId);
        return total;
    }

    public int stockOf(int ts, String sku) {
        Product p = products.get(sku);
        return p == null ? -1 : p.stock;
    }

    public List<String> topSellers(int ts, int n) {
        List<String> skus = new ArrayList<>();
        for (Map.Entry<String, Product> e : products.entrySet()) if (e.getValue().sold > 0) skus.add(e.getKey());
        skus.sort((a, b) -> {
            int d = products.get(b).sold - products.get(a).sold;
            return d != 0 ? d : a.compareTo(b);
        });
        List<String> out = new ArrayList<>();
        for (String s : skus) if (out.size() < n) out.add(s + "(" + products.get(s).sold + ")");
        return out;
    }

    // ---------------------------------------------------------------- level 3

    public boolean addPromo(int ts, String code, int percentOff, long minTotalCents, int ttl) {
        if (promos.containsKey(code) || percentOff < 1 || percentOff > 100 || minTotalCents < 0 || ttl <= 0) return false;
        promos.put(code, new Promo(percentOff, minTotalCents, ts + ttl));
        return true;
    }

    public boolean applyPromo(int ts, String cartId, String code) {
        Cart c = cart(ts, cartId);
        Promo pr = promos.get(code);
        if (c == null || c.lines.isEmpty() || pr == null || ts >= pr.expiresAt) return false;
        c.promo = code;
        c.touched = ts;
        return true;
    }

    public int activeCarts(int ts) {
        int n = 0;
        for (Cart c : carts.values()) if (live(c, ts) && !c.lines.isEmpty()) n++;
        return n;
    }

    // ---------------------------------------------------------------- level 4

    public boolean merge(int ts, String guestId, String userId) {
        if (guestId.equals(userId)) return false;
        Cart g = cart(ts, guestId);
        if (g == null || g.lines.isEmpty()) return false;
        Cart u = cart(ts, userId);
        if (u == null) { u = new Cart(); carts.put(userId, u); }
        for (Map.Entry<String, Integer> e : g.lines.entrySet()) {
            int have = u.lines.getOrDefault(e.getKey(), 0);
            int q = Math.max(have, Math.min(have + e.getValue(), products.get(e.getKey()).stock));
            if (q > 0) u.lines.put(e.getKey(), q);
        }
        Promo up = u.promo == null ? null : promos.get(u.promo);
        if (up == null || ts >= up.expiresAt) u.promo = g.promo;
        u.touched = ts;
        carts.remove(guestId);
        List<Order> moved = history.remove(guestId);
        if (moved != null) {
            List<Order> h = history.computeIfAbsent(userId, k -> new ArrayList<>());
            h.addAll(moved);
            h.sort(Comparator.comparingInt(o -> o.ts));
        }
        return true;
    }

    public List<String> orderHistory(int ts, String cartId) {
        List<String> out = new ArrayList<>();
        for (Order o : history.getOrDefault(cartId, List.of())) out.add(o.ts + ":" + (o.cancelled ? "cancelled" : o.total));
        return out;
    }

    public boolean cancelOrder(int ts, String cartId, int orderTs) {
        for (Order o : history.getOrDefault(cartId, List.of())) {
            if (o.ts != orderTs || o.cancelled) continue;
            for (Map.Entry<String, Integer> e : o.lines.entrySet()) {
                Product p = products.get(e.getKey());
                p.stock += e.getValue();
                p.sold -= e.getValue();
            }
            o.cancelled = true;
            return true;
        }
        return false;
    }
}
