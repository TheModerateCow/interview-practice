// Reads the number of logged searches n, then n queries (one per line), then the target, and
// prints SearchBox.fewestKeystrokes(log, target).
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class Main {
    public static void main(String[] args) throws IOException {
        String[] tok = new String(System.in.readAllBytes()).trim().split("\\s+");
        int n = Integer.parseInt(tok[0]);
        List<String> log = new ArrayList<>();
        for (int i = 0; i < n; i++) log.add(tok[1 + i]);
        String target = tok[1 + n];
        System.out.println(SearchBox.fewestKeystrokes(log, target));
    }
}
