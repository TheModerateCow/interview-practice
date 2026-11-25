import java.util.ArrayList;
import java.util.List;

/** One settlement of a merchant's charges in one currency. */
public final class Batch {
    public final String id;
    public final String merchant;
    public final String currency;
    public final long ts;
    /** Charge ids, earliest availableOn first. */
    public final List<String> charges = new ArrayList<>();
    /** Captured minus refunded, over the batch's charges. */
    public long gross;
    public long fees;
    /** gross - fees, credited to the merchant's available balance. */
    public long net;

    Batch(String id, String merchant, String currency, long ts) {
        this.id = id;
        this.merchant = merchant;
        this.currency = currency;
        this.ts = ts;
    }
}
