package ledger

import "fmt"

// minorDigits is how many digits after the decimal point each booked currency has.
// Every amount in the ledger is an integer count of minor units (cents, fils, yen).
var minorDigits = map[string]int{"EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "USD": 2}

// ValidCurrency reports whether the ledger books amounts in cur.
func ValidCurrency(cur string) bool {
	_, ok := minorDigits[cur]
	return ok
}

// Format renders minor units for display: Format(-1250, "USD") is "-12.50 USD".
func Format(minor int64, cur string) string {
	sign := ""
	if minor < 0 {
		sign, minor = "-", -minor
	}
	d := minorDigits[cur]
	if d == 0 {
		return fmt.Sprintf("%s%d %s", sign, minor, cur)
	}
	unit := int64(1)
	for i := 0; i < d; i++ {
		unit *= 10
	}
	return fmt.Sprintf("%s%d.%0*d %s", sign, minor/unit, d, minor%unit, cur)
}
