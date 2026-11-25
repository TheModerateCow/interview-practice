# Warehouse inventory

You've joined the team that owns the **inventory service** of an online retailer with several warehouses. Stock lives in bins. When a customer checks out, the store places a **reservation**: a hold on stock that lasts until the order ships (it is *committed*: picked from the bins), until it is cancelled (*released*), or until its time-to-live runs out (it *expires*). Stock also moves between warehouses as **transfers**, and each warehouse has **replenishment rules** that say when a SKU needs restocking.

*On hand* is what is physically in a warehouse's bins. *Available* is on hand minus what active reservations hold, and it's what the storefront may still promise. Quantities are whole units and times are Unix seconds. Every call that takes `now` moves the service clock forward and expires the holds whose time has run out. `now` may never go backwards (`ErrBackdated`).

The code is Go package `inventory` (standard library only): the `Service` and its stock calls, an in-memory store with per-SKU counters and a cached pick path, reservation expiry, reservations, transfers, replenishment, and a small stdin driver in `cmd/run`. Read around before you change anything.

The round has **3 phases**: fix the bugs below, build replenishment planning, then a third part that opens once phase 2 passes (or with 15 minutes left, or when you press **Next part**).

## Phase 1: bug report

> **INV-207 · three reports from the warehouses this week**
>
> 1. **Overselling after late cancellations.** For a few SKUs the storefront showed more stock available than was on the shelves. At one point east showed 14 `LAMP` available with only 10 on hand, and we took orders we couldn't ship. It seems to follow cancellations that arrive late, after the checkout hold would have run out anyway, but not every late cancellation does it.
> 2. **"Short pick" with stock on the shelf.** Pickers at east got `ErrShortPick` committing a `TOWEL` order while `OnHand` said 12 and `BinQty` showed towels sitting in bin `A-09`. Those towels had been put away into a bin that never held towels before. Another time it was a transfer from west, received into a fresh bin. SKUs that had never been picked before were fine.
> 3. **A transfer took stock that was promised to customers.** East had 10 chairs, 8 of them held for orders, and a transfer of 5 chairs to west still went through. East's available went to −3 and one of those orders then failed to ship.

This test reproduces item 1 and fails today. Paste it into a `_test.go` file to use it:

```go
func TestLateCancellation(t *testing.T) {
	s := New()
	s.AddWarehouse("east")
	s.Receive("east", "A-01", "LAMP", 10, 100)
	s.Reserve("o1", "east", "LAMP", 4, 300, 200) // the hold runs out at 500
	s.Release("o1", 650)                         // the order service cancels late
	if got, _ := s.Available("east", "LAMP", 700); got != 10 {
		t.Fatalf("available: got %d want 10", got)
	}
}
```

Fix the cause of each one, not just the symptom.

## Phase 2: replenishment planning

Implement `Replenishment` in `replenish.go`:

```go
func (s *Service) Replenishment(warehouse string, now int64) ([]Suggestion, error)
```

It plans restocking for one warehouse at time `now`. It only plans: nothing is moved or ordered.

- **Errors.** An unknown warehouse returns `ErrUnknownWarehouse`. A `now` older than the service clock returns `ErrBackdated`. Like every call that takes `now`, it moves the clock forward first, so holds that run out by `now` no longer count.
- **Which SKUs.** Only SKUs with a `Rule` for this warehouse (set with `SetRule`), one `Suggestion` each at most, sorted by SKU.
- **Stock position.** A SKU's position is its *available* stock in the warehouse plus what is *inbound*: units in transfers to this warehouse that have been started but not yet received. Once a transfer is received its units are on hand, so they are counted once, not twice.
- **When and how much.** Suggest a SKU when its position is **at or below** the rule's `Min`. `Qty` is `Max - Position`, rounded **up** to a multiple of `Pack` when `Pack > 1`. `Position` in the suggestion is the position you computed.
- **Where from.** `From` is the other warehouse that can best spare the units. A warehouse's surplus for the SKU is its available stock minus its own rule's `Min` for that SKU (0 if it has no rule). Pick the warehouse with the largest surplus that is at least `Qty`, lowest warehouse ID on a tie. If none can, `From` is `""` (buy from the supplier).

### Example

```
AddWarehouse("east"); AddWarehouse("west")
Receive("east", "A-01", "BOOT", 4, 0)
Receive("west", "W-01", "BOOT", 45, 0)
SetRule("east", "BOOT", Rule{Min: 10, Max: 30, Pack: 1})
SetRule("west", "BOOT", Rule{Min: 15, Max: 60})
SetRule("east", "SOCK", Rule{Min: 20, Max: 100, Pack: 25})
Reserve("o1", "east", "BOOT", 2, 600, 5)          // held until 605
Replenishment("east", 10) ->
  {SKU: BOOT, Position: 2, Qty: 28, From: west}   // west can spare 45 - 15 = 30
  {SKU: SOCK, Position: 0, Qty: 100, From: ""}
StartTransfer("t1", "west", "east", "BOOT", 5, 20)
Replenishment("east", 605) ->                     // o1 has run out; 5 boots inbound
  {SKU: BOOT, Position: 9, Qty: 21, From: west}
  {SKU: SOCK, Position: 0, Qty: 100, From: ""}
```

## Checking your work

- **Run** runs `cmd/run/main.go`, which reads commands from stdin (`warehouse`, `rule`, `receive`, `reserve`, `release`, `commit`, `transfer`, `arrive`, `available`, `onhand`, `bin`, `replenish`; see the top of the file). Extend it as you like.
- **My tests** runs your own `*_test.go` files. `inventory_example_test.go` is an example to copy.
- **Submit** runs the hidden tests for every phase you've unlocked.
