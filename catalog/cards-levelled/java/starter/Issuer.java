public class Issuer {
    public Issuer() {
        throw new UnsupportedOperationException("not implemented");
    }

    public boolean issueCard(int day, String cardId, int limit) {
        throw new UnsupportedOperationException("not implemented");
    }

    public String authorize(int day, String cardId, String category, int amount) {
        throw new UnsupportedOperationException("not implemented");
    }

    public boolean capture(int day, String authId, int amount) {
        throw new UnsupportedOperationException("not implemented");
    }

    public boolean voidAuth(int day, String authId) {
        throw new UnsupportedOperationException("not implemented");
    }

    public int available(int day, String cardId) {
        throw new UnsupportedOperationException("not implemented");
    }
}
