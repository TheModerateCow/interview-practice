import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Comparator;

/** Ranking and cursor helpers shared by the feed service. */
final class Ranking {
    private Ranking() { }

    /** Recency worth one doubling of a post's likes, in seconds. */
    static final long DECAY_SECONDS = 6 * 60 * 60;

    /** How far back the home feed looks, in seconds. */
    static final long FEED_WINDOW = 7 * 24 * 60 * 60;

    /** A post with its ranking score. */
    record Ranked(double score, Post post) { }

    /** Ranking score: each doubling of likes is worth DECAY_SECONDS of recency. */
    static double hotScore(int likes, long createdAt) {
        return Math.log(1 + likes) / Math.log(2) + (double) createdAt / DECAY_SECONDS;
    }

    /** Feed order: highest score first, then lowest post id. */
    static final Comparator<Ranked> ORDER = (a, b) -> {
        if (a.score() != b.score()) return Double.compare(b.score(), a.score());
        return a.post().id().compareTo(b.post().id());
    };

    /** True if a post with this score and id comes after the cursor position. */
    static boolean after(Ranked r, double cursorScore, String cursorId) {
        if (r.score() != cursorScore) return r.score() < cursorScore;
        return r.post().id().compareTo(cursorId) > 0;
    }

    /** Opaque token for the position just after the post with this score and id. */
    static String encodeCursor(double score, String postId) {
        String raw = Double.toString(score) + "|" + postId;
        return Base64.getUrlEncoder().encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    /** Inverse of encodeCursor: {score, id}. Throws BAD_CURSOR for anything it did not make. */
    static Object[] decodeCursor(String token) {
        try {
            String raw = new String(Base64.getUrlDecoder().decode(token), StandardCharsets.UTF_8);
            int bar = raw.indexOf('|');
            if (bar < 0) throw new IllegalArgumentException();
            return new Object[] {Double.parseDouble(raw.substring(0, bar)), raw.substring(bar + 1)};
        } catch (IllegalArgumentException e) {
            throw new FeedException(FeedException.Code.BAD_CURSOR, "bad cursor: " + token);
        }
    }
}
