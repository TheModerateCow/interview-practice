package parking

import (
	"strconv"
	"testing"
)

func hiddenItoa(n int) string { return strconv.Itoa(n) }

func hiddenSame(t *testing.T, what string, got, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("%s: got %v want %v", what, got, want)
		}
	}
}

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

// garage returns a garage with the given spots added as id, size pairs at ts 1, 2, ...
func hiddenGarage(t *testing.T, idSize ...string) *Garage {
	t.Helper()
	g := NewGarage()
	for i := 0; i+1 < len(idSize); i += 2 {
		if !g.AddSpot(i/2+1, idSize[i], idSize[i+1]) {
			t.Fatalf("AddSpot(%s, %s) failed", idSize[i], idSize[i+1])
		}
	}
	return g
}

// ---------------------------------------------------------------- level 1

func Test_l1_add_spot_rules(t *testing.T) {
	g := NewGarage()
	hiddenEq(t, "add small", g.AddSpot(1, "A1", "small"), true)
	hiddenEq(t, "duplicate id", g.AddSpot(2, "A1", "large"), false)
	hiddenEq(t, "unknown size", g.AddSpot(3, "Z9", "huge"), false)
	hiddenEq(t, "empty size", g.AddSpot(4, "Z8", ""), false)
	hiddenEq(t, "add large", g.AddSpot(5, "B1", "large"), true)
	hiddenEq(t, "duplicate kept its size", g.Park(6, "CAR-1", "small"), "A1")
	hiddenEq(t, "rejected size added no spot", g.Park(7, "CAR-2", "small"), "B1")
	hiddenEq(t, "garage full", g.Park(8, "CAR-3", "small"), "")
}

func Test_l1_park_smallest_fit(t *testing.T) {
	g := hiddenGarage(t, "L1", "large", "M1", "medium", "S1", "small")
	hiddenEq(t, "small takes small", g.Park(10, "S-A", "small"), "S1")
	hiddenEq(t, "next small takes medium", g.Park(11, "S-B", "small"), "M1")
	hiddenEq(t, "medium doesn't fit small, takes large", g.Park(12, "M-A", "medium"), "L1")
	hiddenEq(t, "nothing left", g.Park(13, "S-C", "small"), "")
	hiddenEq(t, "spot of", g.SpotOf(14, "S-B"), "M1")
	hiddenEq(t, "spot of the failed park", g.SpotOf(15, "S-C"), "")
}

func Test_l1_park_lowest_id_on_ties(t *testing.T) {
	g := hiddenGarage(t, "m2", "medium", "m10", "medium", "m1", "medium", "s1", "small")
	hiddenEq(t, "large doesn't fit medium", g.Park(10, "TRUCK", "large"), "")
	hiddenEq(t, "lowest id first", g.Park(11, "A", "medium"), "m1")
	hiddenEq(t, "string order", g.Park(12, "B", "medium"), "m10")
	hiddenEq(t, "then m2", g.Park(13, "C", "medium"), "m2")
	hiddenEq(t, "medium can't use small", g.Park(14, "D", "medium"), "")
	hiddenEq(t, "small still fits", g.Park(15, "E", "small"), "s1")
}

func Test_l1_park_rejects(t *testing.T) {
	g := NewGarage()
	hiddenEq(t, "empty garage", g.Park(1, "CAR", "small"), "")
	g = hiddenGarage(t, "A1", "small", "A2", "small")
	hiddenEq(t, "unknown size", g.Park(10, "CAR", "tiny"), "")
	hiddenEq(t, "park", g.Park(11, "CAR", "small"), "A1")
	hiddenEq(t, "already parked", g.Park(12, "CAR", "small"), "")
	hiddenEq(t, "still in its first spot", g.SpotOf(13, "CAR"), "A1")
	hiddenEq(t, "the other spot is still free", g.Park(14, "BUS", "small"), "A2")
}

