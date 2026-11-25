// Reads "n m need", then n rider positions, then m driver positions (any whitespace),
// and prints Dispatch.minDispatchRadius.
import java.io.IOException;

public class Main {
    public static void main(String[] args) throws IOException {
        String[] tok = new String(System.in.readAllBytes()).trim().split("\\s+");
        int p = 0;
        int n = Integer.parseInt(tok[p++]), m = Integer.parseInt(tok[p++]), need = Integer.parseInt(tok[p++]);
        int[] riders = new int[n], drivers = new int[m];
        for (int i = 0; i < n; i++) riders[i] = Integer.parseInt(tok[p++]);
        for (int i = 0; i < m; i++) drivers[i] = Integer.parseInt(tok[p++]);
        System.out.println(Dispatch.minDispatchRadius(riders, drivers, need));
    }
}
