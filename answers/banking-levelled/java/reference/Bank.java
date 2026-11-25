import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** The in-memory core of a retail bank: accounts, money movement, rankings, scheduled payments, merges and balance history. */
public class Bank {
    private static final class Account {
        int balance;
        int spent; // withdrawals, transfers sent and scheduled payments made
    }

    /** One point in an account id's balance history. */
    private record Change(int ts, int balance, boolean open) {}

    private static final class Payment {
        String account;
        final int amount, due;
        String status = "pending";
        Payment(String account, int amount, int due) { this.account = account; this.amount = amount; this.due = due; }
    }

    private final Map<String, Account> accounts = new HashMap<>();
    private final Map<String, List<Change>> history = new HashMap<>();
    private final List<Payment> payments = new ArrayList<>(); // in the order they were scheduled
    private final Map<String, Payment> byId = new HashMap<>();

    public Bank() {}

    private void record(int ts, String id) {
        Account a = accounts.get(id);
        history.computeIfAbsent(id, k -> new ArrayList<>())
               .add(new Change(ts, a == null ? 0 : a.balance, a != null));
    }

    /** Runs every pending payment due at or before ts, earliest due first, ties in schedule order. */
    private void settle(int ts) {
        List<Payment> due = new ArrayList<>();
        for (Payment p : payments) {
            if (p.status.equals("pending") && p.due <= ts) due.add(p);
        }
        due.sort((x, y) -> Integer.compare(x.due, y.due)); // stable
        for (Payment p : due) {
            Account a = accounts.get(p.account);
            if (a == null || a.balance < p.amount) {
                p.status = "failed";
                continue;
            }
            a.balance -= p.amount;
            a.spent += p.amount;
            p.status = "paid";
            record(p.due, p.account);
        }
    }

    public boolean openAccount(int ts, String id) {
        settle(ts);
        if (accounts.containsKey(id)) return false;
        accounts.put(id, new Account());
        record(ts, id);
        return true;
    }

    public Integer deposit(int ts, String id, int amount) {
        settle(ts);
        Account a = accounts.get(id);
        if (a == null) return null;
        a.balance += amount;
        record(ts, id);
        return a.balance;
    }

    public Integer withdraw(int ts, String id, int amount) {
        settle(ts);
        Account a = accounts.get(id);
        if (a == null || a.balance < amount) return null;
        a.balance -= amount;
        a.spent += amount;
        record(ts, id);
        return a.balance;
    }

    public Integer transfer(int ts, String from, String to, int amount) {
        settle(ts);
        Account src = accounts.get(from), dst = accounts.get(to);
        if (src == null || dst == null || from.equals(to) || src.balance < amount) return null;
        src.balance -= amount;
        src.spent += amount;
        dst.balance += amount;
        record(ts, from);
        record(ts, to);
        return src.balance;
    }

    public Integer balance(int ts, String id) {
        settle(ts);
        Account a = accounts.get(id);
        return a == null ? null : a.balance;
    }

    /** Up to n open accounts as "id:spent", most spent first, ties by id. */
    public List<String> topSpenders(int ts, int n) {
        settle(ts);
        List<String> ids = new ArrayList<>(accounts.keySet());
        ids.sort((x, y) -> {
            int sx = accounts.get(x).spent, sy = accounts.get(y).spent;
            if (sx != sy) return sy - sx;
            return x.compareTo(y);
        });
        List<String> out = new ArrayList<>();
        for (int i = 0; i < ids.size() && i < n; i++) out.add(ids.get(i) + ":" + accounts.get(ids.get(i)).spent);
        return out;
    }

    /** Every open account holding at least min, as "id:balance", largest balance first, ties by id. */
    public List<String> accountsAbove(int ts, int min) {
        settle(ts);
        List<String> ids = new ArrayList<>();
        for (Map.Entry<String, Account> e : accounts.entrySet()) {
            if (e.getValue().balance >= min) ids.add(e.getKey());
        }
        ids.sort((x, y) -> {
            int bx = accounts.get(x).balance, by = accounts.get(y).balance;
            if (bx != by) return by - bx;
            return x.compareTo(y);
        });
        List<String> out = new ArrayList<>();
        for (String id : ids) out.add(id + ":" + accounts.get(id).balance);
        return out;
    }

    /** Books a payment due delay after ts. Returns its id "pay1", "pay2", ... or null. */
    public String schedulePayment(int ts, String id, int amount, int delay) {
        settle(ts);
        if (!accounts.containsKey(id)) return null;
        Payment p = new Payment(id, amount, ts + delay);
        payments.add(p);
        String pid = "pay" + payments.size();
        byId.put(pid, p);
        return pid;
    }

    public boolean cancelPayment(int ts, String id, String paymentId) {
        settle(ts);
        Payment p = byId.get(paymentId);
        if (p == null || !p.status.equals("pending") || !p.account.equals(id)) return false;
        p.status = "cancelled";
        return true;
    }

    /** "pending", "paid", "failed" or "cancelled"; "" for an unknown id. */
    public String paymentStatus(int ts, String paymentId) {
        settle(ts);
        Payment p = byId.get(paymentId);
        return p == null ? "" : p.status;
    }

    /** Folds absorb into keep: balance, spending and pending payments. absorb is closed. */
    public boolean mergeAccounts(int ts, String keep, String absorb) {
        settle(ts);
        Account k = accounts.get(keep), a = accounts.get(absorb);
        if (k == null || a == null || keep.equals(absorb)) return false;
        k.balance += a.balance;
        k.spent += a.spent;
        for (Payment p : payments) {
            if (p.status.equals("pending") && p.account.equals(absorb)) {
                p.account = keep;
            }
        }
        accounts.remove(absorb);
        record(ts, keep);
        record(ts, absorb);
        return true;
    }

    /** What the id's balance was right after everything at or before atTs (atTs <= ts); null if not open then. */
    public Integer balanceAt(int ts, String id, int atTs) {
        settle(ts);
        List<Change> h = history.getOrDefault(id, List.of());
        int lo = 0, hi = h.size();
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (h.get(mid).ts() > atTs) hi = mid; else lo = mid + 1;
        }
        if (lo == 0 || !h.get(lo - 1).open()) return null;
        return h.get(lo - 1).balance();
    }
}
