package shipping

import (
	"errors"
	"testing"
)

func hiddenBox(w, l, wi, h int) Parcel {
	return Parcel{WeightGrams: w, LengthCm: l, WidthCm: wi, HeightCm: h}
}

var (
	hiddenKilo = hiddenBox(1000, 10, 10, 10)
	hiddenLong = hiddenBox(1000, 101, 10, 10) // oversize, 2500 g dimensional
)

type hiddenQuoteCase struct {
	name string
	o    Order
	want int
}

func hiddenCheckQuotes(t *testing.T, cases []hiddenQuoteCase) {
	t.Helper()
	for _, c := range cases {
		got, err := Quote(c.o)
		if err != nil {
			t.Fatalf("%s: unexpected error %v", c.name, err)
		}
		if got != c.want {
			t.Fatalf("%s: got %d want %d", c.name, got, c.want)
		}
	}
}

func Test_p1_billable_weight(t *testing.T) {
	cases := []struct {
		name string
		p    Parcel
		want int
	}{
		{"actual heavier, rounded up to 500 g", hiddenBox(1200, 10, 10, 10), 1500},
		{"dimensional heavier", hiddenBox(300, 40, 30, 20), 5000},
		{"exact 1000 g stays 1000", hiddenKilo, 1000},
		{"exact 500 g stays 500", hiddenBox(500, 5, 5, 5), 500},
		{"1 g bills as 500", hiddenBox(1, 1, 1, 1), 500},
		{"dimensional weight rounds up before banding", hiddenBox(900, 11, 22, 31), 2000},
		{"exact 2500 g", hiddenBox(2500, 10, 10, 10), 2500},
		{"30 kg is allowed", hiddenBox(30000, 10, 10, 10), 30000},
		{"dimensional exactly 30 kg is allowed", hiddenBox(1000, 50, 50, 60), 30000},
	}
	for _, c := range cases {
		got, err := BillableGrams(c.p)
		if err != nil || got != c.want {
			t.Fatalf("%s: got %d, %v want %d, nil", c.name, got, err, c.want)
		}
	}
}

func Test_p1_billable_errors(t *testing.T) {
	cases := []struct {
		name string
		p    Parcel
		want error
	}{
		{"zero weight", hiddenBox(0, 1, 1, 1), ErrInvalidParcel},
		{"negative width", hiddenBox(5, 1, -1, 1), ErrInvalidParcel},
		{"zero height", hiddenBox(5, 1, 1, 0), ErrInvalidParcel},
		{"zero length", hiddenBox(5, 0, 1, 1), ErrInvalidParcel},
		{"over 30 kg actual", hiddenBox(30001, 10, 10, 10), ErrTooHeavy},
		{"over 30 kg dimensional", hiddenBox(1000, 60, 50, 51), ErrTooHeavy},
	}
	for _, c := range cases {
		_, err := BillableGrams(c.p)
		if !errors.Is(err, c.want) {
			t.Fatalf("%s: got %v want %v", c.name, err, c.want)
		}
	}
}

func Test_p1_zone_rates(t *testing.T) {
	hiddenCheckQuotes(t, []hiddenQuoteCase{
		{"zone 1, 1 kg", Order{Parcels: []Parcel{hiddenKilo}, Zone: 1}, 543},
		{"zone 2, 1 kg", Order{Parcels: []Parcel{hiddenKilo}, Zone: 2}, 705},
		{"zone 3, 1 kg", Order{Parcels: []Parcel{hiddenKilo}, Zone: 3}, 868},
		{"zone 4, 1 kg", Order{Parcels: []Parcel{hiddenKilo}, Zone: 4}, 1194},
		{"zone 1, 1500 g", Order{Parcels: []Parcel{hiddenBox(1500, 10, 10, 10)}, Zone: 1}, 651},
		{"zone 3, 3200 g bills 3500", Order{Parcels: []Parcel{hiddenBox(3200, 10, 10, 10)}, Zone: 3}, 1845},
		{"zone 2, dimensional 2000 g", Order{Parcels: []Parcel{hiddenBox(900, 11, 22, 31)}, Zone: 2}, 1009},
		{"zone 4, 30 kg express", Order{Parcels: []Parcel{hiddenBox(30000, 40, 30, 30)}, Zone: 4, Express: true}, 22850},
	})
}

func Test_p1_express_rounding(t *testing.T) {
	hiddenCheckQuotes(t, []hiddenQuoteCase{
		{"zone 1 express", Order{Parcels: []Parcel{hiddenKilo}, Zone: 1, Express: true}, 732},
		{"zone 2 express rounds half up", Order{Parcels: []Parcel{hiddenKilo}, Zone: 2, Express: true}, 953},
		{"express rounds per parcel", Order{Parcels: []Parcel{hiddenKilo, hiddenKilo}, Zone: 2, Express: true}, 1905},
		{"express two parcels", Order{Parcels: []Parcel{hiddenBox(700, 20, 20, 20), hiddenBox(2000, 15, 15, 15)}, Zone: 2, Express: true}, 2726},
	})
}

