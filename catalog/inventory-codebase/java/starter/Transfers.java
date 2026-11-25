final class Transfers {
    private Transfers() {}

    static Transfer start(Inventory s, String id, String from, String to, String sku, int qty, long now) {
        s.checkWarehouse(from);
        s.checkWarehouse(to);
        if (id.isEmpty() || from.equals(to) || qty <= 0) {
            throw new InventoryException(InventoryException.Code.INVALID, "transfer needs an id, two warehouses and a positive quantity");
        }
        if (s.store.transfers.containsKey(id)) {
            throw new InventoryException(InventoryException.Code.DUPLICATE, "transfer " + id);
        }
        s.advance(now);
        StockKey src = new StockKey(from, sku);
        int avail = s.store.onHand(src);
        if (avail < qty) {
            throw new InventoryException(InventoryException.Code.INSUFFICIENT_STOCK, avail + " available at " + from + ", " + qty + " requested");
        }
        s.store.pick(src, qty);
        Transfer t = new Transfer(id, from, to, sku, qty, now);
        s.store.transfers.put(id, t);
        s.store.inbound.merge(new StockKey(to, sku), qty, Integer::sum);
        return t.copy();
    }

    static void receive(Inventory s, String id, String bin, long now) {
        if (bin.isEmpty()) throw new InventoryException(InventoryException.Code.INVALID, "empty bin");
        s.advance(now);
        Transfer t = s.store.transfers.get(id);
        if (t == null) throw new InventoryException(InventoryException.Code.NOT_FOUND, "transfer " + id);
        if (t.status != Transfer.Status.IN_TRANSIT) {
            throw new InventoryException(InventoryException.Code.TRANSFER_STATE, "");
        }
        s.store.inbound.merge(new StockKey(t.to, t.sku), -t.qty, Integer::sum);
        s.store.putAway(new BinKey(t.to, bin, t.sku), t.qty);
        t.status = Transfer.Status.RECEIVED;
        t.receivedAt = now;
        t.bin = bin;
    }
}
