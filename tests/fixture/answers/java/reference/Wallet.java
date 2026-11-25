import java.util.ArrayList;
import java.util.List;

public class Wallet {
    private final String owner;
    private long bal;
    private final List<String> hist = new ArrayList<>();
    private boolean frozen;

    public Wallet(String owner) { this.owner = owner; }

    private void check(long cents) {
        if (frozen) throw new WalletFrozenException();
        if (cents <= 0) throw new InvalidAmountException(String.valueOf(cents));
    }

    public void deposit(long cents) {
        check(cents);
        bal += cents;
        hist.add("+" + cents);
    }

    public long withdraw(long cents) {
        check(cents);
        if (cents > bal) throw new InsufficientFundsException(String.valueOf(cents));
        bal -= cents;
        hist.add("-" + cents);
        return bal;
    }

    public long balance() { return bal; }
    public String ownerName() { return owner; }
    public List<String> history() { return new ArrayList<>(hist); }
    public void freeze() { frozen = true; }
    public boolean frozen() { return frozen; }
}
