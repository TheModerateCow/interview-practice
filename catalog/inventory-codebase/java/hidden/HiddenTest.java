import java.util.List;

// The app compiles one phase's tests at a time: helpers use only phase-1 code.
public class HiddenTest {
    static String hiddenCode(Runnable r) {
        try {
            r.run();
            return "ok";
        } catch (InventoryException e) {
            return e.code.name();
        }
    }

    static Inventory hiddenService(String... warehouses) {
        Inventory s = new Inventory();
        for (String w : warehouses) s.addWarehouse(w);
        return s;
    }

    static void hiddenReserve(Inventory s, String id, String w, String sku, int qty, long ttl, long now) {
        s.reserve(id, w, sku, qty, ttl, now);
    }

    static String hiddenStatus(Inventory s, String id) {
        Reservation r = s.reservation(id);
        if (r == null) throw new AssertionError("reservation " + id + " not found");
        return r.status().name().toLowerCase() + "@" + r.updatedAt();
    }

    static String hiddenPlan(List<Suggestion> ps) {
        StringBuilder b = new StringBuilder("[");
        for (Suggestion p : ps) {
            if (b.length() > 1) b.append(' ');
            b.append("{SKU:").append(p.sku()).append(" Position:").append(p.position())
                    .append(" Qty:").append(p.qty()).append(" From:").append(p.from()).append('}');
        }
        return b.append(']').toString();
    }

    static String hiddenTransfer(Transfer t) {
        return "{ID:" + t.id() + " From:" + t.from() + " To:" + t.to() + " SKU:" + t.sku() + " Qty:" + t.qty()
                + " Status:" + t.status().name().toLowerCase() + " ShippedAt:" + t.shippedAt()
                + " ReceivedAt:" + t.receivedAt() + " Bin:" + t.bin() + "}";
    }

    // ---------------------------------------------------------------- phase 1

    static void test_p1_release_after_hold_ran_out_returns_stock_once() {
        Inventory s = hiddenService("east");
        s.receive("east", "A-01", "LAMP", 10, 100);
        hiddenReserve(s, "o1", "east", "LAMP", 6, 600, 200); // runs out at 800
        Expect.eq(4, s.available("east", "LAMP", 799));
        s.release("o1", 900); // the order service cancels late
        Expect.eq("expired@800", hiddenStatus(s, "o1"));
        Expect.eq(10, s.available("east", "LAMP", 900));
        Expect.eq("INSUFFICIENT_STOCK", hiddenCode(() -> s.reserve("o2", "east", "LAMP", 11, 600, 910)));
        hiddenReserve(s, "o3", "east", "LAMP", 10, 600, 920);
        s.commit("o3", 930);
        Expect.eq(0, s.onHand("east", "LAMP"));
        Expect.eq(0, s.available("east", "LAMP", 940));
    }

    static void test_p1_late_release_after_hold_ran_out_at_exact_second() {
        Inventory s = hiddenService("east");
        s.receive("east", "A-01", "LAMP", 5, 0);
        hiddenReserve(s, "o1", "east", "LAMP", 3, 60, 10); // runs out at 70
        hiddenReserve(s, "o2", "east", "LAMP", 2, 600, 20);
        s.release("o1", 70);
        s.release("o1", 71); // retried
        Expect.eq("expired@70", hiddenStatus(s, "o1"));
        Expect.eq(3, s.available("east", "LAMP", 72));
        Expect.eq("INSUFFICIENT_STOCK", hiddenCode(() -> s.reserve("o3", "east", "LAMP", 4, 60, 80)));
    }

