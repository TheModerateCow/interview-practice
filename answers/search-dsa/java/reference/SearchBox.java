import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class SearchBox {
    /** Fewest keystrokes (letter, Backspace, Tab) that make an empty search box show target. */
    public static int fewestKeystrokes(List<String> log, String target) {
        Map<String, Integer> count = new HashMap<>();
        int maxNodes = target.length() + 1;
        for (String q : log) {
            count.merge(q, 1, Integer::sum);
            maxNodes += q.length();
        }
        // Trie over the logged queries and the target; node 0 is the empty box, and no node has child 0.
        Trie trie = new Trie(maxNodes);
        Map<String, Integer> end = new HashMap<>();
        for (String q : count.keySet()) end.put(q, trie.insert(q));
        int goal = trie.insert(target);

        // Tab jumps to the most popular logged query under the node (ties: alphabetically first).
        // Visiting queries best-first, the first one to pass through a node is that node's suggestion.
        List<String> queries = new ArrayList<>(count.keySet());
        queries.sort(Comparator.comparingInt((String q) -> -count.get(q)).thenComparing(Comparator.naturalOrder()));
        int[] tab = new int[trie.size];
        Arrays.fill(tab, -1);
        for (String q : queries) {
            int node = 0;
            for (int i = 0; i < q.length(); i++) {
                if (tab[node] == -1) tab[node] = end.get(q);
                node = trie.child[node * 26 + (q.charAt(i) - 'a')];
            }
            if (tab[node] == -1) tab[node] = end.get(q);
        }

        // Every keystroke costs 1, so BFS over trie nodes. Strings off the trie are dead ends.
        int[] dist = new int[trie.size];
        Arrays.fill(dist, -1);
        dist[0] = 0;
        ArrayDeque<Integer> todo = new ArrayDeque<>();
        todo.add(0);
        while (!todo.isEmpty()) {
            int node = todo.poll();
            if (node == goal) return dist[node];
            List<Integer> nexts = new ArrayList<>();
            for (int c = 0; c < 26; c++) {
                int kid = trie.child[node * 26 + c];
                if (kid != 0) nexts.add(kid);
            }
            if (trie.parent[node] != -1) nexts.add(trie.parent[node]);
            if (tab[node] != -1) nexts.add(tab[node]);
            for (int nxt : nexts) {
                if (dist[nxt] == -1) {
                    dist[nxt] = dist[node] + 1;
                    todo.add(nxt);
                }
            }
        }
        return dist[goal];
    }

    private static final class Trie {
        final int[] child;
        final int[] parent;
        int size = 1;

        Trie(int maxNodes) {
            child = new int[maxNodes * 26];
            parent = new int[maxNodes];
            parent[0] = -1;
        }

        int insert(String word) {
            int node = 0;
            for (int i = 0; i < word.length(); i++) {
                int slot = node * 26 + (word.charAt(i) - 'a');
                if (child[slot] == 0) {
                    child[slot] = size;
                    parent[size] = node;
                    size++;
                }
                node = child[slot];
            }
            return node;
        }
    }
}