func Test_p1_oversize(t *testing.T) {
	hiddenCheckQuotes(t, []hiddenQuoteCase{
		{"101 cm side", Order{Parcels: []Parcel{hiddenLong}, Zone: 1}, 2496},
		{"100 cm side is not oversize", Order{Parcels: []Parcel{hiddenBox(1000, 100, 10, 10)}, Zone: 1}, 760},
		{"oversize fee not multiplied by express", Order{Parcels: []Parcel{hiddenBox(1000, 10, 10, 101)}, Zone: 2, Express: true}, 3195},
	})
}

func Test_p1_free_shipping(t *testing.T) {
	hiddenCheckQuotes(t, []hiddenQuoteCase{
		{"at threshold", Order{Parcels: []Parcel{hiddenKilo}, Zone: 1, SubtotalCents: 7500}, 0},
		{"one cent under", Order{Parcels: []Parcel{hiddenKilo}, Zone: 1, SubtotalCents: 7499}, 543},
		{"zone 3 qualifies", Order{Parcels: []Parcel{hiddenKilo}, Zone: 3, SubtotalCents: 20000}, 0},
		{"zone 4 never free", Order{Parcels: []Parcel{hiddenKilo}, Zone: 4, SubtotalCents: 10000}, 1194},
		{"express never free", Order{Parcels: []Parcel{hiddenKilo}, Zone: 1, SubtotalCents: 10000, Express: true}, 732},
		{"oversize fee still charged", Order{Parcels: []Parcel{hiddenKilo, hiddenLong}, Zone: 1, SubtotalCents: 7500}, 1628},
	})
}

func Test_p1_promos(t *testing.T) {
	hiddenCheckQuotes(t, []hiddenQuoteCase{
		{"SHIP10 zone 1", Order{Parcels: []Parcel{hiddenKilo}, Zone: 1, PromoCode: "SHIP10"}, 489},
		{"SHIP10 zone 4", Order{Parcels: []Parcel{hiddenKilo}, Zone: 4, PromoCode: "SHIP10"}, 1075},
		{"SHIP10 discount rounds down", Order{Parcels: []Parcel{hiddenKilo, hiddenLong}, Zone: 1, SubtotalCents: 7500, PromoCode: "SHIP10"}, 1466},
		{"FLAT600 zone 4", Order{Parcels: []Parcel{hiddenKilo}, Zone: 4, PromoCode: "FLAT600"}, 594},
		{"FLAT600 never below zero", Order{Parcels: []Parcel{hiddenKilo}, Zone: 1, PromoCode: "FLAT600"}, 0},
		{"FLAT600 ignored with free shipping", Order{Parcels: []Parcel{hiddenKilo, hiddenLong}, Zone: 1, SubtotalCents: 7500, PromoCode: "FLAT600"}, 1628},
		{"FLAT600 applies when zone 4 blocks free shipping", Order{Parcels: []Parcel{hiddenLong}, Zone: 4, SubtotalCents: 7500, PromoCode: "FLAT600"}, 3035},
	})
}

func Test_p1_mixed_orders(t *testing.T) {
	mixed := []Parcel{hiddenBox(2600, 10, 10, 10), hiddenBox(900, 11, 22, 31), hiddenBox(1000, 120, 30, 5)}
	two := []Parcel{hiddenBox(1200, 30, 20, 10), hiddenBox(4100, 40, 30, 30)}
	hiddenCheckQuotes(t, []hiddenQuoteCase{
		{"zone 3 express SHIP10", Order{Parcels: mixed, Zone: 3, Express: true, PromoCode: "SHIP10"}, 7477},
		{"zone 3 free SHIP10", Order{Parcels: mixed, Zone: 3, SubtotalCents: 9000, PromoCode: "SHIP10"}, 1466},
		{"zone 2 standard", Order{Parcels: two, Zone: 2}, 3537},
		{"zone 2 express FLAT600", Order{Parcels: two, Zone: 2, Express: true, PromoCode: "FLAT600"}, 4176},
	})
}

func Test_p1_order_errors(t *testing.T) {
	cases := []struct {
		name string
		o    Order
		want error
	}{
		{"no parcels beats bad zone and promo", Order{Zone: 9, PromoCode: "X"}, ErrNoParcels},
		{"zone 0 beats bad promo", Order{Parcels: []Parcel{hiddenKilo}, Zone: 0, PromoCode: "X"}, ErrUnknownZone},
		{"zone 5", Order{Parcels: []Parcel{hiddenKilo}, Zone: 5}, ErrUnknownZone},
		{"promo is case-sensitive and beats bad parcel", Order{Parcels: []Parcel{hiddenBox(0, 1, 1, 1)}, Zone: 1, PromoCode: "ship10"}, ErrUnknownPromo},
		{"first bad parcel wins: too heavy", Order{Parcels: []Parcel{hiddenKilo, hiddenBox(30001, 1, 1, 1), hiddenBox(0, 1, 1, 1)}, Zone: 1}, ErrTooHeavy},
		{"first bad parcel wins: invalid", Order{Parcels: []Parcel{hiddenKilo, hiddenBox(1, 1, 0, 1), hiddenBox(30001, 1, 1, 1)}, Zone: 1}, ErrInvalidParcel},
	}
	for _, c := range cases {
		got, err := Quote(c.o)
		if !errors.Is(err, c.want) {
			t.Fatalf("%s: got %d, %v want %v", c.name, got, err, c.want)
		}
	}
}
