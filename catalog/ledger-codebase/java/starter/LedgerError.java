/** Base class of every error the ledger raises. */
public class LedgerError extends RuntimeException {
    public LedgerError(String message) {
        super(message);
    }

    /** invalid request */
    public static class Invalid extends LedgerError {
        public Invalid(String m) { super(m); }
    }

    /** entry does not balance */
    public static class Unbalanced extends LedgerError {
        public Unbalanced(String m) { super(m); }
    }

    /** unknown currency */
    public static class UnknownCurrency extends LedgerError {
        public UnknownCurrency(String m) { super(m); }
    }

    /** entry is older than the ledger head */
    public static class Backdated extends LedgerError {
        public Backdated(String m) { super(m); }
    }

    /** not found */
    public static class NotFound extends LedgerError {
        public NotFound(String m) { super(m); }
    }

    /** already exists */
    public static class Duplicate extends LedgerError {
        public Duplicate(String m) { super(m); }
    }

    /** unknown merchant */
    public static class UnknownMerchant extends LedgerError {
        public UnknownMerchant(String m) { super(m); }
    }

    /** insufficient available balance */
    public static class InsufficientFunds extends LedgerError {
        public InsufficientFunds(String m) { super(m); }
    }

    /** payout cannot make that transition */
    public static class PayoutState extends LedgerError {
        public PayoutState(String m) { super(m); }
    }
}
