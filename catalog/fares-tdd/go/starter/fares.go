package fares

import "errors"

var (
	ErrUnknownConcession = errors.New("unknown concession")
	ErrInvalidTime       = errors.New("invalid time")
	ErrInvalidZone       = errors.New("invalid zone")
)

func IsPeak(time int) bool {
	panic("not implemented")
}

func JourneyFare(zones int, peak bool, concession string) (int, error) {
	panic("not implemented")
}

type FareCard struct{}

func NewFareCard(concession string) (*FareCard, error) {
	panic("not implemented")
}

func (f *FareCard) Ride(time int, fromZone int, toZone int) (int, error) {
	panic("not implemented")
}
