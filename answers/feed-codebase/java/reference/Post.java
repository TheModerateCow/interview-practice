/** One published post. Times are whole seconds since the epoch. */
public final class Post {
    private final String id;
    private final String author;
    private final long createdAt;
    private final String text;
    int likes;

    Post(String id, String author, long createdAt, String text) {
        this.id = id;
        this.author = author;
        this.createdAt = createdAt;
        this.text = text;
    }

    public String id() { return id; }
    public String author() { return author; }
    public long createdAt() { return createdAt; }
    public String text() { return text; }
    public int likes() { return likes; }
}
