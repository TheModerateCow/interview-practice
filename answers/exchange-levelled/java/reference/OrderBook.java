import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** The order book for one instrument: resting orders, queue priority, sweeps and limit orders matched by price and time. */
public class OrderBook {
    private static final class Order {
        final String id;
        final boolean sell;
        final int price;
        int left, filled;
        String state = "open";
        Order(String id, boolean sell, int price, int qty) { this.id = id; this.sell = sell; this.price = price; this.left = qty; }
    }

    private static final class Level {
        final LinkedHashMap<String, Order> queue = new LinkedHashMap<>(); // first in line first
        long shares;
    }

    /** One side of the book: price levels, best first. */
    private static final class Side {
        final TreeMap<Integer, Level> levels;
        final boolean desc;
        Side(boolean desc) { this.desc = desc; levels = desc ? new TreeMap<>(Collections.reverseOrder()) : new TreeMap<>(); }

        void add(Order o) {
            Level lv = levels.computeIfAbsent(o.price, p -> new Level());
            lv.queue.put(o.id, o);
            lv.shares += o.left;
        }

        void remove(Order o) {
            Level lv = levels.get(o.price);
            lv.queue.remove(o.id);
            lv.shares -= o.left;
            if (lv.queue.isEmpty()) levels.remove(o.price);
        }

        /** Fills up to qty from the best level on, stopping at levels worse than limit (if given). -> {shares, cost} */
        long[] take(long qty, Integer limit) {
            long got = 0, cost = 0;
            while (qty > 0 && !levels.isEmpty()) {
                Map.Entry<Integer, Level> best = levels.firstEntry();
                int p = best.getKey();
                if (limit != null && (desc ? p < limit : p > limit)) break;
                Level lv = best.getValue();
                Iterator<Order> it = lv.queue.values().iterator();
                while (qty > 0 && it.hasNext()) {
                    Order o = it.next();
                    int t = (int) Math.min(o.left, qty);
                    o.left -= t;
                    o.filled += t;
                    lv.shares -= t;
                    qty -= t;
                    got += t;
                    cost += (long) t * p;
                    if (o.left == 0) {
                        o.state = "filled";
                        it.remove();
                    }
                }
                if (lv.queue.isEmpty()) levels.remove(p);
            }
            return new long[] {got, cost};
        }
    }

    private final Map<String, Order> orders = new HashMap<>(); // every id ever used
    private final Side asks = new Side(false), bids = new Side(true);

    public OrderBook() {}

    private Side sideOf(Order o) { return o.sell ? asks : bids; }

    private Order resting(String id) {
        Order o = orders.get(id);
        return o != null && o.state.equals("open") ? o : null;
    }

    // ---- level 1 ----

    public boolean addOrder(String orderId, int price, int qty) {
        return submit(orderId, "sell", price, qty) != null;
    }

    public boolean cancelOrder(String orderId) {
        Order o = resting(orderId);
        if (o == null) return false;
        sideOf(o).remove(o);
        o.state = "cancelled";
        return true;
    }

    public Integer bestAsk() {
        return asks.levels.isEmpty() ? null : asks.levels.firstKey();
    }

    public long depthAt(int price) {
        Level a = asks.levels.get(price), b = bids.levels.get(price);
        return (a == null ? 0 : a.shares) + (b == null ? 0 : b.shares);
    }

    // ---- level 2 ----

    public boolean amendOrder(String orderId, int qty) {
        Order o = resting(orderId);
        if (o == null) return false;
        Side s = sideOf(o);
        if (qty > o.left) { // more shares: back of the queue
            s.remove(o);
            o.left = qty;
            s.add(o);
        } else {
            s.levels.get(o.price).shares -= o.left - qty;
            o.left = qty;
        }
        return true;
    }

    public List<String> queueAt(int price) {
        List<String> out = new ArrayList<>();
        Level lv = asks.levels.get(price);
        if (lv == null) lv = bids.levels.get(price);
        if (lv == null) return out;
        for (Order o : lv.queue.values()) out.add(o.id + ":" + o.left);
        return out;
    }

    public List<String> topLevels(int n) {
        List<String> out = new ArrayList<>();
        for (Map.Entry<Integer, Level> e : asks.levels.entrySet()) {
            if (out.size() >= n) break;
            out.add(e.getKey() + ":" + e.getValue().shares + ":" + e.getValue().queue.size());
        }
        return out;
    }

    // ---- level 3 ----

    public Long quoteBuy(long qty) {
        long cost = 0;
        for (Map.Entry<Integer, Level> e : asks.levels.entrySet()) {
            long t = Math.min(qty, e.getValue().shares);
            cost += t * e.getKey();
            qty -= t;
            if (qty == 0) return cost;
        }
        return null;
    }

    public long marketBuy(long qty) {
        return asks.take(qty, null)[1];
    }

    // ---- level 4 ----

    public Integer submit(String orderId, String side, int price, int qty) {
        if (orders.containsKey(orderId)) return null;
        Order o = new Order(orderId, side.equals("sell"), price, qty);
        orders.put(orderId, o);
        int got = (int) (o.sell ? bids : asks).take(qty, price)[0];
        o.left -= got;
        o.filled += got;
        if (o.left == 0) o.state = "filled";
        else sideOf(o).add(o);
        return got;
    }

    public Integer bestBid() {
        return bids.levels.isEmpty() ? null : bids.levels.firstKey();
    }

    public String orderStatus(String orderId) {
        Order o = orders.get(orderId);
        return o == null ? "" : o.state + ":" + o.filled;
    }
}
