// Drives the store from stdin, one command per line, and prints each result:
//
//   set <ts> <key> <field> <value>
//   get <ts> <key> <field>                 prints the value, or (none)
//   delete <ts> <key> <field>
//   cas <ts> <key> <field> <expected> <value>
//
// Values are single words here. Add your own commands as you build later levels.
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class Main {
    public static void main(String[] args) throws IOException {
        Store s = new Store();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line; (line = in.readLine()) != null; ) {
            String[] f = line.trim().split("\\s+");
            if (f.length < 2) continue;
            int ts = Integer.parseInt(f[1]);
            if (f[0].equals("set") && f.length == 5) System.out.println(s.set(ts, f[2], f[3], f[4]));
            else if (f[0].equals("get") && f.length == 4) {
                String v = s.get(ts, f[2], f[3]);
                System.out.println(v == null ? "(none)" : v);
            }
            else if (f[0].equals("delete") && f.length == 4) System.out.println(s.delete(ts, f[2], f[3]));
            else if (f[0].equals("cas") && f.length == 6) System.out.println(s.compareAndSet(ts, f[2], f[3], f[4], f[5]));
            else System.out.println("unknown command: " + line);
        }
    }
}
