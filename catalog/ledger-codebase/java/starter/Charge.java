/** One captured payment to a merchant. */
public final class Charge {
    public final String id;
    public final String merchant;
    public final String currency;
    /** "card" or "bank". */
    public final String method;
    /** Captured amount, minor units. */
    public final long amount;
    public final long capturedAt;
    /** capturedAt plus the method's hold. */
    public final long availableOn;
    /** Refunded so far, minor units. */
    public long refunded;
    /** Settlement batch that paid it out; empty until settled. */
    public String batch = "";
    /** Capture order. */
    long seq;

    Charge(String id, String merchant, String currency, String method, long amount, long capturedAt, long availableOn) {
        this.id = id;
        this.merchant = merchant;
        this.currency = currency;
        this.method = method;
        this.amount = amount;
        this.capturedAt = capturedAt;
        this.availableOn = availableOn;
    }

    Charge copy() {
        Charge c = new Charge(id, merchant, currency, method, amount, capturedAt, availableOn);
        c.refunded = refunded;
        c.batch = batch;
        c.seq = seq;
        return c;
    }
}
