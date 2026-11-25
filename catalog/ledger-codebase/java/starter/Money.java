import java.util.Map;

/** Currencies and display formatting. Every amount in the ledger is a whole number of minor units (cents, fils, yen). */
public final class Money {
    private Money() {}

    /** How many digits after the decimal point each booked currency has. */
    static final Map<String, Integer> MINOR_DIGITS = Map.of("EUR", 2, "GBP", 2, "JPY", 0, "KWD", 3, "USD", 2);

    /** True if the ledger books amounts in cur. */
    public static boolean validCurrency(String cur) {
        return MINOR_DIGITS.containsKey(cur);
    }

    /** Renders minor units for display: {@code formatAmount(-1250, "USD")} is {@code "-12.50 USD"}. */
    public static String formatAmount(long minor, String cur) {
        String sign = minor < 0 ? "-" : "";
        long abs = Math.abs(minor);
        int d = MINOR_DIGITS.get(cur);
        if (d == 0) return sign + abs + " " + cur;
        long unit = 1;
        for (int i = 0; i < d; i++) unit *= 10;
        return sign + abs / unit + "." + String.format("%0" + d + "d", abs % unit) + " " + cur;
    }
}
