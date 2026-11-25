/** Every error the inventory service reports. Callers branch on {@link #code}. */
public class InventoryException extends RuntimeException {
    public enum Code {
        /** A bad argument. */
        INVALID,
        /** An id that is already taken. */
        DUPLICATE,
        /** No reservation or transfer has that id. */
        NOT_FOUND,
        UNKNOWN_WAREHOUSE,
        /** Not enough available stock (on hand minus active reservations). */
        INSUFFICIENT_STOCK,
        /** The bins hold less than the pick asks for. */
        SHORT_PICK,
        /** The reservation is not active any more. */
        NOT_ACTIVE,
        /** The transfer is not in transit. */
        TRANSFER_STATE,
        /** A timestamp older than the service clock. */
        BACKDATED
    }

    public final Code code;

    public InventoryException(Code code, String message) {
        super(message.isEmpty() ? code.name() : code + ": " + message);
        this.code = code;
    }
}
