import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** A public library's lending desk: copies of titles, members, loans with due dates and late fines, and each member's borrowing history. */
public class Library {
    /** How many copies a member can have on loan at once. */
    public static final int MAX_LOANS = 3;
    /** A copy checked out on day t is due on day t + LOAN_DAYS. */
    public static final int LOAN_DAYS = 14;
    /** Late fine in cents per day past the due date, capped per loan. */
    public static final int FINE_PER_DAY = 25;
    public static final int FINE_CAP = 1000;

    /** One checkout of one copy; back is -1 while the copy is still out. */
    private static final class Loan {
        final String copyId, title;
        String member;
        final int out;
        int due, back = -1, renewals;
        Loan(String copyId, String title, String member, int out, int due) {
            this.copyId = copyId; this.title = title; this.member = member; this.out = out; this.due = due;
        }
    }

    private static final class BookCopy {
        final String id, title;
        Loan current;
        BookCopy(String id, String title) { this.id = id; this.title = title; }
    }

    private static final class Member {
        final List<Loan> loans = new ArrayList<>(); // every checkout, oldest first

        List<Loan> onLoan() {
            List<Loan> out = new ArrayList<>();
            for (Loan l : loans) if (l.back == -1) out.add(l);
            return out;
        }

        boolean hasTitle(String title) {
            for (Loan l : onLoan()) if (l.title.equals(title)) return true;
            return false;
        }
    }

    private final Map<String, BookCopy> copies = new HashMap<>();
    private final Map<String, Member> members = new HashMap<>();
    private final Map<String, Integer> checkouts = new HashMap<>(); // successful checkouts per title

    public Library() {}

    public boolean addMember(int ts, String memberId) {
        if (members.containsKey(memberId)) return false;
        members.put(memberId, new Member());
        return true;
    }

    public boolean addCopy(int ts, String copyId, String title) {
        if (copies.containsKey(copyId)) return false;
        copies.put(copyId, new BookCopy(copyId, title));
        return true;
    }

    public String checkout(int ts, String memberId, String title) {
        Member m = members.get(memberId);
        if (m == null || m.onLoan().size() >= MAX_LOANS || m.hasTitle(title)) return "";
        BookCopy best = null;
        for (BookCopy c : copies.values()) {
            if (c.title.equals(title) && c.current == null && (best == null || c.id.compareTo(best.id) < 0)) best = c;
        }
        if (best == null) return "";
        Loan l = new Loan(best.id, title, memberId, ts, ts + LOAN_DAYS);
        best.current = l;
        m.loans.add(l);
        checkouts.merge(title, 1, Integer::sum);
        return best.id;
    }

    public boolean returnCopy(int ts, String copyId) {
        BookCopy c = copies.get(copyId);
        if (c == null || c.current == null) return false;
        c.current.back = ts;
        c.current = null;
        return true;
    }

    public String borrower(int ts, String copyId) {
        BookCopy c = copies.get(copyId);
        return c != null && c.current != null ? c.current.member : "";
    }

    public int available(int ts, String title) {
        int n = 0;
        for (BookCopy c : copies.values()) {
            if (c.title.equals(title) && c.current == null) {
                n++;
            }
        }
        return n;
    }

    public List<String> loansOf(int ts, String memberId) {
        List<String> out = new ArrayList<>();
        Member m = members.get(memberId);
        if (m != null) for (Loan l : m.onLoan()) out.add(l.copyId);
        Collections.sort(out);
        return out;
    }

    /** Up to n titles as "title(checkouts)", most checkouts first, ties by title. */
    public List<String> popular(int ts, int n) {
        List<String> titles = new ArrayList<>(checkouts.keySet());
        titles.sort((a, b) -> {
            int ca = checkouts.get(a), cb = checkouts.get(b);
            if (ca != cb) return Integer.compare(cb, ca);
            return a.compareTo(b);
        });
        List<String> out = new ArrayList<>();
        for (int i = 0; i < titles.size() && i < n; i++) out.add(titles.get(i) + "(" + checkouts.get(titles.get(i)) + ")");
        return out;
    }

    public int dueDate(int ts, String copyId) {
        BookCopy c = copies.get(copyId);
        return c != null && c.current != null ? c.current.due : -1;
    }

    public int renew(int ts, String copyId) {
        BookCopy c = copies.get(copyId);
        if (c == null || c.current == null) return -1;
        Loan l = c.current;
        if (ts > l.due || l.renewals >= 2) return -1;
        l.renewals++;
        l.due += LOAN_DAYS;
        return l.due;
    }

    public int fines(int ts, String memberId) {
        int total = 0;
        Member m = members.get(memberId);
        if (m != null) {
            for (Loan l : m.loans) {
                if (l.back != -1 && l.back > l.due) {
                    total += Math.min(FINE_CAP, FINE_PER_DAY * (l.back - l.due));
                }
            }
        }
        return total;
    }

    public List<String> history(int ts, String memberId) {
        List<String> out = new ArrayList<>();
        Member m = members.get(memberId);
        if (m != null) for (Loan l : m.loans) out.add(l.title);
        return out;
    }

    public boolean merge(int ts, String keepId, String dropId) {
        Member k = members.get(keepId), d = members.get(dropId);
        if (k == null || d == null || keepId.equals(dropId)) return false;
        if (k.onLoan().size() + d.onLoan().size() > MAX_LOANS) return false;
        for (Loan l : d.onLoan()) {
            if (k.hasTitle(l.title)) return false;
        }
        for (Loan l : d.loans) {
            l.member = keepId;
        }
        k.loans.addAll(d.loans);
        k.loans.sort((a, b) -> Integer.compare(a.out, b.out)); // stable
        members.remove(dropId);
        return true;
    }
}
