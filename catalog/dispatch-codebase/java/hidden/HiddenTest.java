import java.util.ArrayList;
import java.util.List;

// The app compiles one phase's tests at a time: helpers use only phase-1 code (plus the Assignment record).
public class HiddenTest {
    static String hiddenCode(Runnable r) {
        try {
            r.run();
            return "ok";
        } catch (DispatchException e) {
            return e.code.name();
        }
    }

    static String hiddenAssignments(List<Assignment> as) {
        List<String> out = new ArrayList<>();
        for (Assignment a : as) out.add(a.orderId() + "->" + a.courierId());
        return out.toString();
    }

    static void hiddenTrip(Dispatcher d, String order) {
        d.advance(order, State.PICKED_UP);
        d.advance(order, State.DELIVERED);
    }

    // ---------------------------------------------------------------- phase 1

    static void test_p1_assign_nearest_with_room() {
        Dispatcher d = new Dispatcher();
        d.addCourier("a", new Point(0, 0), 1);
        d.addCourier("b", new Point(300, 0), 1);
        for (String id : new String[]{"o1", "o2", "o3"}) d.placeOrder(id, new Point(100, 0), new Point(100, 900), 0, 5);
        Expect.eq("a", d.assign("o1"));
        Expect.eq("b", d.assign("o2"));
        Expect.eq("NO_COURIER", hiddenCode(() -> d.assign("o3")));
        Expect.eq(State.PLACED, d.order("o3").state());
        Expect.eq("BAD_TRANSITION", hiddenCode(() -> d.assign("o1")));
        Expect.eq(State.ASSIGNED, d.order("o1").state());
        Expect.eq("a", d.order("o1").courierId());
    }

    static void test_p1_assign_ties_and_range() {
        Dispatcher d = new Dispatcher();
        d.addCourier("zed", new Point(0, 200), 1);
        d.addCourier("amy", new Point(200, 0), 1);
        d.addCourier("edge", new Point(4000, 0), 1);
        d.addCourier("gone", new Point(0, 4001), 1);
        for (String id : new String[]{"o1", "o2", "o3", "o4"}) d.placeOrder(id, new Point(0, 0), new Point(500, 500), 0, 0);
        Expect.eq("amy", d.assign("o1"));    // tie goes to the lower id
        Expect.eq("zed", d.assign("o2"));    // then the other tied courier
        Expect.eq("edge", d.assign("o3"));   // exactly MAX_PICKUP_DISTANCE away is in range
        Expect.eq("NO_COURIER", hiddenCode(() -> d.assign("o4")));  // only an out-of-range courier left
    }

    static void test_p1_lifecycle_rules() {
        Dispatcher d = new Dispatcher();
        d.addCourier("c1", new Point(0, 0), 1);
        d.placeOrder("o1", new Point(0, 0), new Point(250, 0), 0, 0);
        Expect.eq("BAD_TRANSITION", hiddenCode(() -> d.advance("o1", State.DELIVERED)));
        Expect.eq("BAD_TRANSITION", hiddenCode(() -> d.advance("o1", State.ASSIGNED)));
        d.assign("o1");
        Expect.eq("BAD_TRANSITION", hiddenCode(() -> d.advance("o1", State.DELIVERED)));
        Expect.eq("ok", hiddenCode(() -> d.advance("o1", State.PICKED_UP)));
        Expect.eq("BAD_TRANSITION", hiddenCode(() -> d.advance("o1", State.CANCELLED)));
        Expect.eq("ok", hiddenCode(() -> d.advance("o1", State.DELIVERED)));
        Expect.eq("BAD_TRANSITION", hiddenCode(() -> d.advance("o1", State.DELIVERED)));
        Expect.eq("UNKNOWN_ORDER", hiddenCode(() -> d.advance("nope", State.PICKED_UP)));
        Expect.eq("INVALID_COURIER", hiddenCode(() -> d.addCourier("c2", new Point(0, 0), 0)));
        Expect.eq("DUPLICATE_COURIER", hiddenCode(() -> d.addCourier("c1", new Point(0, 0), 3)));
    }

