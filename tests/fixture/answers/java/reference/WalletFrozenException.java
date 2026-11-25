public class WalletFrozenException extends RuntimeException {
    public WalletFrozenException() { super(); }
    public WalletFrozenException(String message) { super(message); }
}
