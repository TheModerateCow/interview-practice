# Car rental fleet desk

You're building the in-memory fleet desk for a car-rental company with several branches. It tracks every car's class and where it is parked, hands cars out and takes them back, and later grows pricing, one-way rentals and reservations made ahead of time. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{RentalDesk}}` type. Keep building on it: later levels add methods to it. Standard library only.

**Timestamps.** Every method takes `{{ts}}` (an integer) as its first argument: the time of the call, in **hours**. Timestamps never go down from one call to the next. Level 1 doesn't use them yet, but keep them in the signatures.

**Classes.** A car's class is `"economy"`, `"compact"` or `"suv"`; any other string (including `"SUV"`) is invalid. Branches are plain names such as `"downtown"`.

## Level 1: cars and rentals

| Method | Behaviour |
|---|---|
| `{{add_car}}({{ts}}, {{car_id}}, {{car_class}}, {{branch}})` | Adds a car parked at `{{branch}}`. Returns `false` if `{{car_id}}` already exists or `{{car_class}}` is invalid. |
| `{{rent}}({{ts}}, {{customer}}, {{branch}}, {{car_class}}, {{days}})` | Hands `{{customer}}` a car of `{{car_class}}` parked at `{{branch}}` for `{{days}}` days and returns its id: the **lowest car id** among those cars (plain string order, so `"c10"` comes before `"c2"`). Returns `""`, changing nothing, if `{{car_class}}` is invalid, `{{days}} <= 0`, `{{customer}}` already has a car out, or no such car is parked there. |
| `{{return_car}}({{ts}}, {{car_id}})` | The car comes back to the branch it was rented from and can be rented again. Returns `false` if the car doesn't exist or isn't rented. |
| `{{status}}({{ts}}, {{car_id}})` | `"available:<branch>"` for a parked car, `"rented:<customer>"` for a car that's out, `""` if the car doesn't exist. |

A customer whose car has come back can rent again.

### Example

```
{{add_car}}(1, "c2", "economy", "downtown")  -> true
{{add_car}}(1, "c1", "economy", "downtown")  -> true
{{add_car}}(1, "c3", "suv", "airport")       -> true
{{rent}}(2, "maya", "downtown", "economy", 3) -> "c1"
{{rent}}(3, "leo", "downtown", "economy", 1)  -> "c2"
{{rent}}(4, "ana", "downtown", "economy", 1)  -> ""     (no economy car left downtown)
{{status}}(5, "c1")                           -> "rented:maya"
{{return_car}}(6, "c1")                       -> true
{{status}}(7, "c1")                           -> "available:downtown"
{{rent}}(8, "ana", "downtown", "economy", 2)  -> "c1"
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