    static void test_p1_release_and_commit_lifecycle() {
        Inventory s = hiddenService("east");
        s.receive("east", "A-01", "KETTLE", 8, 0);
        hiddenReserve(s, "o1", "east", "KETTLE", 3, 300, 10);
        hiddenReserve(s, "o2", "east", "KETTLE", 4, 300, 20);
        s.release("o1", 30);
        s.release("o1", 40); // retry is a no-op
        Expect.eq("released@30", hiddenStatus(s, "o1"));
        Expect.eq(4, s.available("east", "KETTLE", 40));
        s.commit("o2", 50);
        Expect.eq("committed@50", hiddenStatus(s, "o2"));
        Expect.eq(4, s.onHand("east", "KETTLE"));
        Expect.eq(4, s.available("east", "KETTLE", 60));
        Expect.eq("NOT_ACTIVE", hiddenCode(() -> s.release("o2", 70)));
        Expect.eq("NOT_ACTIVE", hiddenCode(() -> s.commit("o1", 70)));
        Expect.eq("NOT_ACTIVE", hiddenCode(() -> s.commit("o2", 70)));
        Expect.eq("NOT_FOUND", hiddenCode(() -> s.release("nope", 70)));
        hiddenReserve(s, "o3", "east", "KETTLE", 4, 100, 80);
        Expect.eq("NOT_ACTIVE", hiddenCode(() -> s.commit("o3", 180)));
        Expect.eq("expired@180", hiddenStatus(s, "o3"));
        Expect.eq(4, s.onHand("east", "KETTLE"));
    }

    static void test_p1_pick_finds_bins_put_away_after_an_earlier_pick() {
        Inventory s = hiddenService("east");
        s.receive("east", "B-02", "TOWEL", 4, 0);
        hiddenReserve(s, "o1", "east", "TOWEL", 3, 600, 10);
        s.commit("o1", 20); // B-02 now holds 1
        s.receive("east", "A-09", "TOWEL", 6, 30);
        s.receive("east", "C-01", "TOWEL", 5, 31);
        Expect.eq(12, s.onHand("east", "TOWEL"));
        hiddenReserve(s, "o2", "east", "TOWEL", 9, 600, 40);
        s.commit("o2", 50);
        Expect.eq(0, s.binQty("east", "A-09", "TOWEL"));
        Expect.eq(0, s.binQty("east", "B-02", "TOWEL"));
        Expect.eq(3, s.binQty("east", "C-01", "TOWEL"));
        Expect.eq(3, s.onHand("east", "TOWEL"));
    }

    static void test_p1_transfer_arrival_into_new_bin_is_pickable() {
        Inventory s = hiddenService("east", "west");
        s.receive("west", "W-1", "RUG", 20, 0);
        s.receive("east", "E-5", "RUG", 2, 0);
        hiddenReserve(s, "o1", "east", "RUG", 2, 600, 10);
        s.commit("o1", 20);
        s.startTransfer("t1", "west", "east", "RUG", 7, 30);
        s.receiveTransfer("t1", "E-1", 40);
        hiddenReserve(s, "o2", "east", "RUG", 7, 600, 50);
        s.commit("o2", 60);
        Expect.eq(0, s.binQty("east", "E-1", "RUG"));
        Expect.eq(0, s.onHand("east", "RUG"));
    }

    static void test_p1_pick_order_and_short_pick() {
        Inventory s = hiddenService("east");
        s.receive("east", "C-03", "CUP", 5, 0);
        s.receive("east", "A-10", "CUP", 2, 0);
        s.receive("east", "A-02", "CUP", 3, 0);
        s.receive("east", "A-02", "BOWL", 9, 0);
        hiddenReserve(s, "o1", "east", "CUP", 4, 600, 10);
        s.commit("o1", 20);
        Expect.eq(0, s.binQty("east", "A-02", "CUP"));
        Expect.eq(1, s.binQty("east", "A-10", "CUP"));
        Expect.eq(5, s.binQty("east", "C-03", "CUP"));
        Expect.eq(9, s.binQty("east", "A-02", "BOWL"));
        Expect.eq(6, s.available("east", "CUP", 30));
    }

    static void test_p1_transfer_cannot_take_reserved_stock() {
        Inventory s = hiddenService("east", "west");
        s.receive("east", "A-01", "CHAIR", 10, 0);
        hiddenReserve(s, "o1", "east", "CHAIR", 8, 3600, 10);
        Expect.eq("INSUFFICIENT_STOCK", hiddenCode(() -> s.startTransfer("t1", "east", "west", "CHAIR", 5, 20)));
        Expect.eq(null, s.transfer("t1"));
        Expect.eq(0, s.inbound("west", "CHAIR"));
        Expect.eq(10, s.onHand("east", "CHAIR"));
        Transfer tr = s.startTransfer("t2", "east", "west", "CHAIR", 2, 30);
        Expect.eq("{ID:t2 From:east To:west SKU:CHAIR Qty:2 Status:in_transit ShippedAt:30 ReceivedAt:0 Bin:}", hiddenTransfer(tr));
        Expect.eq(0, s.available("east", "CHAIR", 40));
        s.commit("o1", 50);
        Expect.eq(0, s.onHand("east", "CHAIR"));
    }

