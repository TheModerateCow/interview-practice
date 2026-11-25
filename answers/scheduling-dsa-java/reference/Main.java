// Reads a scheduling request from stdin and prints the earliest start (or -1).
// Format (whitespace-separated numbers):
//   n days duration quorum
//   then for each of the n attendees: offset workStart workEnd m, followed by m pairs "start end"
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class Main {
    public static void main(String[] args) throws IOException {
        String[] tok = new String(System.in.readAllBytes()).trim().split("\\s+");
        int p = 0;
        int n = Integer.parseInt(tok[p++]), days = Integer.parseInt(tok[p++]);
        int duration = Integer.parseInt(tok[p++]), quorum = Integer.parseInt(tok[p++]);
        List<Attendee> attendees = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            int offset = Integer.parseInt(tok[p++]), workStart = Integer.parseInt(tok[p++]);
            int workEnd = Integer.parseInt(tok[p++]), m = Integer.parseInt(tok[p++]);
            int[][] busy = new int[m][];
            for (int j = 0; j < m; j++) busy[j] = new int[]{Integer.parseInt(tok[p++]), Integer.parseInt(tok[p++])};
            attendees.add(new Attendee(offset, workStart, workEnd, busy));
        }
        System.out.println(Scheduler.earliestQuorumSlot(attendees, days, duration, quorum));
    }
}
