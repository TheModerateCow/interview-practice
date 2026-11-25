// An example to copy. Write your own tests first, run them with My tests,
// then implement Fares.java and FareCard.java.
// Every static void method whose name starts with "test" is run.
public class ExampleTest {
    static void testOneOffPeakAdultRideAcrossTwoZones() {
        FareCard card = new FareCard("adult");
        Expect.eq(320, card.ride(600, 1, 2)); // Monday 10:00
    }
}
