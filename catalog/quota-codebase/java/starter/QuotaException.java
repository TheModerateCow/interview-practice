/** Every error the service raises. Callers branch on {@link #code}. */
public class QuotaException extends RuntimeException {
    public enum Code { UNKNOWN_KEY, DUPLICATE_KEY, REVOKED, UNKNOWN_PLAN, DUPLICATE_PLAN, INVALID_PLAN, BAD_COST, BAD_RANGE }

    public final Code code;

    public QuotaException(Code code, String message) {
        super(message);
        this.code = code;
    }

    static QuotaException unknownKey() { return new QuotaException(Code.UNKNOWN_KEY, "unknown api key"); }
    static QuotaException duplicateKey() { return new QuotaException(Code.DUPLICATE_KEY, "api key already exists"); }
    static QuotaException revoked() { return new QuotaException(Code.REVOKED, "api key revoked"); }
    static QuotaException unknownPlan() { return new QuotaException(Code.UNKNOWN_PLAN, "unknown plan"); }
    static QuotaException duplicatePlan() { return new QuotaException(Code.DUPLICATE_PLAN, "plan already exists"); }
    static QuotaException invalidPlan() {
        return new QuotaException(Code.INVALID_PLAN, "plan needs a positive limit and window and a non-negative burst");
    }
    static QuotaException badCost() { return new QuotaException(Code.BAD_COST, "request cost must be positive"); }
    static QuotaException badRange() { return new QuotaException(Code.BAD_RANGE, "report range must end after it starts"); }
}
