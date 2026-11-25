// Drives the library from stdin, one command per line, and prints each result
// (strings are printed quoted, so an empty result shows as ""; titles are one word here):
//
//   member <ts> <member>
//   copy <ts> <copy> <title>
//   checkout <ts> <member> <title>
//   return <ts> <copy>
//   borrower <ts> <copy>
//
// Add your own commands here as you build later levels.
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class Main {
    static String q(String s) { return "\"" + s + "\""; }

    public static void main(String[] args) throws IOException {
        Library lib = new Library();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line; (line = in.readLine()) != null; ) {
            String[] f = line.trim().split("\\s+");
            if (f.length < 3) continue;
            int ts = Integer.parseInt(f[1]);
            if (f[0].equals("member") && f.length == 3) System.out.println(lib.addMember(ts, f[2]));
            else if (f[0].equals("copy") && f.length == 4) System.out.println(lib.addCopy(ts, f[2], f[3]));
            else if (f[0].equals("checkout") && f.length == 4) System.out.println(q(lib.checkout(ts, f[2], f[3])));
            else if (f[0].equals("return") && f.length == 3) System.out.println(lib.returnCopy(ts, f[2]));
            else if (f[0].equals("borrower") && f.length == 3) System.out.println(q(lib.borrower(ts, f[2])));
            else System.out.println("unknown command: " + line);
        }
    }
}
