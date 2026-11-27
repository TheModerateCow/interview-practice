import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Loan servicing for a consumer lender: instalment schedules, payments, late fees, payoff quotes and restructuring. */
public class Lender {
    private static final int GRACE_DAYS = 10;
    private static final int LATE_FEE = 2500;

    private static final class Instalment {
        final int due, amount;
        int fee, interest, principal; // still unpaid
        boolean charged;

        Instalment(int due, int interest, int principal) {
            this.due = due;
            this.amount = interest + principal;
            this.interest = interest;
            this.principal = principal;
        }

        int left() {
            return fee + interest + principal;
        }
    }

    private static final class Loan {
        final int rateBp;
        List<Instalment> inst; // in due order

        Loan(int rateBp, List<Instalment> inst) {
            this.rateBp = rateBp;
            this.inst = inst;
        }
    }

    private final Map<String, Loan> loans = new HashMap<>();

    public Lender() {}

    /** Flat interest rounded half up; the last instalment absorbs the principal remainder. */
    private static List<Instalment> instalments(int start, int principal, int months, int rateBp) {
        int interest = (int) (((long) principal * rateBp + 5000) / 10000);
        int base = principal / months;
        List<Instalment> out = new ArrayList<>();
        for (int k = 1; k <= months; k++) {
            int p = k == months ? principal - base * (months - 1) : base;
            out.add(new Instalment(start + 30 * k, interest, p));
        }
        return out;
    }

    // ---------------------------------------------------------------- level 1

    public boolean originate(int day, String loanId, int principal, int months, int rateBp) {
        if (loans.containsKey(loanId) || principal <= 0 || months <= 0 || rateBp < 0) {
            return false;
        }
        loans.put(loanId, new Loan(rateBp, instalments(day, principal, months, rateBp)));
        return true;
    }

    public List<String> schedule(int day, String loanId) {
        List<String> out = new ArrayList<>();
        Loan loan = loans.get(loanId);
        if (loan != null) {
            for (Instalment i : loan.inst) {
                out.add(i.due + ":" + i.amount);
            }
        }
        return out;
    }

    public int amountDue(int day, String loanId) {
        Loan loan = loans.get(loanId);
        if (loan == null) {
            return -1;
        }
        int sum = 0;
        for (Instalment i : loan.inst) {
            if (i.due <= day) {
                sum += i.left();
            }
        }
        return sum;
    }

    // ---------------------------------------------------------------- level 2

    public int pay(int day, String loanId, int amount) {
        Loan loan = loans.get(loanId);
        if (loan == null || amount <= 0) {
            return -1;
        }
        for (Instalment i : loan.inst) {
            int take = Math.min(amount, i.fee);
            i.fee -= take;
            amount -= take;
            take = Math.min(amount, i.interest);
            i.interest -= take;
            amount -= take;
            take = Math.min(amount, i.principal);
            i.principal -= take;
            amount -= take;
        }
        return amount;
    }

    public int owed(int day, String loanId) {
        Loan loan = loans.get(loanId);
        if (loan == null) {
            return -1;
        }
        int sum = 0;
        for (Instalment i : loan.inst) {
            sum += i.left();
        }
        return sum;
    }

    public int principalLeft(int day, String loanId) {
        Loan loan = loans.get(loanId);
        if (loan == null) {
            return -1;
        }
        int sum = 0;
        for (Instalment i : loan.inst) {
            sum += i.principal;
        }
        return sum;
    }

    // ---------------------------------------------------------------- level 3

    public int chargeLateFees(int day) {
        int n = 0;
        for (Loan loan : loans.values()) {
            for (Instalment i : loan.inst) {
                if (i.due + GRACE_DAYS < day && i.left() > 0 && !i.charged) {
                    i.charged = true;
                    i.fee += LATE_FEE;
                    n++;
                }
            }
        }
        return n;
    }

    public String status(int day, String loanId) {
        Loan loan = loans.get(loanId);
        if (loan == null) {
            return "";
        }
        boolean paid = true, late = false;
        for (Instalment i : loan.inst) {
            if (i.left() > 0) {
                paid = false;
                if (i.due + GRACE_DAYS < day) {
                    late = true;
                }
            }
        }
        return paid ? "paid_off" : late ? "late" : "current";
    }

    // ---------------------------------------------------------------- level 4

    public int payoffQuote(int day, String loanId) {
        Loan loan = loans.get(loanId);
        if (loan == null) {
            return -1;
        }
        int sum = 0;
        for (Instalment i : loan.inst) {
            sum += i.principal;
            if (i.due <= day) {
                sum += i.fee + i.interest;
            }
        }
        return sum;
    }

    public boolean restructure(int day, String loanId, int months) {
        Loan loan = loans.get(loanId);
        if (loan == null || months <= 0) {
            return false;
        }
        List<Instalment> kept = new ArrayList<>();
        int rest = 0, future = 0;
        for (Instalment i : loan.inst) {
            if (i.due <= day) {
                kept.add(i);
                continue;
            }
            if (i.left() != i.amount) {
                return false;
            }
            future++;
            rest += i.principal;
        }
        if (future == 0) {
            return false;
        }
        kept.addAll(instalments(day, rest, months, loan.rateBp));
        loan.inst = kept;
        return true;
    }
}
