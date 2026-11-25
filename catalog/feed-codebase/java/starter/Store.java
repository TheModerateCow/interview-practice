import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Everything one feed region knows, held in memory. */
final class Store {
    private final Set<String> users = new HashSet<>();
    private final Map<String, Post> posts = new HashMap<>();
    /** Each author's posts, oldest first (by createdAt, then id). */
    private final Map<String, List<Post>> byAuthor = new HashMap<>();
    private final Map<String, Set<String>> following = new HashMap<>();
    private final Map<String, Map<String, Mute>> mutes = new HashMap<>();
    private final Set<String> likes = new HashSet<>();

    // users ---------------------------------------------------------------

    void addUser(String id) {
        users.add(id);
    }

    void requireUser(String id) {
        if (!users.contains(id)) throw new FeedException(FeedException.Code.UNKNOWN_USER, "no such user: " + id);
    }

    // posts ---------------------------------------------------------------

    void addPost(Post p) {
        if (posts.containsKey(p.id())) {
            throw new FeedException(FeedException.Code.DUPLICATE_POST, "post already exists: " + p.id());
        }
        posts.put(p.id(), p);
        List<Post> list = byAuthor.computeIfAbsent(p.author(), a -> new ArrayList<>());
        int i = lowerBound(list, p.createdAt());
        while (i < list.size() && list.get(i).createdAt() == p.createdAt() && list.get(i).id().compareTo(p.id()) < 0) i++;
        list.add(i, p);
    }

    Post getPost(String id) {
        Post p = posts.get(id);
        if (p == null) throw new FeedException(FeedException.Code.UNKNOWN_POST, "no such post: " + id);
        return p;
    }

    /** The author's posts with start <= createdAt <= end, oldest first. */
    List<Post> postsBy(String author, long start, long end) {
        List<Post> out = new ArrayList<>();
        for (Post p : posts.values()) {
            if (p.author().equals(author) && p.createdAt() >= start && p.createdAt() <= end) out.add(p);
        }
        out.sort(java.util.Comparator.comparingLong(Post::createdAt).thenComparing(Post::id));
        return out;
    }

    /** First index whose post was created at or after t. */
    private static int lowerBound(List<Post> list, long t) {
        int lo = 0, hi = list.size();
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (list.get(mid).createdAt() < t) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }

    /** First index whose post was created after t. */
    private static int upperBound(List<Post> list, long t) {
        int lo = 0, hi = list.size();
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (list.get(mid).createdAt() <= t) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }

    // likes ---------------------------------------------------------------

    /** Records userId liking postId. Returns false if it was already recorded. */
    boolean addLike(String postId, String userId) {
        Post post = getPost(postId);
        String key = postId + "\u0000" + userId;
        likes.add(key);
        post.likes++;
        return true;
    }

    // follows and mutes ---------------------------------------------------

    void follow(String follower, String followee) {
        following.computeIfAbsent(follower, k -> new HashSet<>()).add(followee);
    }

    void unfollow(String follower, String followee) {
        Set<String> s = following.get(follower);
        if (s != null) s.remove(followee);
    }

    /** A copy of who the user follows. */
    Set<String> following(String id) {
        return new HashSet<>(following.getOrDefault(id, Set.of()));
    }

    /** Stores a mute, replacing any earlier mute of the same account. */
    void setMute(String viewer, Mute m) {
        mutes.computeIfAbsent(viewer, k -> new HashMap<>()).put(m.target(), m);
    }

    List<Mute> mutes(String viewer) {
        return new ArrayList<>(mutes.getOrDefault(viewer, Collections.emptyMap()).values());
    }
}
