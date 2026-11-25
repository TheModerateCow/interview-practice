// Reads "n capacity wear", then n half-hourly prices (any whitespace), and prints Meters.bestBatteryProfit.
import java.io.IOException;

public class Main {
    public static void main(String[] args) throws IOException {
        String[] tok = new String(System.in.readAllBytes()).trim().split("\\s+");
        int p = 0;
        int n = Integer.parseInt(tok[p++]), capacity = Integer.parseInt(tok[p++]), wear = Integer.parseInt(tok[p++]);
        int[] prices = new int[n];
        for (int i = 0; i < n; i++) prices[i] = Integer.parseInt(tok[p++]);
        System.out.println(Meters.bestBatteryProfit(prices, capacity, wear));
    }
}
