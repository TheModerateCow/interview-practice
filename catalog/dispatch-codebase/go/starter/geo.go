package dispatch

// CourierSpeed is the planning speed of a bike courier, in metres per
// minute (15 km/h).
const CourierSpeed = 250

// Distance is the street distance between two points. The zone is a street
// grid, so this is the Manhattan distance.
func Distance(a, b Point) int { return abs(a.X-b.X) + abs(a.Y-b.Y) }

// TravelMinutes converts a street distance into whole minutes of riding.
func TravelMinutes(metres int) int {
	return metres / CourierSpeed
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