func Test_l1_leave_frees_spot(t *testing.T) {
	g := hiddenGarage(t, "A1", "small", "B1", "large")
	g.Park(10, "CAR", "small")
	g.Park(11, "VAN", "small")
	hiddenEq(t, "leave", g.Leave(12, "CAR"), true)
	hiddenEq(t, "no spot after leaving", g.SpotOf(13, "CAR"), "")
	hiddenEq(t, "leave twice", g.Leave(14, "CAR"), false)
	hiddenEq(t, "leave unknown", g.Leave(15, "NOPE"), false)
	hiddenEq(t, "freed spot reused", g.Park(16, "BIKE", "small"), "A1")
	hiddenEq(t, "others untouched", g.SpotOf(17, "VAN"), "B1")
	g.Leave(18, "VAN")
	hiddenEq(t, "can park again after leaving", g.Park(19, "CAR", "small"), "B1")
}

// ---------------------------------------------------------------- level 2

func Test_l2_free_spots_exact_size(t *testing.T) {
	g := NewGarage()
	hiddenEq(t, "empty garage", g.FreeSpots(1, "small"), 0)
	hiddenEq(t, "unknown size", g.FreeSpots(2, "huge"), -1)
	g = hiddenGarage(t, "S1", "small", "S2", "small", "M1", "medium", "L1", "large")
	hiddenEq(t, "small", g.FreeSpots(10, "small"), 2)
	hiddenEq(t, "medium", g.FreeSpots(11, "medium"), 1)
	hiddenEq(t, "large", g.FreeSpots(12, "large"), 1)
	g.Park(13, "A", "medium")
	g.Park(14, "B", "small")
	hiddenEq(t, "medium taken", g.FreeSpots(15, "medium"), 0)
	hiddenEq(t, "one small left", g.FreeSpots(16, "small"), 1)
	hiddenEq(t, "large untouched", g.FreeSpots(17, "large"), 1)
}

func Test_l2_free_spots_after_leave(t *testing.T) {
	g := hiddenGarage(t, "S1", "small", "L1", "large", "L2", "large")
	g.Park(10, "A", "small")
	g.Park(11, "B", "small")
	g.Park(12, "C", "large")
	hiddenEq(t, "no small", g.FreeSpots(13, "small"), 0)
	hiddenEq(t, "no large", g.FreeSpots(14, "large"), 0)
	g.Leave(15, "B")
	hiddenEq(t, "small car left a large spot", g.FreeSpots(16, "large"), 1)
	hiddenEq(t, "small still full", g.FreeSpots(17, "small"), 0)
}

func Test_l2_top_visitors_order(t *testing.T) {
	g := hiddenGarage(t, "A1", "small", "A2", "small")
	ts := 10
	for _, p := range []string{"cy", "bo", "ana", "bo", "dee", "bo", "cy", "ana"} {
		g.Park(ts, p, "small")
		g.Leave(ts+1, p)
		ts += 2
	}
	hiddenSame(t, "top 3", g.TopVisitors(ts, 3), []string{"bo(3)", "ana(2)", "cy(2)"})
	hiddenSame(t, "n bigger than plates", g.TopVisitors(ts+1, 10), []string{"bo(3)", "ana(2)", "cy(2)", "dee(1)"})
	hiddenSame(t, "n 0", g.TopVisitors(ts+2, 0), []string{})
}

func Test_l2_top_visitors_count_only_parks(t *testing.T) {
	g := NewGarage()
	hiddenSame(t, "nobody yet", g.TopVisitors(1, 5), []string{})
	g = hiddenGarage(t, "A1", "small")
	g.Park(10, "ana", "small")
	g.Park(11, "ana", "small")
	g.Park(12, "bo", "small")
	g.Park(13, "cy", "huge")
	hiddenSame(t, "failed parks don't count", g.TopVisitors(14, 5), []string{"ana(1)"})
	g.Leave(15, "ana")
	hiddenSame(t, "visits stay after leaving", g.TopVisitors(16, 5), []string{"ana(1)"})
	g.Park(17, "bo", "small")
	hiddenSame(t, "tie by plate", g.TopVisitors(18, 5), []string{"ana(1)", "bo(1)"})
}

