import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** The daily digest. */
final class Digest {
    private Digest() {}

    /** The user's held notifications from their local day before the one containing {@code now}. */
    static List<DigestLine> build(Store store, String id, long now) {
        throw new UnsupportedOperationException("not implemented");
    }
}
