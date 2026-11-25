// Reads one network from stdin and prints fastestDelivery's answer:
//   n m capacity charge
//   rate_0 rate_1 ... rate_{n-1}
//   a b minutes energy      (m lines, one per road)
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class Main {
    public static void main(String[] args) throws IOException {
        String[] tok = new String(System.in.readAllBytes()).trim().split("\\s+");
        int p = 0;
        int n = Integer.parseInt(tok[p++]), m = Integer.parseInt(tok[p++]);
        int capacity = Integer.parseInt(tok[p++]), charge = Integer.parseInt(tok[p++]);
        int[] rate = new int[n];
        for (int i = 0; i < n; i++) rate[i] = Integer.parseInt(tok[p++]);
        List<Road> roads = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            roads.add(new Road(Integer.parseInt(tok[p++]), Integer.parseInt(tok[p++]),
                    Integer.parseInt(tok[p++]), Integer.parseInt(tok[p++])));
        }
        System.out.println(Route.fastestDelivery(n, capacity, charge, rate, roads));
    }
}
