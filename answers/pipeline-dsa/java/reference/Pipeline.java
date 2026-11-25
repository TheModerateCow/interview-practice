import java.util.ArrayList;
import java.util.List;

public class Pipeline {
    /** Fewest minutes until the release job finishes when at most k jobs are pre-warmed and every job
     *  starts as soon as all the jobs that feed it have finished; -1 if the consumer links contain a cycle. */
    public static int fastestRelease(List<Job> jobs, int k) {
        int n = jobs.size();
        k = Math.min(k, n);
        List<List<Integer>> inputs = new ArrayList<>();
        for (int i = 0; i < n; i++) inputs.add(new ArrayList<>());
        int root = -1;
        for (int i = 0; i < n; i++) {
            Job j = jobs.get(i);
            if (j.consumer() < 0) {
                root = i;
            } else {
                inputs.get(j.consumer()).add(i);
            }
        }
        if (root < 0) return -1;
        // BFS from the release over inputs; a job on a cycle is never reached.
        List<Integer> order = new ArrayList<>();
        order.add(root);
        for (int q = 0; q < order.size(); q++) order.addAll(inputs.get(order.get(q)));
        if (order.size() != n) return -1;
        // f[v][b]: fewest minutes to finish v using at most b warm caches in v's subtree. Inputs run in
        // parallel, so merging a child is a min-max split of the budget.
        int[][] f = new int[n][];
        for (int q = n - 1; q >= 0; q--) {
            int v = order.get(q);
            int[] g = new int[k + 1]; // inputs ready with at most b warm: 0 with no inputs
            for (int c : inputs.get(v)) {
                int[] fc = f[c];
                int[] ng = new int[k + 1];
                for (int b = 0; b <= k; b++) {
                    int best = -1;
                    for (int i = 0; i <= b; i++) {
                        int t = Math.max(g[b - i], fc[i]);
                        if (best < 0 || t < best) best = t;
                    }
                    ng[b] = best;
                }
                g = ng;
                f[c] = null;
            }
            Job job = jobs.get(v);
            int[] fv = new int[k + 1];
            for (int b = 0; b <= k; b++) {
                fv[b] = job.cold() + g[b];
                if (b > 0) fv[b] = Math.min(fv[b], job.warm() + g[b - 1]);
            }
            f[v] = fv;
        }
        return f[root][k];
    }
}
