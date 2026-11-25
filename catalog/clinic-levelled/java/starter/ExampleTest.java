// An example to copy. Run your tests with the My tests button.
public class ExampleTest {
    static void test_example_book_and_describe() {
        var c = new Clinic();
        c.addClinician(1, "dr-x");
        c.addRoom(2, "room-x");
        c.addType(3, "flu-shot", 15);
        String id = c.book(4, "dr-x", "pat-x", "flu-shot", 900);
        Expect.eq("appt1", id);
        Expect.eq("dr-x pat-x flu-shot room-x 900-915 booked", c.appointment(5, id));
    }
}
