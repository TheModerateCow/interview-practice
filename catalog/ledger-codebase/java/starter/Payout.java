/**
 * A transfer of a merchant's available funds to their bank account. The status is "pending" until the
 * bank's webhook says it was "paid" or it "failed".
 */
public final class Payout {
    public final String id;
    public final String merchant;
    public final String currency;
    public final long amount;
    public String status;
    public long updatedAt;

    Payout(String id, String merchant, String currency, long amount, String status, long updatedAt) {
        this.id = id;
        this.merchant = merchant;
        this.currency = currency;
        this.amount = amount;
        this.status = status;
        this.updatedAt = updatedAt;
    }

    Payout copy() {
        return new Payout(id, merchant, currency, amount, status, updatedAt);
    }
}
