public class HiddenTest {
    static void test_p1_simple() {
        Expect.eq(3, Roman.toInt("III"));
        Expect.eq(1000, Roman.toInt("M"));
    }
    static void test_p1_subtractive() {
        Expect.eq(4, Roman.toInt("IV"));
        Expect.eq(9, Roman.toInt("IX"));
        Expect.eq(40, Roman.toInt("XL"));
        Expect.eq(900, Roman.toInt("CM"));
    }
    static void test_p1_long() {
        Expect.eq(1994, Roman.toInt("MCMXCIV"));
        Expect.eq(58, Roman.toInt("LVIII"));
    }
    static void test_p1_empty_raises() {
        Expect.raises(IllegalArgumentException.class, () -> Roman.toInt(""));
        Expect.raises(IllegalArgumentException.class, () -> Roman.toInt(null));
    }
    static void test_p1_bad_char_raises() {
        Expect.raises(IllegalArgumentException.class, () -> Roman.toInt("XAI"));
    }
}