    static void test_p1_delivery_frees_courier_and_moves_them() {
        Dispatcher d = new Dispatcher();
        d.addCourier("c1", new Point(0, 0), 1);
        d.addCourier("c2", new Point(1000, 0), 1);
        d.placeOrder("o1", new Point(0, 0), new Point(2000, 0), 0, 0);
        d.assign("o1");
        hiddenTrip(d, "o1");
        d.placeOrder("o2", new Point(2000, 100), new Point(0, 0), 5, 5);
        Expect.eq("c1", d.assign("o2"));  // free again, and now at the last customer
        Expect.eq("[o2]", d.courierOrders("c1").toString());
    }

    static void test_p1_eta_rounds_each_leg_up() {
        Dispatcher d = new Dispatcher();
        d.addCourier("c1", new Point(0, 0), 2);
        d.placeOrder("o1", new Point(600, 0), new Point(600, 1100), 0, 0);
        d.assign("o1");
        Expect.eq(8, d.eta("o1", 0));  // 600 m + 1100 m
        Expect.eq(1, Geo.travelMinutes(1));
        Expect.eq(2, Geo.travelMinutes(500));
        Expect.eq(3, Geo.travelMinutes(501));
        Expect.eq(0, Geo.travelMinutes(0));
    }

    static void test_p1_eta_waits_for_kitchen() {
        Dispatcher d = new Dispatcher();
        d.addCourier("c1", new Point(0, 0), 2);
        d.placeOrder("o2", new Point(0, 700), new Point(700, 700), 5, 15);
        d.assign("o2");
        Expect.eq(18, d.eta("o2", 5));  // food is ready after the courier arrives
    }

    static void test_p1_eta_after_pickup() {
        Dispatcher d = new Dispatcher();
        d.addCourier("c1", new Point(0, 0), 2);
        d.placeOrder("o1", new Point(600, 0), new Point(600, 1100), 0, 0);
        d.assign("o1");
        d.advance("o1", State.PICKED_UP);
        Expect.eq(5, d.eta("o1", 9));  // from the restaurant to the door
        d.advance("o1", State.DELIVERED);
        Expect.eq("ORDER_CLOSED", hiddenCode(() -> d.eta("o1", 12)));
        d.placeOrder("o3", new Point(0, 0), new Point(0, 10), 12, 0);
        Expect.eq("NOT_ASSIGNED", hiddenCode(() -> d.eta("o3", 12)));
    }

    static void test_p1_cancel_frees_courier() {
        Dispatcher d = new Dispatcher();
        d.addCourier("solo", new Point(0, 0), 1);
        d.placeOrder("o1", new Point(100, 100), new Point(900, 900), 0, 5);
        d.placeOrder("o2", new Point(100, 100), new Point(800, 800), 1, 5);
        d.assign("o1");
        Expect.eq("ok", hiddenCode(() -> d.advance("o1", State.CANCELLED)));
        Expect.eq("solo", d.assign("o2"));
    }

    static void test_p1_cancelled_order_leaves_bag() {
        Dispatcher d = new Dispatcher();
        d.addCourier("c1", new Point(0, 0), 3);
        d.placeOrder("o1", new Point(0, 0), new Point(900, 0), 0, 5);
        d.placeOrder("o2", new Point(0, 0), new Point(0, 900), 0, 5);
        d.assign("o1");
        d.assign("o2");
        d.advance("o1", State.CANCELLED);
        Expect.eq("[o2]", d.courierOrders("c1").toString());
    }

