import java.io.*;
import java.util.*;

public class Main {
    // stdin: n m, then n capacities, then m lines "board alight". Prints the answer.
    public static void main(String[] args) throws IOException {
        StreamTokenizer in = new StreamTokenizer(new BufferedReader(new InputStreamReader(System.in)));
        in.nextToken(); int n = (int) in.nval;
        in.nextToken(); int m = (int) in.nval;
        int[] cap = new int[n];
        for (int i = 0; i < n; i++) { in.nextToken(); cap[i] = (int) in.nval; }
        int[][] req = new int[m][2];
        for (int i = 0; i < m; i++) {
            in.nextToken(); req[i][0] = (int) in.nval;
            in.nextToken(); req[i][1] = (int) in.nval;
        }
        System.out.println(Upgrades.maxUpgrades(cap, req));
    }
}
