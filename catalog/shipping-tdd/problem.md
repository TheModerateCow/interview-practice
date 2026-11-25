# Shipping quotes (TDD)

You're building the shipping calculator for an online shop: given an order's parcels, destination zone, basket subtotal, delivery speed and promo code, it returns the shipping price in cents. All amounts are integer **cents** and all weights integer **grams**.

This is a **test-driven** round. Work in this order:

1. Write your tests first, in your own test file (the example test in the starter, `{{your_tests}}`, shows the style; copy it). Run them with **My tests**. They should fail against the stub.
2. Then implement the calculator until your tests pass.
3. **Submit** runs the hidden tests against your implementation. Your own tests are judged too: afterwards they are run against a correct implementation (they must all pass) and against several subtly wrong ones (the more they catch, the better).

Name your test helpers as you like, but avoid names starting with `hidden`. Keep the types, function signatures and error kinds in the starter as given.

## API

`{{billable_grams}}(parcel)` and `{{quote}}(order)`. A `Parcel` has `{{weight_grams}}`, `{{length_cm}}`, `{{width_cm}}` and `{{height_cm}}`. An `Order` has `{{parcels}}` (a list of parcels), `{{zone}}`, `{{subtotal_cents}}` (never negative), `{{express}}` and `{{promo_code}}`. On an error, return no price and fail with one of the error kinds given.

## {{billable_grams}}

1. If the weight or any dimension is `<= 0`: `{{invalid_parcel}}`.
2. **Dimensional weight** = `L × W × H / 5` grams, rounded **up** to a whole gram.
3. Take the larger of the actual weight and the dimensional weight, then round it **up** to the next multiple of 500 g. A value that is already a multiple of 500 stays as it is (1000 → 1000, 1001 → 1500).
4. If that billable weight is over 30000 g: `{{too_heavy}}`. Exactly 30000 g is allowed.

## {{quote}}

**Validation**, checked in this order; the first failure is returned:

1. No parcels: `{{no_parcels}}`.
2. Zone not 1, 2, 3 or 4: `{{unknown_zone}}`.
3. Promo code not `""`, `"SHIP10"` or `"FLAT600"` (exact, case-sensitive): `{{unknown_promo}}`.
4. Each parcel in list order, using `{{billable_grams}}`'s rules: the first parcel that fails decides the error.

**Price**, computed in exactly this order:

1. **Base rate** of each parcel from its billable weight: the zone's price for the first 1000 g, plus the zone's step price for each further 500 g. A 500 g parcel pays the first-1000 g price.

   | Zone | First 1000 g | Each further 500 g |
   |---|---|---|
   | 1 | 500 | 100 |
   | 2 | 650 | 140 |
   | 3 | 800 | 180 |
   | 4 | 1100 | 250 |

2. **Express**: if `{{express}}`, each parcel's base rate is multiplied by 1.35 and rounded **half up** to a whole cent, per parcel.
3. **Free shipping** applies when `{{subtotal_cents}} >= 7500`, the zone is 1, 2 or 3, and the order is **not** express. It sets every parcel's base rate to 0. It does not waive the oversize surcharge.
4. **Oversize surcharge**: a parcel whose longest side is over 100 cm adds 1500 to its charge. It is never multiplied by express. A 100 cm side is not oversize.
5. **Sum** the parcel charges (base rate + surcharge).
6. **Fuel surcharge**: add 8.5% of the sum, rounded **half up** to a whole cent, once for the whole order.
7. **Promo**, on the total after fuel:
   - `SHIP10`: 10% off the total; the discount is rounded **down** to a whole cent.
   - `FLAT600`: 600 off the total, never below 0. It is **ignored** (no error) when free shipping applies.

The result of step 7 is the quote.

## Examples

```
a = parcel(weight 2200, 20 x 20 x 20)       // billable 2500 g
b = parcel(weight 1000, 110 x 20 x 10)      // billable 4500 g (dimensional 4400), oversize

{{billable_grams}}(parcel(400, 30 x 20 x 10))  -> 1500   (dimensional 1200 g beats 400 g, rounded up to 1500)

{{quote}}(parcels [a], zone 2)                                                   -> 1161
    base 650 + 3×140 = 1070; fuel 90.95 -> 91
{{quote}}(parcels [a], zone 2, express, promo "SHIP10")                          -> 1412
    1070 × 1.35 = 1444.5 -> 1445; fuel 122.825 -> 123; 1568 - 156 = 1412
{{quote}}(parcels [a, b], zone 3, subtotal 8000, promo "FLAT600")                -> 1628
    free shipping: bases 0; b's oversize 1500; fuel 127.5 -> 128; FLAT600 ignored
{{quote}}(parcels [a, b], zone 3, subtotal 8000, express, promo "FLAT600")       -> 6008
    express, so no free shipping: 1809 + (2781 + 1500) = 6090; fuel 517.65 -> 518; 6608 - 600
```

## Checking your work

- **My tests** runs your own `{{your_tests}}` files against your code. The starter's example test is one to copy.
- **Submit** runs the hidden tests against your code.