    static void test_p1_duplicate_order_keeps_assignment() {
        Dispatcher d = new Dispatcher();
        d.addCourier("c1", new Point(0, 0), 1);
        d.addCourier("c2", new Point(3000, 0), 1);
        d.placeOrder("o1", new Point(0, 0), new Point(900, 0), 0, 5);
        d.assign("o1");
        Expect.eq("DUPLICATE_ORDER", hiddenCode(() -> d.placeOrder("o1", new Point(3000, 0), new Point(900, 0), 2, 5)));
        Order o = d.order("o1");
        Expect.eq(State.ASSIGNED, o.state());
        Expect.eq("c1", o.courierId());
        Expect.eq(new Point(0, 0), o.restaurant());
        Expect.eq("BAD_TRANSITION", hiddenCode(() -> d.assign("o1")));
    }

    static void test_p1_duplicate_pending_order_unchanged() {
        Dispatcher d = new Dispatcher();
        d.placeOrder("o9", new Point(10, 10), new Point(20, 20), 3, 10);
        Expect.eq("DUPLICATE_ORDER", hiddenCode(() -> d.placeOrder("o9", new Point(50, 50), new Point(60, 60), 4, 2)));
        Order o = d.order("o9");
        Expect.eq(3, o.placedAt());
        Expect.eq(10, o.prepMinutes());
    }

    // ---------------------------------------------------------------- phase 2

    static void test_p2_hands_out_due_orders() {
        Dispatcher d = new Dispatcher();
        d.addCourier("north", new Point(0, 3000), 2);
        d.addCourier("south", new Point(0, 0), 2);
        d.placeOrder("n1", new Point(0, 2900), new Point(500, 2900), 0, 5);
        d.placeOrder("s1", new Point(100, 0), new Point(500, 0), 0, 8);
        Expect.eq("[n1->north, s1->south]", hiddenAssignments(d.dispatchPending(0)));
        Expect.eq(State.ASSIGNED, d.order("n1").state());
        Expect.eq("south", d.order("s1").courierId());
        Expect.eq(0, d.dispatchPending(1).size());
    }

    static void test_p2_ready_soonest_first() {
        Dispatcher d = new Dispatcher();
        d.addCourier("solo", new Point(0, 0), 1);
        d.placeOrder("early", new Point(0, 0), new Point(500, 0), 0, 20);
        d.placeOrder("late", new Point(0, 0), new Point(0, 500), 5, 5);
        Expect.eq("[late->solo]", hiddenAssignments(d.dispatchPending(10)));  // food ready first goes first
        Expect.eq(State.PLACED, d.order("early").state());
    }

    static void test_p2_ready_ties_by_order_id() {
        Dispatcher d = new Dispatcher();
        d.addCourier("solo", new Point(0, 0), 1);
        d.placeOrder("o-b", new Point(0, 0), new Point(500, 0), 0, 10);
        d.placeOrder("o-a", new Point(0, 0), new Point(0, 500), 5, 5);
        Expect.eq("[o-a->solo]", hiddenAssignments(d.dispatchPending(3)));  // same ready minute, lower id first
    }

    static void test_p2_dispatch_window() {
        Dispatcher d = new Dispatcher();
        d.addCourier("c1", new Point(0, 0), 5);
        d.placeOrder("in10", new Point(0, 0), new Point(100, 0), 0, 10);
        d.placeOrder("in11", new Point(0, 0), new Point(200, 0), 0, 11);
        d.placeOrder("ready", new Point(0, 0), new Point(300, 0), 0, 0);
        Expect.eq("[ready->c1, in10->c1]", hiddenAssignments(d.dispatchPending(0)));
        Expect.eq(State.PLACED, d.order("in11").state());
        Expect.eq("[in11->c1]", hiddenAssignments(d.dispatchPending(1)));
    }

