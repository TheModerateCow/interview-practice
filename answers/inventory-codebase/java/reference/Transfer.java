/** Moves stock of one SKU from one warehouse to another. Callers only ever see copies. */
public final class Transfer {
    public enum Status { IN_TRANSIT, RECEIVED }

    final String id;
    final String from;
    final String to;
    final String sku;
    final int qty;
    final long shippedAt;

    Status status = Status.IN_TRANSIT;
    long receivedAt;
    /** Destination bin, once received. */
    String bin = "";

    Transfer(String id, String from, String to, String sku, int qty, long shippedAt) {
        this.id = id;
        this.from = from;
        this.to = to;
        this.sku = sku;
        this.qty = qty;
        this.shippedAt = shippedAt;
    }

    Transfer copy() {
        Transfer c = new Transfer(id, from, to, sku, qty, shippedAt);
        c.status = status;
        c.receivedAt = receivedAt;
        c.bin = bin;
        return c;
    }

    public String id() { return id; }
    public String from() { return from; }
    public String to() { return to; }
    public String sku() { return sku; }
    public int qty() { return qty; }
    public Status status() { return status; }
    public long shippedAt() { return shippedAt; }
    public long receivedAt() { return receivedAt; }
    public String bin() { return bin; }
}
