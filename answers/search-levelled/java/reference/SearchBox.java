import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

/**
 * The autocomplete behind a site search box, built from the query log: popularity, suggestions, top-k lists and
 * the fewest keystrokes to reach a query.
 */
public class SearchBox {
    private record Entry(int count, String query) {}

    /** More popular first, ties alphabetical. */
    private static final Comparator<Entry> BEST =
            Comparator.comparingInt((Entry e) -> -e.count()).thenComparing(Entry::query);

    private static final class Node {
        final Map<Character, Node> kids = new HashMap<>();
        // every logged query under this prefix, best suggestion first
        final TreeSet<Entry> ranked = new TreeSet<>(BEST);
    }

    private final Map<String, Integer> count = new HashMap<>();
    private final Node root = new Node();

    public SearchBox() {}

    private List<Node> path(String query) {
        Node n = root;
        List<Node> out = new ArrayList<>();
        out.add(n);
        for (int i = 0; i < query.length(); i++) {
            n = n.kids.computeIfAbsent(query.charAt(i), c -> new Node());
            out.add(n);
        }
        return out;
    }

    private Node find(String prefix) {
        Node n = root;
        for (int i = 0; i < prefix.length() && n != null; i++) n = n.kids.get(prefix.charAt(i));
        return n;
    }

    /** Changes query's popularity to n (0 removes it) in every prefix's ranking. */
    private void set(String query, int n) {
        int old = count.getOrDefault(query, 0);
        for (Node nd : path(query)) {
            if (old > 0) nd.ranked.remove(new Entry(old, query));
            if (n > 0) nd.ranked.add(new Entry(n, query));
        }
        if (n > 0) count.put(query, n);
        else count.remove(query);
    }

    public int logQuery(String query) {
        int n = count.getOrDefault(query, 0) + 1;
        set(query, n);
        return n;
    }

    public int popularity(String query) {
        return count.getOrDefault(query, 0);
    }

    public String suggest(String prefix) {
        Node n = find(prefix);
        if (n == null || n.ranked.isEmpty()) return null;
        return n.ranked.first().query();
    }

    // level 2

    public boolean deleteQuery(String query) {
        if (!count.containsKey(query)) return false;
        set(query, 0);
        return true;
    }

    public Integer mergeQueries(String from, String into) {
        if (!count.containsKey(from) || from.equals(into)) return null;
        int moved = count.get(from);
        set(from, 0);
        int n = count.getOrDefault(into, 0) + moved;
        set(into, n);
        return n;
    }

    // level 3

    public int importLog(List<String> log) {
        Map<String, Integer> batch = new HashMap<>();
        for (String q : log) batch.merge(q, 1, Integer::sum);
        for (Map.Entry<String, Integer> e : batch.entrySet())
            set(e.getKey(), count.getOrDefault(e.getKey(), 0) + e.getValue());
        return count.size();
    }

    public List<String> topSuggestions(String prefix, int k) {
        List<String> out = new ArrayList<>();
        Node n = find(prefix);
        if (n == null) return out;
        Iterator<Entry> it = n.ranked.iterator();
        for (int i = 0; i < k && it.hasNext(); i++) {
            Entry e = it.next();
            out.add(e.query() + ":" + e.count());
        }
        return out;
    }

    // level 4

    public int fewestKeystrokes(String target) {
        // Each keystroke costs 1: breadth-first over box texts. Only prefixes of logged queries
        // and of the target are worth visiting; any other text can only be backspaced away.
        Map<String, Integer> dist = new HashMap<>();
        dist.put("", 0);
        ArrayDeque<String> todo = new ArrayDeque<>();
        todo.add("");
        while (!todo.isEmpty()) {
            String s = todo.poll();
            int d = dist.get(s);
            if (s.equals(target)) return d;
            List<String> nexts = new ArrayList<>();
            if (!s.isEmpty()) nexts.add(s.substring(0, s.length() - 1));
            Node n = find(s);
            if (n != null && !n.ranked.isEmpty()) {
                nexts.add(n.ranked.first().query()); // Tab
                for (Map.Entry<Character, Node> kid : n.kids.entrySet())
                    if (!kid.getValue().ranked.isEmpty()) nexts.add(s + kid.getKey());
            }
            if (s.length() < target.length() && target.startsWith(s)) nexts.add(target.substring(0, s.length() + 1));
            for (String x : nexts) {
                if (!dist.containsKey(x)) {
                    dist.put(x, d + 1);
                    todo.add(x);
                }
            }
        }
        return -1;
    }
}
