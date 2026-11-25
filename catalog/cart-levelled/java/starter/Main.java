import java.util.Scanner;

/**
 * Drives the shop from stdin, one command per line, and prints each result:
 *
 *   product <ts> <sku> <priceCents> <stock>
 *   add <ts> <cart> <sku> <qty>
 *   remove <ts> <cart> <sku> <qty>
 *   total <ts> <cart>
 *   items <ts> <cart>
 *
 * Add your own commands here as you build later levels.
 */
public class Main {
    public static void main(String[] args) {
        Shop shop = new Shop();
        Scanner sc = new Scanner(System.in);
        while (sc.hasNextLine()) {
            String line = sc.nextLine().trim();
            String[] f = line.split("\\s+");
            if (f.length < 3) continue;
            int ts = Integer.parseInt(f[1]);
            if (f[0].equals("product") && f.length == 5) System.out.println(shop.addProduct(ts, f[2], Long.parseLong(f[3]), Integer.parseInt(f[4])));
            else if (f[0].equals("add") && f.length == 5) System.out.println(shop.addToCart(ts, f[2], f[3], Integer.parseInt(f[4])));
            else if (f[0].equals("remove") && f.length == 5) System.out.println(shop.removeFromCart(ts, f[2], f[3], Integer.parseInt(f[4])));
            else if (f[0].equals("total") && f.length == 3) System.out.println(shop.cartTotal(ts, f[2]));
            else if (f[0].equals("items") && f.length == 3) System.out.println(shop.items(ts, f[2]));
            else System.out.println("unknown command: " + line);
        }
    }
}
