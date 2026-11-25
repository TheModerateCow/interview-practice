# Transit fares (TDD)

You're building the fare engine for a city's tap-to-ride travel card. Each ride is recorded on the rider's card as it happens, and the card decides how much to charge for it: zone-based fares, a peak uplift, concession discounts, transfers that join several rides into one journey, and daily and weekly caps. All amounts are integer **cents**.

This is a **test-driven** round. Work in this order:

1. Write your tests first, in a `*Test.java` file (`ExampleTest.java` shows the style; copy it). There is no JUnit: every `static void` method whose name starts with `test` is run, and you check results with `Expect.eq(expected, actual)`, `Expect.isTrue(condition)` and `Expect.raises(IllegalArgumentException.class, () -> ...)`. Run them with **My tests**. They should fail against the stub.
2. Then implement `Fares.java` and `FareCard.java` until your tests pass.
3. **Submit** runs the hidden tests against your implementation. Your own tests are judged too: afterwards they are run against a correct implementation (they must all pass) and against several subtly wrong ones (the more they catch, the better).

Java 21, standard library only, default package. Keep the class names, method signatures and `Concession` enum as given. Name your helpers as you like, but avoid names starting with `hidden`.

## API

```java
enum Concession { ADULT, CHILD, SENIOR }                 // given
static boolean Fares.isPeak(int time)
static int Fares.journeyFare(int zones, boolean peak, Concession c)
class FareCard {
    FareCard(Concession concession)
    int ride(int time, int fromZone, int toZone)          // cents charged for this ride
}
```

Errors are thrown as `IllegalArgumentException` with exactly the messages below.

**Time** is an int number of minutes since Monday 00:00 of week 0, passed in by the caller. The day number is `time / 1440`: days 0-4 are Monday-Friday, 5 is Saturday, 6 is Sunday, 7 is the next Monday, and so on. The minute of the day is `time % 1440`.

## Fares.isPeak

A time is **peak** on Monday-Friday when the minute of the day is in 07:00-09:30 or 16:00-19:00, start included, end excluded (07:00 is peak, 09:30 is not). Saturdays and Sundays are never peak.

## Fares.journeyFare

Computed in exactly this order:

1. **Base fare** by the number of zones (1-6):

   | Zones | 1 | 2 | 3 | 4 | 5 | 6 |
   |---|---|---|---|---|---|---|
   | Cents | 250 | 320 | 410 | 480 | 550 | 620 |

2. **Peak uplift**: if `peak`, multiply by 1.30 and round **up** to the next multiple of 10 cents (a multiple of 10 stays as it is).
3. **Concession**: `ADULT` pays 100%, `CHILD` 50%, `SENIOR` 70% of the step-2 amount, rounded **down** to a multiple of 5 cents.

## FareCard

`new FareCard(null)` throws `IllegalArgumentException("unknown concession")`.

### `ride(time, fromZone, toZone)`

**Validation**, in this order; the first failure is thrown and the ride is not recorded (the card's state does not change):

1. `time` is negative, or earlier than the previous recorded ride's time: `"invalid time"`. Equal times are allowed.
2. `fromZone` or `toZone` is not from 1 to 6: `"invalid zone"`.

A ride covers the zones from `min(fromZone, toZone)` to `max(fromZone, toZone)`, both included; direction does not matter.

**Journeys.** Rides are grouped into journeys. A ride **joins the current journey** (a transfer) when both hold:

- its `time` is less than 90 minutes after the time of the journey's **first** ride (89 joins, 90 does not), and
- the journey has fewer than 3 rides so far.

Otherwise the ride starts a new journey. The first ride on a card always starts one.

A journey covers the zones from the lowest to the highest zone of all its rides (zones in between count even if no ride touched them). It is **peak** if, and only if, its first ride's time is peak; later rides do not change that.

**Amount due** for a ride: the `journeyFare` of the journey's zone count, peak status and the card's concession, **after** adding this ride, minus the `journeyFare` of the journey **before** this ride (0 for a ride that starts a new journey). Both are computed with the journey's peak status. A transfer that adds no new zones is due 0.

**Caps**, applied to the amount due:

- A **service day** runs from 04:00 to 04:00: a ride belongs to service day `Math.floorDiv(time - 240, 1440)` (a ride at 02:00 on Tuesday belongs to Monday's service day). A **service week** is `Math.floorDiv(serviceDay, 7)`, Monday 04:00 to the next Monday 04:00.
- Daily and weekly caps per concession:

  | Concession | Daily cap | Weekly cap |
  |---|---|---|
  | ADULT | 1200 | 4800 |
  | CHILD | 600 | 2400 |
  | SENIOR | 840 | 3360 |

- The **charge** is the amount due, reduced so that neither the total charged in the ride's service day nor the total charged in its service week goes above its cap (a partial charge is possible), and never below 0. Each ride's charge counts toward the service day and week of that ride's own time, even when it is a transfer in a journey that began on an earlier service day.

`ride` returns the charge.

## Examples

```text
isPeak(420) -> true (Monday 07:00)     isPeak(570) -> false (Monday 09:30)     isPeak(7680) -> false (Saturday 08:00)
journeyFare(4, true, ADULT)  -> 630   480 × 1.30 = 624 -> 630
journeyFare(1, true, SENIOR) -> 230   250 × 1.30 = 325 -> 330; 70% = 231 -> 230

new FareCard(ADULT):
ride(480, 1, 2)   -> 420   Monday 08:00, new peak journey, 2 zones
ride(520, 2, 4)   -> 210   transfer (40 min): journey now zones 1-4, 630 - 420
ride(560, 4, 4)   -> 0     transfer (80 min): no new zones
ride(570, 1, 1)   -> 250   journey already has 3 rides: new journey, 09:30 is off-peak

new FareCard(CHILD):
ride(1050, 1, 6)  -> 405   Monday 17:30, peak, 6 zones
ride(1170, 6, 1)  -> 195   Monday 19:30, off-peak 310, capped at 600 for the day
ride(1590, 1, 1)  -> 0     Tuesday 02:30 still belongs to Monday's service day
ride(1690, 1, 1)  -> 125   Tuesday 04:10, a new service day

new FareCard(SENIOR):
ride(7680, 3, 1)  -> 285   Saturday 08:00, off-peak, 3 zones
ride(7700, 1, 5)  -> 100   transfer: 5 zones 385 - 285
```

## Checking your work

- **My tests** runs your own `*Test.java` files against your code. `ExampleTest.java` is an example to copy.
- **Submit** runs the hidden tests against your `Fares.java` and `FareCard.java`.
