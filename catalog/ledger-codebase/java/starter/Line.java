/** One posting as it appears on an account statement. {@code balance} is the account's balance right after it. */
public record Line(long ts, String entryId, long amount, long balance) {}
