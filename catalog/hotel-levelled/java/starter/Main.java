// Drives the hotel from stdin, one command per line, and prints each result:
//
//   room <day> <room_id> <room_type> <rate>
//   book <day> <guest> <room_id> <check_in> <check_out>
//   cancel <day> <booking_id>
//   cost <day> <booking_id>
//
// A failed book prints an empty line. Add your own commands here as you build later levels.
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class Main {
    public static void main(String[] args) throws IOException {
        Hotel h = new Hotel();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line; (line = in.readLine()) != null; ) {
            String[] f = line.trim().split("\\s+");
            if (f.length < 3) continue;
            int day = Integer.parseInt(f[1]);
            if (f[0].equals("room") && f.length == 5) System.out.println(h.addRoom(day, f[2], f[3], Integer.parseInt(f[4])));
            else if (f[0].equals("book") && f.length == 6) System.out.println(h.book(day, f[2], f[3], Integer.parseInt(f[4]), Integer.parseInt(f[5])));
            else if (f[0].equals("cancel") && f.length == 3) System.out.println(h.cancel(day, f[2]));
            else if (f[0].equals("cost") && f.length == 3) System.out.println(h.cost(day, f[2]));
            else System.out.println("unknown command: " + line);
        }
    }
}
