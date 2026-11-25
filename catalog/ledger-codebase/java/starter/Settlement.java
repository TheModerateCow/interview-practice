import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Settlement: moving available charges from pending to available, minus fees. */
final class Settlement {
    private Settlement() {}

    /**
     * Moves every charge of merchant whose funds are available at ts from pending to available, minus
     * fees, as one batch per currency (sorted by currency code).
     */
    static List<Batch> settle(Ledger l, String merchant, long ts) {
        throw new UnsupportedOperationException("not implemented");
    }
}
