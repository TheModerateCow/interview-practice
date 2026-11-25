// Drives the box office from stdin, one command per line, and prints each result:
//
//   create <ts> <event> <capacity>
//   buy <ts> <event> <buyer> <qty>
//   refund <ts> <event> <buyer> <qty>
//   available <ts> <event>
//
// Add your own commands here as you build later levels.
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class Main {
    public static void main(String[] args) throws IOException {
        Office o = new Office();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line; (line = in.readLine()) != null; ) {
            String[] f = line.trim().split("\\s+");
            if (f.length < 3) continue;
            int ts = Integer.parseInt(f[1]);
            if (f[0].equals("create") && f.length == 4) System.out.println(o.createEvent(ts, f[2], Integer.parseInt(f[3])));
            else if (f[0].equals("buy") && f.length == 5) System.out.println(o.buy(ts, f[2], f[3], Integer.parseInt(f[4])));
            else if (f[0].equals("refund") && f.length == 5) System.out.println(o.refund(ts, f[2], f[3], Integer.parseInt(f[4])));
            else if (f[0].equals("available") && f.length == 3) System.out.println(o.available(ts, f[2]));
            else System.out.println("unknown command: " + line);
        }
    }
}
