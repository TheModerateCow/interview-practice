// Package shipping prices parcels for an online shop.
package shipping

import "errors"

var (
	ErrNoParcels     = errors.New("order has no parcels")
	ErrUnknownZone   = errors.New("unknown zone")
	ErrUnknownPromo  = errors.New("unknown promo code")
	ErrInvalidParcel = errors.New("invalid parcel")
	ErrTooHeavy      = errors.New("parcel too heavy")
)

// Parcel is one box in an order.
type Parcel struct {
	WeightGrams int
	LengthCm    int
	WidthCm     int
	HeightCm    int
}

// Order is everything needed to price shipping.
type Order struct {
	Parcels       []Parcel
	Zone          int  // 1-4
	SubtotalCents int  // merchandise subtotal, never negative
	Express       bool // express delivery for the whole order
	PromoCode     string
}

const (
	maxBillable     = 30000
	freeShippingMin = 7500
	oversizeSide    = 100
	oversizeFee     = 1500
)

var (
	firstKg = [5]int{0, 500, 650, 800, 1100}
	perStep = [5]int{0, 100, 140, 180, 250}
)

// halfUp returns num/den rounded half up, for num >= 0.
func halfUp(num, den int) int { return (num + den/2) / den }

// BillableGrams returns the weight a parcel is charged for.
func BillableGrams(p Parcel) (int, error) {
	if p.WeightGrams <= 0 || p.LengthCm <= 0 || p.WidthCm <= 0 || p.HeightCm <= 0 {
		return 0, ErrInvalidParcel
	}
	dim := (p.LengthCm*p.WidthCm*p.HeightCm + 4) / 5
	g := max(p.WeightGrams, dim)
	g = (g + 499) / 500 * 500
	if g > maxBillable {
		return 0, ErrTooHeavy
	}
	return g, nil
}

// Quote returns the shipping price of an order in cents.
func Quote(o Order) (int, error) {
	if len(o.Parcels) == 0 {
		return 0, ErrNoParcels
	}
	if o.Zone < 1 || o.Zone > 4 {
		return 0, ErrUnknownZone
	}
	if o.PromoCode != "" && o.PromoCode != "SHIP10" && o.PromoCode != "FLAT600" {
		return 0, ErrUnknownPromo
	}
	free := o.SubtotalCents >= freeShippingMin && o.Zone <= 3 && !o.Express
	sum := 0
	for _, p := range o.Parcels {
		g, err := BillableGrams(p)
		if err != nil {
			return 0, err
		}
		rate := firstKg[o.Zone]
		if g > 1000 {
			rate += (g - 1000) / 500 * perStep[o.Zone]
		}
		if o.Express {
			rate = halfUp(rate*135, 100)
		}
		if free {
			rate = 0
		}
		if max(p.LengthCm, p.WidthCm, p.HeightCm) > oversizeSide {
			rate += oversizeFee
		}
		sum += rate
	}
	total := sum + halfUp(sum*85, 1000)
	switch {
	case o.PromoCode == "SHIP10":
		total -= total / 10
	case o.PromoCode == "FLAT600" && !free:
		total = max(total-600, 0)
	}
	return total, nil
}
