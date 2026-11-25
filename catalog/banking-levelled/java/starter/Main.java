// Drives the bank from stdin, one command per line, and prints each result:
//
//   open <ts> <id>
//   deposit <ts> <id> <amount>          prints the new balance, or (failed)
//   withdraw <ts> <id> <amount>         prints the new balance, or (failed)
//   transfer <ts> <from> <to> <amount>  prints the sender's new balance, or (failed)
//   balance <ts> <id>                   prints the balance, or (none)
//
// Add your own commands as you build later levels.
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

public class Main {
    // show prints an amount, or (failed) when the call was refused.
    static void show(Integer v) {
        System.out.println(v == null ? "(failed)" : v.toString());
    }

    static int num(String s) {
        return Integer.parseInt(s);
    }

    public static void main(String[] args) throws IOException {
        Bank b = new Bank();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line; (line = in.readLine()) != null; ) {
            String[] f = line.trim().split("\\s+");
            if (f.length < 2) continue;
            int ts = Integer.parseInt(f[1]);
            if (f[0].equals("open") && f.length == 3) System.out.println(b.openAccount(ts, f[2]));
            else if (f[0].equals("deposit") && f.length == 4) show(b.deposit(ts, f[2], num(f[3])));
            else if (f[0].equals("withdraw") && f.length == 4) show(b.withdraw(ts, f[2], num(f[3])));
            else if (f[0].equals("transfer") && f.length == 5) show(b.transfer(ts, f[2], f[3], num(f[4])));
            else if (f[0].equals("balance") && f.length == 3) {
                Integer v = b.balance(ts, f[2]);
                System.out.println(v == null ? "(none)" : v.toString());
            } else System.out.println("unknown command: " + line);
        }
    }
}
