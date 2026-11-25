import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** One B2B invoice: discounted line items, tax by category, credit notes, payments and late fees. */
public class Invoice {
    private static final Map<String, Integer> TERMS = Map.of("net15", 15, "net30", 30, "net60", 60);
    private static final Map<String, Integer> TAX_BP = Map.of("standard", 2000, "reduced", 500, "zero", 0); // 2000 = 20%
    private static final int LATE_FEE_BP = 150; // 1.5%

    private static final class Line {
        final String category;
        final long net;
        Line(String category, long net) { this.category = category; this.net = net; }
    }

    private final int issueDay;
    private final int terms;
    private final List<Line> lines = new ArrayList<>();
    private long settled; // payments + credit notes

    public Invoice(int issueDay, String terms) {
        if (!TERMS.containsKey(terms)) throw new InvalidTermsException("unknown payment terms " + terms);
        this.issueDay = issueDay;
        this.terms = TERMS.get(terms);
    }

    /** numerator / denominator rounded to the nearest long, an exact half rounding up (both >= 0). */
    private static long halfUp(long numerator, long denominator) {
        return (numerator + denominator / 2) / denominator;
    }

    private static int discountBp(int quantity) {
        if (quantity >= 100) return 1000;
        if (quantity >= 50) return 500;
        return 0;
    }

    public int addLine(int unitPrice, int quantity, String category) {
        if (!TAX_BP.containsKey(category)) throw new InvalidCategoryException("unknown tax category " + category);
        if (quantity < 1) throw new InvalidQuantityException("quantity must be at least 1");
        if (unitPrice < 0) throw new InvalidPriceException("unit price must not be negative");
        long gross = (long) unitPrice * quantity;
        long net = gross - halfUp(gross * discountBp(quantity), 10000);
        lines.add(new Line(category, net));
        return (int) net;
    }

    private long subtotalL() {
        long sum = 0;
        for (Line l : lines) sum += l.net;
        return sum;
    }

    private long taxL() {
        Map<String, Long> byCategory = new LinkedHashMap<>();
        for (Line l : lines) byCategory.merge(l.category, l.net, Long::sum);
        long sum = 0;
        for (Map.Entry<String, Long> e : byCategory.entrySet()) {
            sum += halfUp(e.getValue() * TAX_BP.get(e.getKey()), 10000);
        }
        return sum;
    }

    public int subtotal() { return (int) subtotalL(); }

    public int tax() { return (int) taxL(); }

    public int total() { return (int) (subtotalL() + taxL()); }

    public int dueDay() { return issueDay + terms; }

    private long balanceL() { return subtotalL() + taxL() - settled; }

    public int balance() { return (int) balanceL(); }

    private void settle(int amount) {
        if (amount < 1 || amount > balanceL()) throw new InvalidAmountException("amount must be 1 to the balance");
        settled += amount;
    }

    public void pay(int amount) { settle(amount); }

    public void creditNote(int amount) { settle(amount); }

    public int amountDue(int day) {
        if (day < issueDay) throw new InvalidDayException("day is before the issue day");
        long owed = balanceL();
        if (day > dueDay() && owed > 0) {
            return (int) (owed + halfUp(owed * LATE_FEE_BP, 10000));
        }
        return (int) owed;
    }
}
