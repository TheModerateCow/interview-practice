# Dispatch service

You've joined the team that runs order dispatch for a food-delivery platform. This small Java 21 program (default package, standard library only) is the in-memory core of one delivery zone: couriers come on shift, customers place orders, dispatch hands each order to a courier, couriers move it through `placed → assigned → picked_up → delivered` (or `cancelled`), and the tracking page shows an ETA.

Positions are metres on a street grid, so distances are Manhattan distances. Times are whole minutes since the start of the shift. Couriers ride at a planning speed of 250 m/min.

The round has three phases: fix the bugs, build the missing feature, then (revealed later) make the hot path fast. Read around before you change anything: the code is small, and the causes are rarely in the file where the symptom shows.

## Phase 1: bug report

> **DISP-412: support escalations from Friday's shift**
>
> 1. **ETAs are early.** Customers say the tracking page promised 12 minutes and the food took 13. It happens on most orders, not all. Riders confirm the routes were the expected length.
> 2. **Cancellations block couriers.** After a customer cancels an order that already had a courier, that courier stops receiving orders: `assign` throws "no courier available" even when the courier is idle, and their bag still lists the cancelled order.
> 3. **Retried checkouts reset live orders.** The checkout service retries `placeOrder` with the same order id when a request times out. Orders that are already assigned, sometimes already on the road, show up again as `placed`, and get assigned a second time.
>
> Expected: an ETA leg never rounds in the customer's favour; cancelling frees the courier's slot; placing an order with an id that already exists throws `DispatchException` (`DUPLICATE_ORDER`) and changes nothing.

This test reproduces item 2 and fails today. Paste it into a `*Test.java` file to use it:

```java
public class CancelTest {
    static void testCancelFreesRider() {
        Dispatcher d = new Dispatcher();
        d.addCourier("rider-7", new Point(0, 0), 1);
        d.placeOrder("a", new Point(200, 0), new Point(200, 600), 0, 10);
        d.placeOrder("b", new Point(300, 0), new Point(900, 0), 2, 10);
        d.assign("a");
        d.advance("a", State.CANCELLED);
        Expect.eq("rider-7", d.assign("b"));
    }
}
```

## Phase 2: automatic dispatch

`List<Assignment> dispatchPending(int now)` (it calls `Batch.dispatchPending` in `Batch.java`) is the dispatch loop's tick, called every minute. It is not implemented yet. It must:

1. Consider only orders that are still `placed`.
2. Hold back an order until its food is nearly ready: an order is **due** when `readyAt() - now <= Batch.DISPATCH_WINDOW` (10 minutes). Orders whose food is already ready are due.
3. Hand out due orders in order of `readyAt()`, soonest first; orders ready in the same minute go in order-id order. (Food that's ready first should be picked up first, even if it was ordered later.)
4. Give each order to a courier exactly as `assign` would: the nearest courier with room who is within `Dispatcher.MAX_PICKUP_DISTANCE` of the restaurant, ties to the lower courier id. Earlier hand-outs in the same tick count against a courier's capacity.
5. Leave an order `placed` if no courier can take it; a later tick tries again.
6. Return the assignments made, in the order they were made, as `Assignment(orderId, courierId)`. Return an empty (non-null) list when nothing was assigned.

Example:

```
addCourier("solo", Point(0, 0), 1)
placeOrder("early", Point(0, 0), Point(500, 0), 0, 20)   // ready at 20
placeOrder("late",  Point(0, 0), Point(0, 500), 5, 5)    // ready at 10
dispatchPending(10) -> [Assignment(late, solo)]            // "early" stays placed
```

## Checking your work

- **Run** runs `Main.java`, a small program that reads commands from stdin (`courier`, `order`, `assign`, `advance`, `eta`, `dispatch`, `bag`; see the top of the file). Extend it as you like.
- **My tests** runs your own `*Test.java` files: every `static void` method whose name starts with `test`, checked with `Expect.eq`, `Expect.isTrue` and `Expect.raises` (no JUnit). `ExampleTest.java` is an example to copy; the test above is a good first one to add.
- **Submit** runs the hidden tests for the phases you've unlocked. Phase 3 opens once phase 2 passes, or with 15 minutes left.