    static void test_p1_transfer_lifecycle() {
        Inventory s = hiddenService("east", "west");
        s.receive("east", "A-01", "DESK", 6, 0);
        Expect.eq("INVALID", hiddenCode(() -> s.startTransfer("t1", "east", "east", "DESK", 1, 10)));
        Expect.eq("UNKNOWN_WAREHOUSE", hiddenCode(() -> s.startTransfer("t1", "east", "south", "DESK", 1, 10)));
        Expect.eq("INSUFFICIENT_STOCK", hiddenCode(() -> s.startTransfer("t1", "east", "west", "DESK", 7, 10)));
        s.startTransfer("t1", "east", "west", "DESK", 4, 10);
        Expect.eq("DUPLICATE", hiddenCode(() -> s.startTransfer("t1", "east", "west", "DESK", 1, 11)));
        Expect.eq(4, s.inbound("west", "DESK"));
        Expect.eq(0, s.onHand("west", "DESK"));
        s.receiveTransfer("t1", "Z-9", 20);
        Expect.eq("TRANSFER_STATE", hiddenCode(() -> s.receiveTransfer("t1", "Z-9", 21)));
        Expect.eq(0, s.inbound("west", "DESK"));
        Expect.eq(4, s.binQty("west", "Z-9", "DESK"));
        Expect.eq(2, s.onHand("east", "DESK"));
        Expect.eq("{ID:t1 From:east To:west SKU:DESK Qty:4 Status:received ShippedAt:10 ReceivedAt:20 Bin:Z-9}",
                hiddenTransfer(s.transfer("t1")));
    }

    static void test_p1_validation_and_clock() {
        Inventory s = hiddenService("east");
        Expect.eq("DUPLICATE", hiddenCode(() -> s.addWarehouse("east")));
        Expect.eq("INVALID", hiddenCode(() -> s.receive("east", "A-01", "PEN", 0, 1)));
        Expect.eq("UNKNOWN_WAREHOUSE", hiddenCode(() -> s.receive("west", "A-01", "PEN", 1, 1)));
        s.receive("east", "A-01", "PEN", 3, 100);
        Expect.eq("BACKDATED", hiddenCode(() -> s.receive("east", "A-01", "PEN", 1, 99)));
        Expect.eq("INVALID", hiddenCode(() -> s.reserve("o1", "east", "PEN", 1, 0, 100)));
        Expect.eq("INSUFFICIENT_STOCK", hiddenCode(() -> s.reserve("o1", "east", "PEN", 4, 60, 100)));
        Reservation r = s.reserve("o1", "east", "PEN", 3, 60, 100);
        Expect.eq("east PEN 3 100..160 active",
                r.warehouse() + " " + r.sku() + " " + r.qty() + " " + r.createdAt() + ".." + r.expiresAt() + " " + r.status().name().toLowerCase());
        Expect.eq("DUPLICATE", hiddenCode(() -> s.reserve("o1", "east", "PEN", 1, 60, 101)));
        Expect.eq("BACKDATED", hiddenCode(() -> s.release("o1", 50)));
        Expect.eq(0, s.available("east", "PEN", 159));
        Expect.eq(3, s.available("east", "PEN", 160));
        Expect.eq("BACKDATED", hiddenCode(() -> s.available("east", "PEN", 10)));
    }

    // ---------------------------------------------------------------- phase 2

    static void test_p2_reorders_up_to_max_at_or_below_min() {
        Inventory s = hiddenService("east");
        s.receive("east", "A-01", "SOAP", 10, 0);
        s.receive("east", "A-02", "SALT", 11, 0);
        s.receive("east", "A-03", "OIL", 3, 0);
        s.setRule("east", "SOAP", new Rule(10, 50, 0));
        s.setRule("east", "SALT", new Rule(10, 50, 0));
        s.setRule("east", "OIL", new Rule(5, 12, 1));
        s.setRule("east", "FLOUR", new Rule(0, 20, 0));
        Expect.eq("[{SKU:FLOUR Position:0 Qty:20 From:} {SKU:OIL Position:3 Qty:9 From:} {SKU:SOAP Position:10 Qty:40 From:}]",
                hiddenPlan(s.replenishment("east", 10)));
        Expect.eq(10, s.onHand("east", "SOAP"));
        Expect.eq(3, s.replenishment("east", 20).size());
    }

