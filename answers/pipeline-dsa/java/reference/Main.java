// Reads one pipeline from stdin and prints Pipeline.fastestRelease's answer:
//   n k
//   consumer cold warm      (n lines, one per job; consumer -1 is the release)
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class Main {
    public static void main(String[] args) throws IOException {
        String[] tok = new String(System.in.readAllBytes()).trim().split("\\s+");
        int p = 0;
        int n = Integer.parseInt(tok[p++]), k = Integer.parseInt(tok[p++]);
        List<Job> jobs = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            int consumer = Integer.parseInt(tok[p++]);
            int cold = Integer.parseInt(tok[p++]);
            int warm = Integer.parseInt(tok[p++]);
            jobs.add(new Job(consumer, cold, warm));
        }
        System.out.println(Pipeline.fastestRelease(jobs, k));
    }
}
