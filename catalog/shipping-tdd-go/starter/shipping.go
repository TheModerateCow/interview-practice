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

// BillableGrams returns the weight a parcel is charged for.
func BillableGrams(p Parcel) (int, error) {
	panic("not implemented")
}

// Quote returns the shipping price of an order in cents.
func Quote(o Order) (int, error) {
	panic("not implemented")
}
