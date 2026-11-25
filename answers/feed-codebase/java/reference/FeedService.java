import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Home feed for one region. Times are whole seconds since the epoch. */
public class FeedService {
    /** Most posts one account may contribute to a catch-up list. */
    static final int CATCH_UP_PER_AUTHOR = 2;

    private final Store store = new Store();

    // accounts ------------------------------------------------------------

    public void addUser(String userId) {
        store.addUser(userId);
    }

    public void follow(String follower, String followee) {
        store.requireUser(follower);
        store.requireUser(followee);
        if (follower.equals(followee)) throw new FeedException(FeedException.Code.SELF_FOLLOW, "cannot follow yourself");
        store.follow(follower, followee);
    }

    public void unfollow(String follower, String followee) {
        store.requireUser(follower);
        store.unfollow(follower, followee);
    }

    /** Hides target's posts from viewer for good. */
    public void mute(String viewer, String target, long now) {
        mute(viewer, target, now, null);
    }

    /** Hides target's posts from viewer for {@code hours} hours (for good if null). */
    public void mute(String viewer, String target, long now, Double hours) {
        store.requireUser(viewer);
        store.requireUser(target);
        store.setMute(viewer, Mute.starting(target, now, hours));
    }

    // posts ---------------------------------------------------------------

    public Post publish(String postId, String author, long createdAt) {
        return publish(postId, author, createdAt, "");
    }

    public Post publish(String postId, String author, long createdAt, String text) {
        store.requireUser(author);
        Post post = new Post(postId, author, createdAt, text);
        store.addPost(post);
        return post;
    }

    public Post post(String postId) {
        return store.getPost(postId);
    }

    /** Records a like (idempotent per user) and returns the post's like count. */
    public int like(String postId, String userId) {
        store.requireUser(userId);
        store.addLike(postId, userId);
        return store.getPost(postId).likes();
    }

    // feeds ---------------------------------------------------------------

    public Page homeFeed(String viewer, long now) {
        return homeFeed(viewer, now, 10, null);
    }

    /** One page of the viewer's ranked home feed (cursor null for the first page). See problem.md for the rules. */
    public Page homeFeed(String viewer, long now, int limit, String cursor) {
        if (limit < 1) throw new FeedException(FeedException.Code.BAD_LIMIT, "limit must be at least 1");
        store.requireUser(viewer);
        Set<String> authors = sources(viewer, now);
        authors.add(viewer);
        List<Ranking.Ranked> ranked = ranked(authors, now - Ranking.FEED_WINDOW, now);
        if (cursor != null) {
            Object[] c = Ranking.decodeCursor(cursor);
            double score = (Double) c[0];
            String id = (String) c[1];
            ranked.removeIf(r -> !Ranking.after(r, score, id));
        }
        List<Ranking.Ranked> page = ranked.subList(0, Math.min(limit, ranked.size()));
        String next = null;
        if (ranked.size() > limit) {
            Ranking.Ranked last = page.get(page.size() - 1);
            next = Ranking.encodeCursor(last.score(), last.post().id());
        }
        List<String> ids = new ArrayList<>();
        for (Ranking.Ranked r : page) ids.add(r.post().id());
        return new Page(ids, next);
    }

    public List<String> catchUp(String viewer, long since, long now) {
        return catchUp(viewer, since, now, 5);
    }

    /** The "while you were away" list. See problem.md for the rules. */
    public List<String> catchUp(String viewer, long since, long now, int limit) {
        if (limit < 1) throw new FeedException(FeedException.Code.BAD_LIMIT, "limit must be at least 1");
        store.requireUser(viewer);
        long start = Math.max(since + 1, now - Ranking.FEED_WINDOW);
        List<String> picked = new ArrayList<>();
        Map<String, Integer> perAuthor = new HashMap<>();
        for (Ranking.Ranked r : ranked(sources(viewer, now), start, now)) {
            int count = perAuthor.getOrDefault(r.post().author(), 0);
            if (count < CATCH_UP_PER_AUTHOR) {
                perAuthor.put(r.post().author(), count + 1);
                picked.add(r.post().id());
                if (picked.size() == limit) break;
            }
        }
        return picked;
    }

    // internals -----------------------------------------------------------

    /** Accounts the viewer follows, minus those muted at {@code now}. */
    private Set<String> sources(String viewer, long now) {
        Set<String> followed = store.following(viewer);
        for (Mute m : store.mutes(viewer)) {
            if (m.active(now)) followed.remove(m.target());
        }
        return followed;
    }

    /** Posts by these authors published in [start, end], in feed order. */
    private List<Ranking.Ranked> ranked(Set<String> authors, long start, long end) {
        List<Ranking.Ranked> out = new ArrayList<>();
        for (String author : new HashSet<>(authors)) {
            for (Post p : store.postsBy(author, start, end)) {
                out.add(new Ranking.Ranked(Ranking.hotScore(p.likes(), p.createdAt()), p));
            }
        }
        out.sort(Ranking.ORDER);
        return out;
    }
}
