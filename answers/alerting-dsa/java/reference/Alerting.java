public class Alerting {
    /** Longest run of consecutive minutes whose pooled error rate is within budget:
     *  total errors * 1_000_000 <= total requests * budgetPpm. */
    public static int longestCompliantWindow(int[] requests, int[] errors, int budgetPpm) {
        int n = requests.length;
        // Minute i weighs errors*1e6 - requests*budget; a window is compliant when its weights sum to <= 0,
        // i.e. prefix[j] <= prefix[i] for the window covering minutes i..j-1. Sums reach 2e17: use long.
        long[] prefix = new long[n + 1];
        for (int i = 0; i < n; i++) {
            prefix[i + 1] = prefix[i] + (long) errors[i] * 1_000_000L - (long) requests[i] * budgetPpm;
        }
        // Only a running maximum of prefix can be the best start: an earlier start that is at least as high wins.
        int[] starts = new int[n + 1];
        int top = 0;
        for (int i = 0; i <= n; i++) {
            if (top == 0 || prefix[i] > prefix[starts[top - 1]]) starts[top++] = i;
        }
        int best = 0;
        for (int j = n; j >= 0 && top > 0; j--) {
            while (top > 0 && prefix[starts[top - 1]] >= prefix[j]) {
                best = Math.max(best, j - starts[--top]);
            }
        }
        return best;
    }
}
