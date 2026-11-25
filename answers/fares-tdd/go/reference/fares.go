package fares

import (
	"errors"
	"strings"
)

var (
	ErrUnknownConcession = errors.New("unknown concession")
	ErrInvalidTime       = errors.New("invalid time")
	ErrInvalidZone       = errors.New("invalid zone")
)

const (
	day            = 1440
	transferWindow = 90
	maxRides       = 3
)

var base = [6]int{250, 320, 410, 480, 550, 620} // by number of zones, 1..6

// concession: share of the fare paid, daily cap, weekly cap (cents).
type concession struct{ payPercent, dailyCap, weeklyCap int }

var concessions = map[string]concession{
	"adult":  {100, 1200, 4800},
	"child":  {50, 600, 2400},
	"senior": {70, 840, 3360},
}

func parse(s string) (concession, error) {
	for name, c := range concessions {
		if strings.EqualFold(name, s) {
			return c, nil
		}
	}
	return concession{}, ErrUnknownConcession
}

// IsPeak reports whether a ride at time (minutes since Monday 00:00 of week 0) is in a peak window.
func IsPeak(time int) bool {
	weekday := (time/day)%7 <= 4
	m := time % day
	return weekday && ((m >= 420 && m < 570) || (m >= 960 && m < 1140))
}

// JourneyFare is the fare in cents for a journey covering zones zones (1-6), after the peak uplift and the concession discount.
func JourneyFare(zones int, peak bool, concession string) (int, error) {
	c, err := parse(concession)
	if err != nil {
		return 0, err
	}
	return journeyFare(zones, peak, c), nil
}

func journeyFare(zones int, peak bool, c concession) int {
	fare := base[zones-1]
	if peak {
		fare = (fare*130 + 999) / 1000 * 10
	}
	return fare * c.payPercent / 500 * 5
}

// FareCard is one rider's travel card. Rides arrive in time order.
type FareCard struct {
	concession  concession
	lastTime    int
	rides       int // rides in the current journey; 0 = no journey yet
	start       int
	lo, hi      int
	peak        bool
	spentByDay  map[int]int
	spentByWeek map[int]int
}

func NewFareCard(concession string) (*FareCard, error) {
	c, err := parse(concession)
	if err != nil {
		return nil, err
	}
	return &FareCard{concession: c, lastTime: -1, spentByDay: map[int]int{}, spentByWeek: map[int]int{}}, nil
}

func floorDiv(a, b int) int {
	q := a / b
	if a%b != 0 && (a < 0) != (b < 0) {
		q--
	}
	return q
}

// Ride records a ride and returns the cents charged for it.
func (f *FareCard) Ride(time int, fromZone int, toZone int) (int, error) {
	if time < 0 || time < f.lastTime {
		return 0, ErrInvalidTime
	}
	if fromZone < 1 || fromZone > 6 || toZone < 1 || toZone > 6 {
		return 0, ErrInvalidZone
	}
	f.lastTime = time

	rideLo, rideHi := min(fromZone, toZone), max(fromZone, toZone)
	before := 0
	if f.rides > 0 && time-f.start < transferWindow && f.rides < maxRides {
		before = journeyFare(f.hi-f.lo+1, f.peak, f.concession)
		f.lo = min(f.lo, rideLo)
		f.hi = max(f.hi, rideHi)
		f.rides++
	} else {
		f.start = time
		f.peak = IsPeak(time)
		f.lo = rideLo
		f.hi = rideHi
		f.rides = 1
	}
	due := journeyFare(f.hi-f.lo+1, f.peak, f.concession) - before

	d := floorDiv(time-240, day)
	w := floorDiv(d, 7)
	today, thisWeek := f.spentByDay[d], f.spentByWeek[w]
	charge := max(0, min(due, min(f.concession.dailyCap-today, f.concession.weeklyCap-thisWeek)))
	f.spentByDay[d] = today + charge
	f.spentByWeek[w] = thisWeek + charge
	return charge, nil
}
