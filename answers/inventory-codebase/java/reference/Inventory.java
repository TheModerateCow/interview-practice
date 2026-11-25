import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * The inventory service for a network of warehouses. It is not safe for concurrent use: the API layer
 * serialises calls. Every call that takes {@code now} moves the service clock forward (and expires holds
 * that ran out); {@code now} may not go backwards (BACKDATED).
 */
public class Inventory {
    final Store store = new Store();
    final Set<String> warehouses = new HashSet<>();
    long now;
    int seq;

    public void addWarehouse(String id) {
        if (id.isEmpty()) throw new InventoryException(InventoryException.Code.INVALID, "empty warehouse id");
        if (!warehouses.add(id)) throw new InventoryException(InventoryException.Code.DUPLICATE, "warehouse " + id);
    }

    void checkWarehouse(String id) {
        if (!warehouses.contains(id)) throw new InventoryException(InventoryException.Code.UNKNOWN_WAREHOUSE, id);
    }

    /** Every warehouse, sorted. */
    List<String> warehouseIds() {
        List<String> ids = new ArrayList<>(warehouses);
        Collections.sort(ids);
        return ids;
    }

    /** Moves the clock to now and expires the holds that ran out. */
    void advance(long now) {
        if (now < this.now) throw new InventoryException(InventoryException.Code.BACKDATED, now + " < " + this.now);
        this.now = now;
        store.holds.expire(now, store);
    }

    /** Sets (or replaces) the replenishment rule for sku in warehouse. */
    public void setRule(String warehouse, String sku, Rule r) {
        checkWarehouse(warehouse);
        if (sku.isEmpty() || r.min() < 0 || r.max() <= r.min() || r.pack() < 0) {
            throw new InventoryException(InventoryException.Code.INVALID, "rule needs 0 <= min < max and pack >= 0");
        }
        store.rules.put(new StockKey(warehouse, sku), r);
    }

    /** Puts qty units of sku from a supplier delivery away into a bin. */
    public void receive(String warehouse, String bin, String sku, int qty, long now) {
        checkWarehouse(warehouse);
        if (bin.isEmpty() || sku.isEmpty() || qty <= 0) {
            throw new InventoryException(InventoryException.Code.INVALID, "receive needs a bin, a SKU and a positive quantity");
        }
        advance(now);
        store.putAway(new BinKey(warehouse, bin, sku), qty);
    }

    /** The physical quantity of sku on the warehouse's shelves. */
    public int onHand(String warehouse, String sku) {
        return store.onHand(new StockKey(warehouse, sku));
    }

    /** The quantity of sku in one bin. */
    public int binQty(String warehouse, String bin, String sku) {
        return store.bins.getOrDefault(new BinKey(warehouse, bin, sku), 0);
    }

    /** What can still be promised: on hand minus active reservations, at now. */
    public int available(String warehouse, String sku, long now) {
        checkWarehouse(warehouse);
        advance(now);
        return avail(new StockKey(warehouse, sku));
    }

    int avail(StockKey k) {
        return store.onHand(k) - store.reserved(k);
    }

    // Reservations (Reservations.java)

    /** Holds qty units of sku in warehouse for an order, for ttl seconds from now. */
    public Reservation reserve(String id, String warehouse, String sku, int qty, long ttl, long now) {
        return Reservations.reserve(this, id, warehouse, sku, qty, ttl, now);
    }

    /** Cancels a reservation and returns its stock to available. Releasing a hold that is already released or expired is a no-op. */
    public void release(String id, long now) {
        Reservations.release(this, id, now);
    }

    /** Picks a reservation's quantity from the warehouse's bins for shipping and ends the hold. */
    public void commit(String id, long now) {
        Reservations.commit(this, id, now);
    }

    /** A copy of a reservation, or null. */
    public Reservation reservation(String id) {
        Reservation r = store.reservations.get(id);
        return r == null ? null : r.copy();
    }

    // Transfers (Transfers.java)

    /** Ships qty units of sku from one warehouse to another; they count as inbound at the destination until received. */
    public Transfer startTransfer(String id, String from, String to, String sku, int qty, long now) {
        return Transfers.start(this, id, from, to, sku, qty, now);
    }

    /** Puts an arrived transfer away into a bin at its destination. */
    public void receiveTransfer(String id, String bin, long now) {
        Transfers.receive(this, id, bin, now);
    }

    /** The quantity of sku in transit toward warehouse. */
    public int inbound(String warehouse, String sku) {
        return store.inbound(new StockKey(warehouse, sku));
    }

    /** A copy of a transfer, or null. */
    public Transfer transfer(String id) {
        Transfer t = store.transfers.get(id);
        return t == null ? null : t.copy();
    }

    // Replenishment (Replenish.java)

    /** Plans restocking for one warehouse at time now. It only plans; nothing is moved or ordered. */
    public List<Suggestion> replenishment(String warehouse, long now) {
        return Replenish.plan(this, warehouse, now);
    }
}
