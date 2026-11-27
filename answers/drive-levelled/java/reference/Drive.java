import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Cloud file storage: files by path, folder listings, users with storage quotas, file versions and a trash. */
public class Drive {
    private static final class User {
        final int capacity;
        int used;
        User(int capacity) { this.capacity = capacity; }
    }

    private static final class File {
        final User owner; // null: nobody's, counts against no quota
        final List<Integer> versions = new ArrayList<>(); // sizes, last = current
        File(User owner, int size) { this.owner = owner; versions.add(size); }
        int size() { return versions.get(versions.size() - 1); }
        int total() { return sum(versions); }
    }

    private record Trashed(String path, File file) {}

    private final Map<String, File> files = new HashMap<>();
    private final Map<String, User> users = new HashMap<>();
    private final List<Trashed> trash = new ArrayList<>(); // in deletion order

    public Drive() {}

    private static int sum(List<Integer> xs) {
        int t = 0;
        for (int x : xs) t += x;
        return t;
    }

    /** Counts size against u's quota; false, changing nothing, if it doesn't fit. */
    private static boolean charge(User u, int size) {
        if (u == null) return true;
        if (u.used + size > u.capacity) return false;
        u.used += size;
        return true;
    }

    private static void free(User u, int size) {
        if (u != null) u.used -= size;
    }

    private boolean add(User owner, String path, int size) {
        if (files.containsKey(path) || size < 0 || !charge(owner, size)) return false;
        files.put(path, new File(owner, size));
        return true;
    }

    private boolean copy(User owner, String source, String dest) {
        File src = files.get(source);
        if (src == null || files.containsKey(dest)) return false;
        return add(owner, dest, src.size());
    }

    // ---------------------------------------------------------------- level 1

    public boolean addFile(String path, int size) {
        return add(null, path, size);
    }

    public int getFileSize(String path) {
        File f = files.get(path);
        return f == null ? -1 : f.size();
    }

    public boolean copyFile(String source, String dest) {
        File src = files.get(source);
        return src != null && copy(src.owner, source, dest);
    }

    public int deleteFile(String path) {
        File f = files.remove(path);
        if (f == null) return -1;
        free(f.owner, f.total());
        trash.add(new Trashed(path, f));
        return f.size();
    }

    // ---------------------------------------------------------------- level 2

    private List<String> under(String prefix) {
        List<String> out = new ArrayList<>();
        for (String p : files.keySet()) if (p.startsWith(prefix)) out.add(p);
        return out;
    }

    public List<String> largestFiles(String prefix, int n) {
        List<String> paths = under(prefix);
        paths.sort((a, b) -> {
            int c = Integer.compare(files.get(b).size(), files.get(a).size());
            return c != 0 ? c : a.compareTo(b);
        });
        List<String> out = new ArrayList<>();
        for (int i = 0; i < paths.size() && i < n; i++) out.add(paths.get(i) + "(" + files.get(paths.get(i)).size() + ")");
        return out;
    }

    public int folderSize(String prefix) {
        int t = 0;
        for (String p : under(prefix)) t += files.get(p).size();
        return t;
    }

    // ---------------------------------------------------------------- level 3

    public boolean addUser(String userId, int capacity) {
        if (users.containsKey(userId) || capacity <= 0) return false;
        users.put(userId, new User(capacity));
        return true;
    }

    public int addFileBy(String userId, String path, int size) {
        User u = users.get(userId);
        if (u == null || !add(u, path, size)) return -1;
        return u.capacity - u.used;
    }

    public int copyFileBy(String userId, String source, String dest) {
        User u = users.get(userId);
        if (u == null || !copy(u, source, dest)) return -1;
        return u.capacity - u.used;
    }

    public int remaining(String userId) {
        User u = users.get(userId);
        return u == null ? -1 : u.capacity - u.used;
    }

    // ---------------------------------------------------------------- level 4

    public int overwriteFile(String path, int size) {
        File f = files.get(path);
        if (f == null || size < 0 || !charge(f.owner, size)) return -1;
        f.versions.add(size);
        return f.versions.size();
    }

    public int restoreVersion(String path, int version) {
        File f = files.get(path);
        if (f == null || version < 1 || version > f.versions.size()) return -1;
        List<Integer> later = f.versions.subList(version, f.versions.size());
        free(f.owner, sum(later));
        later.clear();
        return f.size();
    }

    public boolean restoreFile(String path) {
        if (files.containsKey(path)) return false;
        for (int i = trash.size() - 1; i >= 0; i--) {
            Trashed t = trash.get(i);
            if (t.path().equals(path)) {
                if (!charge(t.file().owner, t.file().total())) return false;
                trash.remove(i);
                files.put(path, t.file());
                return true;
            }
        }
        return false;
    }

    public int emptyTrash() {
        int n = trash.size();
        trash.clear();
        return n;
    }
}