    static void test_p2_capacity_spills_to_next_courier() {
        Dispatcher d = new Dispatcher();
        d.addCourier("near", new Point(50, 0), 1);
        d.addCourier("far", new Point(900, 0), 2);
        d.addCourier("farther", new Point(1500, 0), 4);
        for (int i = 1; i <= 4; i++) d.placeOrder("o" + i, new Point(0, 0), new Point(0, 800), i, 0);
        Expect.eq("[o1->near, o2->far, o3->far, o4->farther]", hiddenAssignments(d.dispatchPending(5)));
        Expect.eq("[o2, o3]", d.courierOrders("far").toString());
    }

    static void test_p2_unreachable_and_finished_orders() {
        Dispatcher d = new Dispatcher();
        d.addCourier("away", new Point(5000, 0), 3);
        d.placeOrder("o1", new Point(0, 0), new Point(100, 0), 0, 0);
        d.placeOrder("o2", new Point(4900, 0), new Point(4800, 0), 0, 0);
        d.placeOrder("o3", new Point(4900, 0), new Point(4700, 0), 0, 0);
        d.placeOrder("o4", new Point(4900, 0), new Point(4600, 0), 0, 0);
        d.assign("o2");
        d.advance("o3", State.CANCELLED);
        Expect.eq("[o4->away]", hiddenAssignments(d.dispatchPending(1)));  // only o4 is reachable and waiting
        Expect.eq(State.PLACED, d.order("o1").state());
        Expect.eq(State.CANCELLED, d.order("o3").state());
        d.addCourier("home", new Point(0, 300), 1);
        Expect.eq("[o1->home]", hiddenAssignments(d.dispatchPending(2)));
        List<Assignment> got = d.dispatchPending(3);
        Expect.isTrue(got != null && got.isEmpty(), "nothing to do: expected an empty list, got " + got);
    }

    // ---------------------------------------------------------------- phase 3

    /**
     * A dinner-rush zone: nc couriers (capacity 10 each) and 10*nc orders spread over a 2 km square,
     * placed over the first hours of the shift.
     */
    static Dispatcher hiddenRush(int nc) {
        Dispatcher d = new Dispatcher();
        int[] seed = {12345};
        java.util.function.IntUnaryOperator rnd = n -> {
            seed[0] = seed[0] * 1664525 + 1013904223;
            return (seed[0] >>> 8) % n;
        };
        for (int i = 0; i < nc; i++) d.addCourier("c" + i, new Point(rnd.applyAsInt(2000), rnd.applyAsInt(2000)), 10);
        for (int i = 0; i < nc * 10; i++) {
            Point r = new Point(rnd.applyAsInt(2000), rnd.applyAsInt(2000));
            Point c = new Point(rnd.applyAsInt(2000), rnd.applyAsInt(2000));
            d.placeOrder("o" + i, r, c, i / 20, 5 + rnd.applyAsInt(11));
        }
        return d;
    }

    static void test_p3_dinner_rush_dispatch() {
        Dispatcher d = hiddenRush(280);
        long start = System.nanoTime();
        List<Assignment> got = d.dispatchPending(200);
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.eq(2800, got.size());
        Expect.eq(new Assignment("o12", "c48"), got.get(0));
        Expect.eq(new Assignment("o1486", "c33"), got.get(1399));
        Expect.eq(new Assignment("o2792", "c223"), got.get(2799));
        Expect.isTrue(ms < hiddenBudgetMs, "dispatchPending of 2800 orders took " + ms + " ms, budget " + hiddenBudgetMs + " ms");
    }

    static void test_p3_dinner_rush_manual_assign() {
        Dispatcher d = hiddenRush(280);
        long start = System.nanoTime();
        String last = "";
        for (int i = 0; i < 2800; i++) last = d.assign("o" + i);
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.eq("c223", last);
        Expect.eq("[o1264, o1760, o1995, o2006, o2118, o2130, o2151, o2168, o2194, o2214]", d.courierOrders("c0").toString());
        Expect.isTrue(ms < hiddenBudgetMs, "2800 assign calls took " + ms + " ms, budget " + hiddenBudgetMs + " ms");
    }

    static final long hiddenBudgetMs = 1000;
}
