// Drives the clinic from stdin, one command per line, and prints each result:
//
//   clinician <ts> <id>                              prints true or false
//   room <ts> <id>                                   prints true or false
//   type <ts> <name> <minutes>                       prints true or false
//   book <ts> <clinician> <patient> <type> <start>   prints the appointment id, or (failed)
//   cancel <ts> <id>                                 prints true or false
//   show <ts> <id>                                   prints the appointment, or (none)
//
// Add your own commands as you build later levels.
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class Main {
    public static void main(String[] args) throws IOException {
        Clinic c = new Clinic();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line; (line = in.readLine()) != null; ) {
            String[] f = line.trim().split("\\s+");
            if (f.length < 3) continue;
            int ts = Integer.parseInt(f[1]);
            int n = Integer.parseInt(f[f.length - 1].matches("-?\\d+") ? f[f.length - 1] : "0");
            if (f[0].equals("clinician") && f.length == 3) System.out.println(c.addClinician(ts, f[2]));
            else if (f[0].equals("room") && f.length == 3) System.out.println(c.addRoom(ts, f[2]));
            else if (f[0].equals("type") && f.length == 4) System.out.println(c.addType(ts, f[2], n));
            else if (f[0].equals("book") && f.length == 6) {
                String id = c.book(ts, f[2], f[3], f[4], n);
                System.out.println(id == null ? "(failed)" : id);
            } else if (f[0].equals("cancel") && f.length == 3) System.out.println(c.cancel(ts, f[2]));
            else if (f[0].equals("show") && f.length == 3) {
                String s = c.appointment(ts, f[2]);
                System.out.println(s == null ? "(none)" : s);
            } else System.out.println("unknown command: " + line);
        }
    }
}
