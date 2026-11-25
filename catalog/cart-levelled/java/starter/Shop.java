import java.util.List;

/** An online shop's catalog and shopping carts. Timestamps passed to its methods only ever increase. */
public class Shop {
    // your state here

    public Shop() {}

    /** Adds a product. False if the sku exists, the price isn't positive or the stock is negative. */
    public boolean addProduct(int ts, String sku, long priceCents, int stock) {
        throw new UnsupportedOperationException("not implemented");
    }

    /** Adds qty units of sku to the cart, creating the cart if needed. False, changing nothing, if the sku is
     *  unknown, qty isn't positive, or the cart would hold more units of the sku than are in stock. */
    public boolean addToCart(int ts, String cartId, String sku, int qty) {
        throw new UnsupportedOperationException("not implemented");
    }

    /** Takes up to qty units of sku out of the cart and returns how many are left (the line goes at 0).
     *  -1 if the cart or the line doesn't exist or qty isn't positive. */
    public int removeFromCart(int ts, String cartId, String sku, int qty) {
        throw new UnsupportedOperationException("not implemented");
    }

    /** The cart's total in cents; 0 for an unknown cart. */
    public long cartTotal(int ts, String cartId) {
        throw new UnsupportedOperationException("not implemented");
    }

    /** The cart's lines as "sku:qty", sorted by sku; empty for an unknown cart. */
    public List<String> items(int ts, String cartId) {
        throw new UnsupportedOperationException("not implemented");
    }
}
