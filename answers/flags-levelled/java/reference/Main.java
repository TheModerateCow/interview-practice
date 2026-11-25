// Drives the flag service from stdin, one command per line, and prints each result:
//
//   create <ts> <flag>
//   set <ts> <flag> <env> on|off
//   target <ts> <flag> <env> <user>
//   untarget <ts> <flag> <env> <user>
//   check <ts> <flag> <env> <user>
//
// Add your own commands here as you build later levels.
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class Main {
    public static void main(String[] args) throws IOException {
        FlagService svc = new FlagService();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line; (line = in.readLine()) != null; ) {
            String[] f = line.trim().split("\\s+");
            if (f.length < 3) continue;
            int ts = Integer.parseInt(f[1]);
            if (f[0].equals("create") && f.length == 3) System.out.println(svc.createFlag(ts, f[2]));
            else if (f[0].equals("set") && f.length == 5) System.out.println(svc.setEnabled(ts, f[2], f[3], f[4].equals("on")));
            else if (f[0].equals("target") && f.length == 5) System.out.println(svc.addTarget(ts, f[2], f[3], f[4]));
            else if (f[0].equals("untarget") && f.length == 5) System.out.println(svc.removeTarget(ts, f[2], f[3], f[4]));
            else if (f[0].equals("check") && f.length == 5) System.out.println(svc.isEnabled(ts, f[2], f[3], f[4]));
            else System.out.println("unknown command: " + line);
        }
    }
}