func Test_l2_top_visitors_across_spots(t *testing.T) {
	g := hiddenGarage(t, "S1", "small", "L1", "large")
	g.Park(10, "van", "large")
	g.Leave(11, "van")
	g.Park(12, "van", "small")
	g.Park(13, "car", "small")
	g.Leave(14, "car")
	hiddenSame(t, "one plate, two spots", g.TopVisitors(15, 5), []string{"van(2)", "car(1)"})
}

// ---------------------------------------------------------------- level 3

func Test_l3_reservation_blocks_spot(t *testing.T) {
	g := hiddenGarage(t, "S1", "small", "S2", "small")
	hiddenEq(t, "reserve", g.Reserve(10, "RES", "small", 30), "S1")
	hiddenEq(t, "reserved spot not free", g.FreeSpots(11, "small"), 1)
	hiddenEq(t, "others skip it", g.Park(12, "X", "small"), "S2")
	hiddenEq(t, "full for everyone else", g.Park(13, "Y", "small"), "")
	hiddenEq(t, "still reserved just before expiry", g.Park(39, "Y", "small"), "")
	hiddenEq(t, "free again at expiry", g.FreeSpots(40, "small"), 1)
	hiddenEq(t, "and parkable", g.Park(41, "Y", "small"), "S1")
}

func Test_l3_reserved_plate_gets_its_spot(t *testing.T) {
	g := hiddenGarage(t, "S5", "small", "M1", "medium")
	hiddenEq(t, "reserve picks like park", g.Reserve(10, "RES", "small", 50), "S5")
	g.AddSpot(11, "S0", "small")
	hiddenEq(t, "goes to its reserved spot", g.Park(12, "RES", "small"), "S5")
	hiddenEq(t, "S0 still free", g.FreeSpots(13, "small"), 1)
	hiddenSame(t, "a reserved park is a visit", g.TopVisitors(14, 5), []string{"RES(1)"})
	g.Leave(15, "RES")
	hiddenEq(t, "reservation used up", g.FreeSpots(16, "small"), 2)
	hiddenEq(t, "spot open to others", g.Park(17, "X", "small"), "S0")
	hiddenEq(t, "and the next", g.Park(18, "Y", "small"), "S5")
}

func Test_l3_reserve_rules(t *testing.T) {
	g := hiddenGarage(t, "S1", "small", "M1", "medium")
	hiddenEq(t, "unknown size", g.Reserve(10, "A", "huge", 5), "")
	hiddenEq(t, "ttl 0", g.Reserve(11, "A", "small", 0), "")
	hiddenEq(t, "large doesn't fit", g.Reserve(12, "A", "large", 5), "")
	g.Park(13, "P", "small")
	hiddenEq(t, "parked plate", g.Reserve(14, "P", "small", 5), "")
	hiddenEq(t, "reserve", g.Reserve(15, "A", "small", 5), "M1")
	hiddenEq(t, "one live reservation per plate", g.Reserve(16, "A", "small", 5), "")
	hiddenEq(t, "nothing free", g.Reserve(17, "B", "small", 5), "")
	hiddenEq(t, "after expiry, reserve again", g.Reserve(20, "A", "medium", 5), "M1")
}

func Test_l3_cancel(t *testing.T) {
	g := hiddenGarage(t, "S1", "small")
	g.Reserve(10, "A", "small", 20)
	hiddenEq(t, "cancel live", g.Cancel(11, "A"), true)
	hiddenEq(t, "spot free", g.FreeSpots(12, "small"), 1)
	hiddenEq(t, "cancel twice", g.Cancel(13, "A"), false)
	hiddenEq(t, "cancel unknown", g.Cancel(14, "NOPE"), false)
	g.Reserve(15, "B", "small", 10)
	hiddenEq(t, "cancel at expiry", g.Cancel(25, "B"), false)
	hiddenEq(t, "cancelled plate parks normally", g.Park(26, "A", "small"), "S1")
	hiddenEq(t, "cancel after parking", g.Cancel(27, "A"), false)
}

