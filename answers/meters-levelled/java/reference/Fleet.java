import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** A smart-meter platform's home-battery fleet: tariffs, recorded actions, daily reports and best-schedule planning. */
public class Fleet {
    private static final class DayLog {
        int profit, discharged;
    }

    private static final class Battery {
        final int capacity, wear;
        int stored, cash;
        boolean acted;
        int lastDay, lastSlot; // day and slot of the latest recorded action, when acted
        final Map<Integer, DayLog> days = new HashMap<>();
        int limit = -1; // kWh it may discharge per day; -1 = no limit
        Battery(int capacity, int wear) { this.capacity = capacity; this.wear = wear; }
    }

    private final Map<String, Battery> batteries = new HashMap<>();
    private final Map<Integer, int[]> tariffs = new HashMap<>();

    public Fleet() {}

    public boolean addBattery(String id, int capacity, int wear) {
        if (batteries.containsKey(id)) return false;
        batteries.put(id, new Battery(capacity, wear));
        return true;
    }

    public boolean publishTariff(int day, int[] prices) {
        if (tariffs.containsKey(day)) return false;
        tariffs.put(day, prices.clone());
        return true;
    }

    private Integer act(String id, int day, int slot, boolean charging) {
        Battery b = batteries.get(id);
        int[] prices = tariffs.get(day);
        if (b == null || prices == null || slot < 0 || slot >= prices.length) return null;
        if (b.acted && (day < b.lastDay || day == b.lastDay && slot <= b.lastSlot)) return null;
        DayLog d = b.days.getOrDefault(day, new DayLog());
        int gain;
        if (charging) {
            if (b.stored >= b.capacity) return null;
            b.stored++;
            gain = -prices[slot];
        } else {
            if (b.stored == 0 || (b.limit >= 0 && d.discharged >= b.limit)) return null;
            b.stored--;
            d.discharged++;
            gain = prices[slot] - b.wear;
        }
        b.cash += gain;
        d.profit += gain;
        b.days.put(day, d);
        b.acted = true;
        b.lastDay = day;
        b.lastSlot = slot;
        return b.stored;
    }

    public Integer charge(String id, int day, int slot) { return act(id, day, slot, true); }

    public Integer discharge(String id, int day, int slot) { return act(id, day, slot, false); }

    public Integer stored(String id) {
        Battery b = batteries.get(id);
        return b == null ? null : b.stored;
    }

    public Integer cash(String id) {
        Battery b = batteries.get(id);
        return b == null ? null : b.cash;
    }

    public Integer dayProfit(String id, int day) {
        Battery b = batteries.get(id);
        if (b == null) return null;
        DayLog d = b.days.get(day);
        return d == null ? 0 : d.profit;
    }

    public List<String> topEarners(int day, int n) {
        Map<String, Integer> profit = new HashMap<>();
        for (String id : batteries.keySet()) profit.put(id, dayProfit(id, day));
        List<String> ids = new ArrayList<>(profit.keySet());
        ids.sort((a, b) -> !profit.get(a).equals(profit.get(b)) ? Integer.compare(profit.get(b), profit.get(a)) : a.compareTo(b));
        List<String> out = new ArrayList<>();
        for (String id : ids.subList(0, Math.min(n, ids.size()))) out.add(id + ":" + profit.get(id));
        return out;
    }

    public Integer bestProfit(String id, int day) {
        Battery b = batteries.get(id);
        int[] prices = tariffs.get(day);
        if (b == null || prices == null) return null;
        int n = prices.length;
        int cap = Math.min(b.capacity, n);
        int lim = b.limit < 0 ? n : Math.min(b.limit, n);
        final long unreached = Long.MIN_VALUE / 4;
        // best[u][c]: most cash so far holding c kWh after u kWh discharged today.
        long[][] best = new long[lim + 1][cap + 1];
        for (long[] row : best) Arrays.fill(row, unreached);
        best[0][0] = 0;
        for (int p : prices) {
            long[][] nxt = new long[lim + 1][];
            for (int u = 0; u <= lim; u++) nxt[u] = best[u].clone(); // idle
            for (int u = 0; u <= lim; u++) {
                for (int c = 0; c <= cap; c++) {
                    long v = best[u][c];
                    if (v == unreached) continue;
                    if (c < cap && v - p > nxt[u][c + 1]) nxt[u][c + 1] = v - p;
                    if (c > 0 && u < lim && v + p - b.wear > nxt[u + 1][c - 1]) nxt[u + 1][c - 1] = v + p - b.wear;
                }
            }
            best = nxt;
        }
        long out = 0;
        for (long[] row : best) for (long v : row) out = Math.max(out, v);
        return (int) out;
    }

    public boolean setDischargeLimit(String id, int kwh) {
        Battery b = batteries.get(id);
        if (b == null) return false;
        b.limit = kwh;
        return true;
    }
}
