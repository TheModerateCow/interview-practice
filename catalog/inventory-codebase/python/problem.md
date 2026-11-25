# Warehouse inventory

You've joined the team that owns the **inventory service** of an online retailer with several warehouses. Stock lives in bins. When a customer checks out, the store places a **reservation**: a hold on stock that lasts until the order ships (it is *committed*: picked from the bins), until it is cancelled (*released*), or until its time-to-live runs out (it *expires*). Stock also moves between warehouses as **transfers**, and each warehouse has **replenishment rules** that say when a SKU needs restocking.

*On hand* is what is physically in a warehouse's bins. *Available* is on hand minus what active reservations hold, and it's what the storefront may still promise. Quantities are whole units and times are Unix seconds. Every call that takes `now` moves the service clock forward and expires the holds whose time has run out. `now` may never go backwards (`Backdated`).

The code is Python package `inventory` (standard library only): the `Service` and its stock calls (`service.py`), an in-memory store with per-SKU counters and a cached pick path (`store.py`), reservation expiry, reservations, transfers, replenishment, and a small stdin driver in `main.py`. Read around before you change anything.

The round has **3 phases**: fix the bugs below, build replenishment planning, then a third part that opens once phase 2 passes (or with 15 minutes left, or when you press **Next part**).

## Phase 1: bug report

> **INV-207 · three reports from the warehouses this week**
>
> 1. **Overselling after late cancellations.** For a few SKUs the storefront showed more stock available than was on the shelves. At one point east showed 14 `LAMP` available with only 10 on hand, and we took orders we couldn't ship. It seems to follow cancellations that arrive late, after the checkout hold would have run out anyway, but not every late cancellation does it.
> 2. **"Short pick" with stock on the shelf.** Pickers at east got `ShortPick` committing a `TOWEL` order while `on_hand` said 12 and `bin_qty` showed towels sitting in bin `A-09`. Those towels had been put away into a bin that never held towels before. Another time it was a transfer from west, received into a fresh bin. SKUs that had never been picked before were fine.
> 3. **A transfer took stock that was promised to customers.** East had 10 chairs, 8 of them held for orders, and a transfer of 5 chairs to west still went through. East's available went to −3 and one of those orders then failed to ship.

This test reproduces item 1 and fails today. Paste it into a `test_*.py` file to use it:

```python
def test_late_cancellation():
    s = Service()
    s.add_warehouse("east")
    s.receive("east", "A-01", "LAMP", 10, 100)
    s.reserve("o1", "east", "LAMP", 4, 300, 200)  # the hold runs out at 500
    s.release("o1", 650)                          # the order service cancels late
    assert s.available("east", "LAMP", 700) == 10
```

Fix the cause of each one, not just the symptom.

## Phase 2: replenishment planning

Implement `replenishment` in `inventory/replenish.py`:

```python
def replenishment(self, warehouse: str, now: int) -> list[Suggestion]
```

It plans restocking for one warehouse at time `now` (`Suggestion` has `sku`, `position`, `qty` and `source`). It only plans: nothing is moved or ordered.

- **Errors.** An unknown warehouse returns `UnknownWarehouse`. A `now` older than the service clock returns `Backdated`. Like every call that takes `now`, it moves the clock forward first, so holds that run out by `now` no longer count.
- **Which SKUs.** Only SKUs with a `Rule` for this warehouse (set with `set_rule`), one `Suggestion` each at most, sorted by SKU.
- **Stock position.** A SKU's position is its *available* stock in the warehouse plus what is *inbound*: units in transfers to this warehouse that have been started but not yet received. Once a transfer is received its units are on hand, so they are counted once, not twice.
- **When and how much.** Suggest a SKU when its position is **at or below** the rule's `min`. `qty` is `max - position`, rounded **up** to a multiple of `pack` when `pack > 1`. `position` in the suggestion is the position you computed.
- **Where from.** `source` is the other warehouse that can best spare the units. A warehouse's surplus for the SKU is its available stock minus its own rule's `min` for that SKU (0 if it has no rule). Pick the warehouse with the largest surplus that is at least `qty`, lowest warehouse ID on a tie. If none can, `source` is `""` (buy from the supplier).

### Example

```
add_warehouse("east"); add_warehouse("west")
receive("east", "A-01", "BOOT", 4, 0)
receive("west", "W-01", "BOOT", 45, 0)
set_rule("east", "BOOT", Rule(min=10, max=30, pack=1))
set_rule("west", "BOOT", Rule(min=15, max=60))
set_rule("east", "SOCK", Rule(min=20, max=100, pack=25))
reserve("o1", "east", "BOOT", 2, 600, 5)          # held until 605
replenishment("east", 10) ->
  Suggestion(sku="BOOT", position=2, qty=28, source="west")   # west can spare 45 - 15 = 30
  Suggestion(sku="SOCK", position=0, qty=100, source="")
start_transfer("t1", "west", "east", "BOOT", 5, 20)
replenishment("east", 605) ->                     # o1 has run out; 5 boots inbound
  Suggestion(sku="BOOT", position=9, qty=21, source="west")
  Suggestion(sku="SOCK", position=0, qty=100, source="")
```

## Checking your work

- **Run** runs `main.py`, which reads commands from stdin (`warehouse`, `rule`, `receive`, `reserve`, `release`, `commit`, `transfer`, `arrive`, `available`, `onhand`, `bin`, `replenish`; see the top of the file). Extend it as you like.
- **My tests** runs your own `test_*.py` files. `test_example.py` is an example to copy.
- **Submit** runs the hidden tests for every phase you've unlocked.