func Test_l3_expired_reservation_parks_normally(t *testing.T) {
	g := hiddenGarage(t, "S1", "small", "S2", "small")
	g.Reserve(10, "RES", "small", 10)
	hiddenEq(t, "expired spot taken by another", g.Park(20, "X", "small"), "S1")
	hiddenEq(t, "late plate gets a normal spot", g.Park(21, "RES", "small"), "S2")
	g.Leave(22, "RES")
	hiddenEq(t, "reserve after leaving", g.Reserve(23, "RES", "small", 10), "S2")
	hiddenEq(t, "reserved for RES only", g.Park(24, "Y", "small"), "")
}

// ---------------------------------------------------------------- level 4

func Test_l4_occupant_at(t *testing.T) {
	g := hiddenGarage(t, "S1", "small")
	g.Park(10, "A", "small")
	g.Leave(20, "A")
	g.Park(30, "B", "small")
	for _, c := range []struct {
		at   int
		want string
	}{{9, ""}, {10, "A"}, {19, "A"}, {20, ""}, {29, ""}, {30, "B"}, {100, "B"}} {
		hiddenEq(t, "occupant at "+hiddenItoa(c.at), g.OccupantAt(200, "S1", c.at), c.want)
	}
}

func Test_l4_occupant_at_edges(t *testing.T) {
	g := hiddenGarage(t, "S1", "small", "S2", "small")
	hiddenEq(t, "unknown spot", g.OccupantAt(10, "Z9", 5), "")
	g.Reserve(11, "R", "small", 50)
	hiddenEq(t, "a reservation is not an occupant", g.OccupantAt(12, "S1", 11), "")
	g.Park(13, "R", "small")
	g.Park(14, "X", "small")
	hiddenEq(t, "occupant from the park", g.OccupantAt(15, "S1", 13), "R")
	hiddenEq(t, "other spot", g.OccupantAt(16, "S2", 14), "X")
	hiddenEq(t, "before the park", g.OccupantAt(17, "S2", 13), "")
	g.AddSpot(18, "S3", "small")
	hiddenEq(t, "spot added later", g.OccupantAt(19, "S3", 5), "")
}

func Test_l4_charges_round_up(t *testing.T) {
	g := hiddenGarage(t, "S1", "small")
	g.Park(10, "A", "small")
	g.Leave(70, "A")
	hiddenEq(t, "exactly one hour", g.Charges(71, "A"), 200)
	g.Park(100, "A", "small")
	g.Leave(161, "A")
	hiddenEq(t, "61 minutes is two hours", g.Charges(162, "A"), 600)
	g.Park(200, "A", "small")
	g.Leave(201, "A")
	hiddenEq(t, "one minute is one hour", g.Charges(202, "A"), 800)
}

func Test_l4_charges_by_spot_size(t *testing.T) {
	g := hiddenGarage(t, "M1", "medium", "L1", "large")
	g.Park(10, "BIKE", "small")
	g.Park(11, "CAR", "small")
	g.Leave(130, "BIKE")
	g.Leave(131, "CAR")
	hiddenEq(t, "medium spot, 2 hours", g.Charges(132, "BIKE"), 600)
	hiddenEq(t, "large spot, 2 hours", g.Charges(133, "CAR"), 1000)
}

func Test_l4_charges_finished_stays_only(t *testing.T) {
	g := hiddenGarage(t, "S1", "small", "S2", "small")
	hiddenEq(t, "unknown plate", g.Charges(10, "NOPE"), 0)
	g.Reserve(10, "A", "small", 100)
	g.Park(50, "A", "small")
	g.Park(51, "B", "small")
	hiddenEq(t, "still parked", g.Charges(52, "A"), 0)
	g.Leave(110, "A")
	hiddenEq(t, "charged from the park, not the reservation", g.Charges(111, "A"), 200)
	hiddenEq(t, "others still parked", g.Charges(112, "B"), 0)
	g.Leave(300, "B")
	hiddenEq(t, "B pays its own stay", g.Charges(301, "B"), 1000)
	hiddenEq(t, "A unchanged", g.Charges(302, "A"), 200)
}
