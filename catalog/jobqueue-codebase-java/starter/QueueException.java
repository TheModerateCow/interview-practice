/** Every error the job queue reports. Callers branch on {@link #code}. */
public class QueueException extends RuntimeException {
    public enum Code {
        /** No live job has that id (it never existed, or it completed or was cancelled). */
        NOT_FOUND,
        /** The caller's lease is no longer the job's current lease: it ran out, or someone else holds it now. */
        LEASE_LOST,
        /** A bad argument, or an operation that doesn't apply to the job's state. */
        INVALID,
        /** A timestamp older than the queue clock. */
        BACKDATED
    }

    public final Code code;

    public QueueException(Code code, String message) {
        super(code + ": " + message);
        this.code = code;
    }
}
