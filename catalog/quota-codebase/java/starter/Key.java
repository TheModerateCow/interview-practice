/** An API key issued to an organisation. */
public record Key(String id, String org, String plan, boolean revoked) {
    public Key(String id, String org, String plan) {
        this(id, org, plan, false);
    }
}
