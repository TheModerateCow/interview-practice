public class Roman {
    private static int val(char c) {
        switch (c) {
            case 'I': return 1; case 'V': return 5; case 'X': return 10; case 'L': return 50;
            case 'C': return 100; case 'D': return 500; case 'M': return 1000;
            default: throw new IllegalArgumentException("bad numeral: " + c);
        }
    }

    /** Roman numeral to int; subtractive pairs (IV, IX, XL, ...) supported; bad input throws IllegalArgumentException. */
    public static int toInt(String s) {
        if (s == null || s.isEmpty()) throw new IllegalArgumentException("empty");
        int total = 0;
        for (int i = 0; i < s.length(); i++) {
            int v = val(s.charAt(i));
            if (i + 1 < s.length() && v < val(s.charAt(i + 1))) total -= v; else total += v;
        }
        return total;
    }
}
