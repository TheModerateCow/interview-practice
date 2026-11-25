// An example to copy. Run your tests with the My tests button.
public class ExampleTest {
    static void test_example_checkout() {
        var lib = new Library();
        Expect.isTrue(lib.addMember(1, "m-7"));
        Expect.isTrue(lib.addCopy(2, "B-1", "Beowulf"));
        Expect.eq("B-1", lib.checkout(3, "m-7", "Beowulf"));
        Expect.eq("m-7", lib.borrower(4, "B-1"));
    }
}