    static void test_p2_case_packs_round_up() {
        Inventory s = hiddenService("east");
        s.receive("east", "A-01", "TEA", 7, 0);
        s.receive("east", "A-01", "JAM", 2, 0);
        s.setRule("east", "TEA", new Rule(8, 30, 12));
        s.setRule("east", "JAM", new Rule(4, 26, 6));
        Expect.eq("[{SKU:JAM Position:2 Qty:24 From:} {SKU:TEA Position:7 Qty:24 From:}]", hiddenPlan(s.replenishment("east", 10)));
    }

    static void test_p2_active_holds_reduce_position() {
        Inventory s = hiddenService("east");
        s.receive("east", "A-01", "SOCK", 30, 0);
        s.setRule("east", "SOCK", new Rule(20, 40, 5));
        hiddenReserve(s, "o1", "east", "SOCK", 6, 100, 10); // runs out at 110
        hiddenReserve(s, "o2", "east", "SOCK", 5, 500, 20);
        hiddenReserve(s, "o3", "east", "SOCK", 2, 500, 30);
        s.release("o3", 40);
        Expect.eq("[{SKU:SOCK Position:19 Qty:25 From:}]", hiddenPlan(s.replenishment("east", 109)));
        Expect.eq("[]", hiddenPlan(s.replenishment("east", 110)));
        s.commit("o2", 120);
        Expect.eq("[]", hiddenPlan(s.replenishment("east", 130)));
        hiddenReserve(s, "o4", "east", "SOCK", 6, 500, 140);
        Expect.eq("[{SKU:SOCK Position:19 Qty:25 From:}]", hiddenPlan(s.replenishment("east", 150)));
    }

    static void test_p2_inbound_transfers_count_once() {
        Inventory s = hiddenService("east", "west");
        s.receive("east", "A-01", "BOOT", 4, 0);
        s.receive("west", "W-01", "BOOT", 45, 0);
        s.setRule("east", "BOOT", new Rule(10, 30, 0));
        s.setRule("west", "BOOT", new Rule(15, 60, 0));
        Expect.eq("[{SKU:BOOT Position:4 Qty:26 From:west}]", hiddenPlan(s.replenishment("east", 10)));
        s.startTransfer("t1", "west", "east", "BOOT", 5, 20);
        Expect.eq("[{SKU:BOOT Position:9 Qty:21 From:west}]", hiddenPlan(s.replenishment("east", 30)));
        Expect.eq("[]", hiddenPlan(s.replenishment("west", 30)));
        s.receiveTransfer("t1", "A-02", 40);
        Expect.eq("[{SKU:BOOT Position:9 Qty:21 From:west}]", hiddenPlan(s.replenishment("east", 50)));
        s.startTransfer("t2", "west", "east", "BOOT", 2, 60);
        Expect.eq("[]", hiddenPlan(s.replenishment("east", 70)));
    }

    static void test_p2_source_is_largest_surplus_over_its_min() {
        Inventory s = hiddenService("north", "east", "west", "south");
        s.setRule("north", "BIKE", new Rule(5, 25, 0));
        s.receive("east", "A", "BIKE", 40, 0);
        s.setRule("east", "BIKE", new Rule(30, 60, 0)); // surplus 10
        s.receive("west", "A", "BIKE", 30, 0);          // no rule: surplus 30
        s.receive("south", "A", "BIKE", 34, 0);
        hiddenReserve(s, "o1", "south", "BIKE", 4, 1000, 1); // surplus 30
        Expect.eq("[{SKU:BIKE Position:0 Qty:25 From:south}]", hiddenPlan(s.replenishment("north", 10))); // tie goes to lowest id
        s.release("o1", 20);
        Expect.eq("[{SKU:BIKE Position:0 Qty:25 From:south}]", hiddenPlan(s.replenishment("north", 30))); // south grows
        hiddenReserve(s, "o2", "south", "BIKE", 11, 1000, 40);
        hiddenReserve(s, "o3", "west", "BIKE", 6, 1000, 40);
        Expect.eq("[{SKU:BIKE Position:0 Qty:25 From:}]", hiddenPlan(s.replenishment("north", 50))); // nobody can spare 25
        s.receive("north", "N", "BIKE", 3, 60);
        Expect.eq("[{SKU:BIKE Position:3 Qty:22 From:west}]", hiddenPlan(s.replenishment("north", 70))); // smaller need
        hiddenReserve(s, "o4", "west", "BIKE", 2, 1000, 80);
        hiddenReserve(s, "o5", "south", "BIKE", 2, 1000, 80);
        Expect.eq("[{SKU:BIKE Position:3 Qty:22 From:west}]", hiddenPlan(s.replenishment("north", 90))); // exactly enough
    }

