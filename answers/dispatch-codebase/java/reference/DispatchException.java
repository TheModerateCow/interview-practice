/** Every error the dispatcher reports. Callers branch on {@link #code}. */
public class DispatchException extends RuntimeException {
    public enum Code {
        NO_COURIER, BAD_TRANSITION, INVALID_COURIER, DUPLICATE_ORDER, DUPLICATE_COURIER,
        UNKNOWN_ORDER, UNKNOWN_COURIER, NOT_ASSIGNED, ORDER_CLOSED
    }

    public final Code code;

    public DispatchException(Code code, String message) {
        super(message);
        this.code = code;
    }
}
