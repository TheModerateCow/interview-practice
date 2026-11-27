import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * The core of a multi-currency wallet app: balances per currency, published exchange rates with a fee,
 * rate history with expiry, and standing conversion orders. Every method takes ts first, the time of the
 * call. Timestamps never decrease.
 */
public class Wallets {
    static final long SCALE = 1_000_000L; // a rate of 920_000 means 1 minor unit of source buys 0.92 of target
    static final long FEE_PERCENT = 1;
    static final int RATE_TTL = 100; // a rate published at t is in force until t + RATE_TTL (exclusive)

    record Published(int ts, long rate) {}

    static final class Order {
        String wallet, source, target, status = "open";
        long amount, minRate;
    }

    private final Map<String, Map<String, Long>> wallets = new HashMap<>();
    private final Map<String, List<Published>> rates = new HashMap<>(); // "SRC>TGT" -> oldest first
    private final Map<String, Order> orders = new LinkedHashMap<>(); // keeps creation order

    public Wallets() {}

    static boolean isCode(String c) {
        if (c.length() != 3) return false;
        for (int i = 0; i < 3; i++) {
            char ch = c.charAt(i);
            if (ch < 'A' || ch > 'Z') return false;
        }
        return true;
    }

    private long rateAt(String source, String target, int atTs) {
        long rate = -1;
        for (Published p : rates.getOrDefault(source + ">" + target, List.of())) {
            if (p.ts() <= atTs) {
                rate = atTs < p.ts() + RATE_TTL ? p.rate() : -1;
            }
        }
        return rate;
    }

    private long quoteRaw(String source, String target, long amount, int atTs) {
        if (!isCode(source) || !isCode(target) || source.equals(target) || amount <= 0) return -1;
        long rate = rateAt(source, target, atTs);
        if (rate < 0) return -1;
        long d = SCALE * 100;
        return (amount * rate * (100 - FEE_PERCENT) + d / 2) / d;
    }

    // ---------------------------------------------------------------- level 1

    public boolean openWallet(int ts, String walletId) {
        if (wallets.containsKey(walletId)) return false;
        wallets.put(walletId, new HashMap<>());
        return true;
    }

    public long deposit(int ts, String walletId, String currency, long amount) {
        Map<String, Long> w = wallets.get(walletId);
        if (w == null || !isCode(currency) || amount <= 0) return -1;
        w.merge(currency, amount, Long::sum);
        return w.get(currency);
    }

    public long withdraw(int ts, String walletId, String currency, long amount) {
        Map<String, Long> w = wallets.get(walletId);
        if (w == null || amount <= 0 || w.getOrDefault(currency, 0L) < amount) return -1;
        w.merge(currency, -amount, Long::sum);
        return w.get(currency);
    }

    public long balance(int ts, String walletId, String currency) {
        Map<String, Long> w = wallets.get(walletId);
        return w == null ? -1 : w.getOrDefault(currency, 0L);
    }

    public List<String> holdings(int ts, String walletId) {
        List<String> out = new ArrayList<>();
        for (Map.Entry<String, Long> e : new TreeMap<>(wallets.getOrDefault(walletId, Map.of())).entrySet()) {
            if (e.getValue() > 0) out.add(e.getKey() + ":" + e.getValue());
        }
        return out;
    }

    // ---------------------------------------------------------------- level 2

    public boolean setRate(int ts, String source, String target, long rate) {
        if (!isCode(source) || !isCode(target) || source.equals(target) || rate <= 0) return false;
        rates.computeIfAbsent(source + ">" + target, k -> new ArrayList<>()).add(new Published(ts, rate));
        for (Order o : orders.values()) {
            if (o.status.equals("open") && o.source.equals(source) && o.target.equals(target) && rate >= o.minRate) {
                long got = convert(ts, o.wallet, source, target, o.amount);
                o.status = got < 0 ? "cancelled" : "filled:" + got;
            }
        }
        return true;
    }

    public long quote(int ts, String source, String target, long amount) {
        return quoteRaw(source, target, amount, ts);
    }

    public long convert(int ts, String walletId, String source, String target, long amount) {
        Map<String, Long> w = wallets.get(walletId);
        long got = quoteRaw(source, target, amount, ts);
        if (w == null || got <= 0 || w.getOrDefault(source, 0L) < amount) return -1;
        w.merge(source, -amount, Long::sum);
        w.merge(target, got, Long::sum);
        return got;
    }

    public boolean transfer(int ts, String sender, String receiver, String currency, long amount) {
        Map<String, Long> s = wallets.get(sender), r = wallets.get(receiver);
        if (s == null || r == null || sender.equals(receiver) || amount <= 0
                || s.getOrDefault(currency, 0L) < amount) return false;
        s.merge(currency, -amount, Long::sum);
        r.merge(currency, amount, Long::sum);
        return true;
    }

    // ---------------------------------------------------------------- level 3

    public long quoteAt(int ts, String source, String target, long amount, int atTs) {
        return quoteRaw(source, target, amount, atTs);
    }

    public long totalValue(int ts, String walletId, String currency) {
        Map<String, Long> w = wallets.get(walletId);
        if (w == null || !isCode(currency)) return -1;
        long total = 0;
        for (Map.Entry<String, Long> e : w.entrySet()) {
            long a = e.getValue();
            if (a == 0) continue;
            long v = e.getKey().equals(currency) ? a : quoteRaw(e.getKey(), currency, a, ts);
            if (v < 0) return -1;
            total += v;
        }
        return total;
    }

    // ---------------------------------------------------------------- level 4

    public String placeOrder(int ts, String walletId, String source, String target, long amount, long minRate) {
        if (!wallets.containsKey(walletId) || !isCode(source) || !isCode(target) || source.equals(target)
                || amount <= 0 || minRate <= 0) return "";
        Order o = new Order();
        o.wallet = walletId;
        o.source = source;
        o.target = target;
        o.amount = amount;
        o.minRate = minRate;
        String id = "o" + (orders.size() + 1);
        orders.put(id, o);
        return id;
    }

    public boolean cancelOrder(int ts, String orderId) {
        Order o = orders.get(orderId);
        if (o == null || !o.status.equals("open")) return false;
        o.status = "cancelled";
        return true;
    }

    public String orderStatus(int ts, String orderId) {
        Order o = orders.get(orderId);
        return o == null ? "" : o.status;
    }
}
