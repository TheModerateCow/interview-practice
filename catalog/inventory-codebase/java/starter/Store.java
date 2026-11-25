import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** A SKU in one warehouse: the key of every per-SKU counter. */
record StockKey(String warehouse, String sku) {
    @Override
    public int hashCode() {
        return warehouse.hashCode() * 31 + sku.hashCode();
    }
}

/** A SKU in one bin of one warehouse. */
record BinKey(String warehouse, String bin, String sku) {
    StockKey stock() {
        return new StockKey(warehouse, sku);
    }

    @Override
    public int hashCode() {
        return (warehouse.hashCode() * 31 + bin.hashCode()) * 31 + sku.hashCode();
    }
}

/**
 * The in-memory state. Per-SKU counters are kept alongside the bins so availability checks never
 * walk the shelves.
 */
final class Store {
    final Map<BinKey, Integer> bins = new HashMap<>();
    /** Cached bins per SKU in pick order, built on first pick. */
    final Map<StockKey, List<String>> pickPath = new HashMap<>();
    /** Sum of the SKU's bins. */
    final Map<StockKey, Integer> onHand = new HashMap<>();
    /** Held by active reservations. */
    final Map<StockKey, Integer> reserved = new HashMap<>();
    /** In transit toward the warehouse. */
    final Map<StockKey, Integer> inbound = new HashMap<>();
    final Map<StockKey, Rule> rules = new HashMap<>();

    final Map<String, Reservation> reservations = new HashMap<>();
    final Expiry holds = new Expiry();
    final Map<String, Transfer> transfers = new HashMap<>();

    int onHand(StockKey k) {
        return onHand.getOrDefault(k, 0);
    }

    int reserved(StockKey k) {
        return reserved.getOrDefault(k, 0);
    }

    int inbound(StockKey k) {
        return inbound.getOrDefault(k, 0);
    }

    /** Adds qty of a SKU to a bin. */
    void putAway(BinKey k, int qty) {
        bins.merge(k, qty, Integer::sum);
        onHand.merge(k.stock(), qty, Integer::sum);
        if (!bins.containsKey(k)) {
            pickPath.remove(k.stock());
        }
    }

    /** The bins that hold (or held) the SKU, sorted by bin code, which is the order pickers walk the aisles. */
    List<String> path(StockKey k) {
        List<String> p = pickPath.get(k);
        if (p != null) return p;
        p = new ArrayList<>();
        for (BinKey b : bins.keySet()) {
            if (b.stock().equals(k)) p.add(b.bin());
        }
        Collections.sort(p);
        pickPath.put(k, p);
        return p;
    }

    /**
     * Takes qty of a SKU off the shelves, emptying bins in pick order. If the bins hold less than
     * qty it changes nothing and throws SHORT_PICK.
     */
    void pick(StockKey k, int qty) {
        List<String> path = path(k);
        int total = 0;
        for (String b : path) {
            total += bins.get(new BinKey(k.warehouse(), b, k.sku()));
        }
        if (total < qty) {
            throw new InventoryException(InventoryException.Code.SHORT_PICK, "bins hold " + total + ", " + qty + " requested");
        }
        for (String b : path) {
            BinKey bk = new BinKey(k.warehouse(), b, k.sku());
            int take = Math.min(qty, bins.get(bk));
            bins.merge(bk, -take, Integer::sum);
            onHand.merge(k, -take, Integer::sum);
            qty -= take;
            if (qty == 0) break;
        }
    }

    /** Closes an active reservation and gives its quantity back to available stock. */
    void endHold(Reservation r, Reservation.Status st, long at) {
        reserved.merge(new StockKey(r.warehouse, r.sku), -r.qty, Integer::sum);
        r.status = st;
        r.updatedAt = at;
    }
}
