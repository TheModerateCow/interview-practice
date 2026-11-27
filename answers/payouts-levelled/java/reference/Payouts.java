import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Settlement service for a marketplace: merchants, sales, refunds, payouts, a rolling reserve and chargebacks. Every method takes day first: today's date as an integer. Days never decrease. */
public class Payouts {
    private static final int SETTLE_DAYS = 3;
    private static final int CHARGEBACK_FEE = 1500;

    private record Entry(int settle, int amount, boolean reserve) {}

    private static final class Merchant {
        final int bps;
        int reserveBps, hold;
        final List<Entry> entries = new ArrayList<>();
        final List<String> log = new ArrayList<>();
        final List<String> paid = new ArrayList<>();
        Merchant(int bps) { this.bps = bps; }
    }

    private static final class Sale {
        final String merchant;
        final int amount;
        int refunded, fee;
        boolean chargedBack;
        Sale(String merchant, int amount, int fee) { this.merchant = merchant; this.amount = amount; this.fee = fee; }
    }

    private final Map<String, Merchant> merchants = new TreeMap<>();
    private final Map<String, Sale> sales = new HashMap<>();
    private int nextSale;

    public Payouts() {}

    /** Basis points, half a cent rounds up. */
    private static int feeOn(int amount, int bps) {
        return (int) (((long) amount * bps + 5000) / 10000);
    }

    /** A debit (refund, payout, chargeback): it counts at once. */
    private static void post(Merchant m, int day, String kind, int amount) {
        m.entries.add(new Entry(day, amount, false));
        m.log.add(day + ":" + kind + ":" + amount);
    }

    // ---------------------------------------------------------------- level 1

    public boolean addMerchant(int day, String merchantId, int feeBps) {
        if (merchants.containsKey(merchantId) || feeBps < 0 || feeBps > 10000) return false;
        merchants.put(merchantId, new Merchant(feeBps));
        return true;
    }

    public String recordSale(int day, String merchantId, int amount) {
        Merchant m = merchants.get(merchantId);
        if (m == null || amount <= 0) return "";
        String id = "s" + (++nextSale);
        int f = feeOn(amount, m.bps);
        int net = amount - f;
        int reserve = feeOn(net, m.reserveBps);
        m.entries.add(new Entry(day + SETTLE_DAYS, net - reserve, false));
        if (reserve > 0) m.entries.add(new Entry(day + m.hold, reserve, true));
        m.log.add(day + ":sale:" + net);
        sales.put(id, new Sale(merchantId, amount, f));
        return id;
    }

    public int fee(int day, String saleId) {
        Sale s = sales.get(saleId);
        return s == null ? -1 : s.fee;
    }

    public int balance(int day, String merchantId) {
        Merchant m = merchants.get(merchantId);
        if (m == null) return 0;
        int total = 0;
        for (Entry e : m.entries) total += e.amount();
        return total;
    }

    // ---------------------------------------------------------------- level 2

    public int refund(int day, String saleId, int amount) {
        Sale s = sales.get(saleId);
        if (s == null || s.chargedBack || amount <= 0 || amount > s.amount - s.refunded) return -1;
        Merchant m = merchants.get(s.merchant);
        s.refunded += amount;
        int newFee = feeOn(s.amount - s.refunded, m.bps);
        int debit = amount - (s.fee - newFee);
        s.fee = newFee;
        post(m, day, "refund", -debit);
        return debit;
    }

    public List<String> activity(int day, String merchantId) {
        Merchant m = merchants.get(merchantId);
        return m == null ? new ArrayList<>() : new ArrayList<>(m.log);
    }

    // ---------------------------------------------------------------- level 3

    public int available(int day, String merchantId) {
        Merchant m = merchants.get(merchantId);
        if (m == null) return 0;
        int total = 0;
        for (Entry e : m.entries) if (e.settle() <= day) total += e.amount();
        return total;
    }

    public List<String> runPayouts(int day) {
        List<String> out = new ArrayList<>();
        for (Map.Entry<String, Merchant> me : merchants.entrySet()) {
            Merchant m = me.getValue();
            int a = available(day, me.getKey());
            if (a > 0) {
                post(m, day, "payout", -a);
                m.paid.add(day + ":" + a);
                out.add(me.getKey() + ":" + a);
            }
        }
        return out;
    }

    public List<String> payoutHistory(int day, String merchantId) {
        Merchant m = merchants.get(merchantId);
        return m == null ? new ArrayList<>() : new ArrayList<>(m.paid);
    }

    // ---------------------------------------------------------------- level 4

    public boolean setReserve(int day, String merchantId, int reserveBps, int holdDays) {
        Merchant m = merchants.get(merchantId);
        if (m == null || reserveBps < 0 || reserveBps > 10000 || holdDays < 1) return false;
        m.reserveBps = reserveBps;
        m.hold = holdDays;
        return true;
    }

    public int reserveHeld(int day, String merchantId) {
        Merchant m = merchants.get(merchantId);
        if (m == null) return 0;
        int total = 0;
        for (Entry e : m.entries) if (e.reserve() && e.settle() > day) total += e.amount();
        return total;
    }

    public int chargeback(int day, String saleId) {
        Sale s = sales.get(saleId);
        if (s == null || s.chargedBack || s.refunded == s.amount) return -1;
        s.chargedBack = true;
        int debit = s.amount - s.refunded + CHARGEBACK_FEE;
        post(merchants.get(s.merchant), day, "chargeback", -debit);
        return debit;
    }
}
