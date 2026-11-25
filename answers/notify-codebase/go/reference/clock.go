package notify

const daySeconds = 24 * 60 * 60

// floorMod is a mod b in [0, b), also for negative a.
func floorMod(a, b int64) int64 {
	return ((a % b) + b) % b
}

// localHour is the hour (0-23) on the user's wall clock at UTC time at.
func localHour(at int64, offsetMin int) int {
	wall := at + int64(offsetMin)*60
	return int(floorMod(wall, daySeconds) / 3600)
}

// inQuietHours reports whether at falls in the user's quiet hours. A range
// like 22 -> 7 wraps past midnight.
func inQuietHours(u User, at int64) bool {
	if u.QuietFrom == u.QuietTo {
		return false
	}
	h := localHour(at, u.OffsetMin)
	if u.QuietFrom < u.QuietTo {
		return h >= u.QuietFrom && h < u.QuietTo
	}
	return h >= u.QuietFrom || h < u.QuietTo
}

// localMidnight is the UTC time at which the user's local day containing at
// began.
func localMidnight(at int64, offsetMin int) int64 {
	shift := int64(offsetMin) * 60
	return at - floorMod(at+shift, daySeconds)
}
