// Drives the garage from stdin, one command per line, and prints each result
// (strings are printed quoted, so an empty result shows as ""):
//
//   add <ts> <spot> <size>
//   park <ts> <plate> <size>
//   leave <ts> <plate>
//   spot <ts> <plate>
//
// Add your own commands here as you build later levels.
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class Main {
    public static void main(String[] args) throws IOException {
        Garage g = new Garage();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line; (line = in.readLine()) != null; ) {
            String[] f = line.trim().split("\\s+");
            if (f.length < 3) continue;
            int ts = Integer.parseInt(f[1]);
            if (f[0].equals("add") && f.length == 4) System.out.println(g.addSpot(ts, f[2], f[3]));
            else if (f[0].equals("park") && f.length == 4) System.out.println("\"" + g.park(ts, f[2], f[3]) + "\"");
            else if (f[0].equals("leave") && f.length == 3) System.out.println(g.leave(ts, f[2]));
            else if (f[0].equals("spot") && f.length == 3) System.out.println("\"" + g.spotOf(ts, f[2]) + "\"");
            else System.out.println("unknown command: " + line);
        }
    }
}
