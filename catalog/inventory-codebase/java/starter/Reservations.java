final class Reservations {
    private Reservations() {}

    static Reservation reserve(Inventory s, String id, String warehouse, String sku, int qty, long ttl, long now) {
        s.checkWarehouse(warehouse);
        if (id.isEmpty() || qty <= 0 || ttl <= 0) {
            throw new InventoryException(InventoryException.Code.INVALID, "reserve needs an id, a positive quantity and ttl");
        }
        if (s.store.reservations.containsKey(id)) {
            throw new InventoryException(InventoryException.Code.DUPLICATE, "reservation " + id);
        }
        s.advance(now);
        StockKey k = new StockKey(warehouse, sku);
        int avail = s.avail(k);
        if (avail < qty) {
            throw new InventoryException(InventoryException.Code.INSUFFICIENT_STOCK, avail + " available, " + qty + " requested");
        }
        Reservation r = new Reservation(id, warehouse, sku, qty, now, now + ttl, ++s.seq);
        s.store.reservations.put(id, r);
        s.store.reserved.merge(k, qty, Integer::sum);
        s.store.holds.track(r);
        return r.copy();
    }

    static void release(Inventory s, String id, long now) {
        Reservation r = s.store.reservations.get(id);
        if (r == null) throw new InventoryException(InventoryException.Code.NOT_FOUND, "reservation " + id);
        switch (r.status) {
            case COMMITTED -> throw new InventoryException(InventoryException.Code.NOT_ACTIVE, "committed");
            case RELEASED, EXPIRED -> { return; }
            default -> { }
        }
        s.advance(now);
        s.store.endHold(r, Reservation.Status.RELEASED, now);
    }

    static void commit(Inventory s, String id, long now) {
        s.advance(now);
        Reservation r = s.store.reservations.get(id);
        if (r == null) throw new InventoryException(InventoryException.Code.NOT_FOUND, "reservation " + id);
        if (r.status != Reservation.Status.ACTIVE) {
            throw new InventoryException(InventoryException.Code.NOT_ACTIVE, r.status.name().toLowerCase());
        }
        s.store.pick(new StockKey(r.warehouse, r.sku), r.qty);
        s.store.endHold(r, Reservation.Status.COMMITTED, now);
    }
}
