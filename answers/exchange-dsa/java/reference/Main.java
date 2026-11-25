// Reads events from stdin and prints runBook's answers, one per line:
//   m                      (number of events)
//   add <price> <qty> | cancel <price> <qty> | quote <qty> | buy <qty>   (m lines)
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

public class Main {
    public static void main(String[] args) throws IOException {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        int m = Integer.parseInt(in.readLine().trim());
        List<Event> events = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            String[] w = in.readLine().trim().split("\\s+");
            if (w[0].equals("add") || w[0].equals("cancel")) {
                events.add(new Event(w[0], Long.parseLong(w[1]), Long.parseLong(w[2])));
            } else {
                events.add(new Event(w[0], 0, Long.parseLong(w[1])));
            }
        }
        StringBuilder sb = new StringBuilder();
        for (long v : Book.runBook(events)) sb.append(v).append('\n');
        System.out.print(sb);
    }
}
