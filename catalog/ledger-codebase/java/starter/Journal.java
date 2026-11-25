/**
 * Account names used by the payment flows. Balances are signed: a positive merchant balance is money
 * the platform owes that merchant.
 */
public final class Journal {
    private Journal() {}

    /** Funds due from card networks and banks. */
    public static final String CLEARING_ACCOUNT = "platform:clearing";
    /** Platform revenue. */
    public static final String FEES_ACCOUNT = "platform:fees";
    /** Payouts sent, not yet confirmed by the bank. */
    public static final String IN_TRANSIT_ACCOUNT = "platform:payouts-in-transit";
    /** Payouts the bank confirmed. */
    public static final String BANK_ACCOUNT = "platform:bank-paid-out";

    /** A merchant's captured funds that have not been settled yet. */
    public static String pendingAccount(String merchant) {
        return "merchant:" + merchant + ":pending";
    }

    /** A merchant's settled funds, ready to be paid out. */
    public static String availableAccount(String merchant) {
        return "merchant:" + merchant + ":available";
    }
}
