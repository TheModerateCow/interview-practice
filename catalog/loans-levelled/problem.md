# Loan servicing

You're building the in-memory servicing system for a consumer lender. It originates loans repaid in monthly instalments, and later takes payments, charges late fees, quotes early payoffs and restructures loans. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{Lender}}` type. Keep building on it: later levels add methods to it. Standard library only.

**Days.** Dates are integers. Every method takes `day` as its first argument: today, the day of the call. Days only ever increase from one call to the next.

**Money** is in integer cents. **Rates** are in basis points: 100 bp is 1%.

## Level 1: loans and schedules

| Method | Behaviour |
|---|---|
| `{{originate}}(day, loan_id, principal, months, rate_bp)` | Lends `principal`, repaid in `months` monthly instalments, at a flat `rate_bp` per month. Returns `false`, changing nothing, if `loan_id` already exists, `principal <= 0`, `months <= 0` or `rate_bp < 0` (0 is an interest-free loan). |
| `{{schedule}}(day, loan_id)` | Every instalment in order, as `"due_day:amount"`. An empty list if the loan doesn't exist. |
| `{{amount_due}}(day, loan_id)` | What the borrower must pay today to be up to date: the total still unpaid on instalments due on or before `day`. Nothing can be paid yet at this level, so it's the sum of those instalments. `-1` if the loan doesn't exist. |

**The schedule.** For a loan originated on day `d`:

- Instalment `k` (1 to `months`) is due on day `d + 30 × k`.
- **Interest** is flat: every instalment carries the same interest, `principal × rate_bp / 10000`, rounded half up to whole cents (exactly half a cent rounds up).
- **Principal**: each instalment repays `principal / months` rounded down, and the last one also repays the remainder, so the parts add up to `principal` exactly.
- An instalment's `amount` is its principal part plus its interest.

### Example

```
{{originate}}(1, "car", 100000, 3, 150)   -> true
{{originate}}(2, "car", 5000, 1, 0)       -> false   (car exists)
{{originate}}(3, "bike", 100100, 2, 50)   -> true
{{schedule}}(4, "car")    -> ["31:34833", "61:34833", "91:34834"]   (interest 1500; principal 33333, 33333, 33334)
{{schedule}}(4, "bike")   -> ["33:50551", "63:50551"]               (interest 500.5 rounds up to 501)
{{amount_due}}(30, "car") -> 0
{{amount_due}}(31, "car") -> 34833
{{amount_due}}(70, "car") -> 69666
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
