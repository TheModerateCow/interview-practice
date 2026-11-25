// Reads "n budgetPPM", then n request counts, then n error counts (any whitespace),
// and prints Alerting.longestCompliantWindow.
import java.io.IOException;

public class Main {
    public static void main(String[] args) throws IOException {
        String[] tok = new String(System.in.readAllBytes()).trim().split("\\s+");
        int p = 0;
        int n = Integer.parseInt(tok[p++]), budget = Integer.parseInt(tok[p++]);
        int[] requests = new int[n], errors = new int[n];
        for (int i = 0; i < n; i++) requests[i] = Integer.parseInt(tok[p++]);
        for (int i = 0; i < n; i++) errors[i] = Integer.parseInt(tok[p++]);
        System.out.println(Alerting.longestCompliantWindow(requests, errors, budget));
    }
}