    static void test_p2_errors_and_empty_plans() {
        Inventory s = hiddenService("east", "west");
        Expect.eq("UNKNOWN_WAREHOUSE", hiddenCode(() -> s.replenishment("south", 10)));
        Expect.eq(0, s.replenishment("east", 10).size());
        s.setRule("west", "CAP", new Rule(1, 9, 0));
        Expect.eq(0, s.replenishment("east", 20).size()); // other warehouse's rule
        Expect.eq("BACKDATED", hiddenCode(() -> s.replenishment("west", 5)));
        Expect.eq("INVALID", hiddenCode(() -> s.setRule("east", "CAP", new Rule(5, 5, 0))));
        Expect.eq("[{SKU:CAP Position:0 Qty:9 From:}]", hiddenPlan(s.replenishment("west", 30)));
    }

    // ---------------------------------------------------------------- phase 3

    static void test_p3_flash_sale_at_scale() {
        Inventory s = hiddenService("main", "overflow");
        final int skus = 20, n = 80000;
        java.util.function.IntFunction<String> sku = i -> "SKU-" + (i % skus);
        for (int i = 0; i < skus; i++) {
            s.receive("main", "A-" + i, sku.apply(i), 400, 0);
            s.receive("overflow", "Z-" + i, sku.apply(i), 3000, 0);
            s.setRule("main", sku.apply(i), new Rule(1200, 2400, 100));
        }
        int soldOut = 0, committed = 0, notActive = 0, fromOverflow = 0, restocked = 0;
        long start = System.nanoTime();
        for (int i = 0; i < n; i++) {
            long now = 1 + i;
            int qty = 1 + i % 5;
            // The product page checks stock, then checkout holds it: card payments for
            // 15 minutes, bank transfers and pre-orders for up to 12 hours.
            if (s.available("main", sku.apply(i), now) < qty) {
                soldOut++;
            } else {
                s.reserve("o" + i, "main", sku.apply(i), qty, 900 + ((long) i * 7919) % 42300, now);
            }
            if (i % 3 == 0 && i >= 5) {
                try {
                    s.commit("o" + (i - 5), now);
                    committed++;
                } catch (InventoryException e) {
                    notActive++;
                }
            }
            if (i % 5 == 0 && i >= 2) {
                try {
                    s.release("o" + (i - 2), now);
                } catch (InventoryException e) {
                    if (e.code != InventoryException.Code.NOT_FOUND) throw e;
                }
            }
            if (i % 4000 == 3999) {
                for (Suggestion sg : s.replenishment("main", now)) {
                    if (!sg.from().isEmpty()) fromOverflow++;
                    s.receive("main", "A-" + sg.sku().substring(4), sg.sku(), sg.qty(), now);
                    restocked += sg.qty();
                }
            }
        }
        long ms = (System.nanoTime() - start) / 1_000_000;
        int total = 0;
        for (int i = 0; i < skus; i++) total += s.available("main", sku.apply(i), n + 1);
        Expect.eq("soldOut=724 committed=21090 notActive=5575 fromOverflow=72 restocked=120900 available=38943 onhand=4461",
                "soldOut=" + soldOut + " committed=" + committed + " notActive=" + notActive + " fromOverflow=" + fromOverflow
                        + " restocked=" + restocked + " available=" + total + " onhand=" + s.onHand("main", sku.apply(7)));
        Expect.isTrue(ms < 2400, "too slow: " + n + " checkouts took " + ms + " ms (budget 2400 ms)");
    }
}
