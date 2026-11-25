/**
 * Holds stock of one SKU in one warehouse for an order until it is committed (picked for
 * shipping), released, or its hold runs out at {@code expiresAt}. The service owns these
 * objects; callers only ever see copies.
 */
public final class Reservation {
    public enum Status { ACTIVE, RELEASED, COMMITTED, EXPIRED }

    final String id;
    final String warehouse;
    final String sku;
    final int qty;
    final long createdAt;
    final long expiresAt;
    final int seq; // placement order, breaks expiresAt ties

    Status status = Status.ACTIVE;
    /** When status last changed; for an expired hold, expiresAt. */
    long updatedAt;

    Reservation(String id, String warehouse, String sku, int qty, long createdAt, long expiresAt, int seq) {
        this.id = id;
        this.warehouse = warehouse;
        this.sku = sku;
        this.qty = qty;
        this.createdAt = createdAt;
        this.expiresAt = expiresAt;
        this.seq = seq;
        this.updatedAt = createdAt;
    }

    Reservation copy() {
        Reservation c = new Reservation(id, warehouse, sku, qty, createdAt, expiresAt, seq);
        c.status = status;
        c.updatedAt = updatedAt;
        return c;
    }

    public String id() { return id; }
    public String warehouse() { return warehouse; }
    public String sku() { return sku; }
    public int qty() { return qty; }
    public long createdAt() { return createdAt; }
    public long expiresAt() { return expiresAt; }
    public Status status() { return status; }
    public long updatedAt() { return updatedAt; }
}
