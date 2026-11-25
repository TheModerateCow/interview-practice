package quota

// windowStart returns the start of the fixed window that contains now.
// Windows are aligned to the epoch, so every key on a plan resets together.
func windowStart(now, window int64) int64 {
	return now - now%window
}

// resetIn is how many seconds remain until the window containing now ends.
func resetIn(now, window int64) int64 {
	return windowStart(now, window) + window - now
}

// rollover is how many units carry into a window from the one before it:
// whatever the key left unused there, up to the plan's burst allowance.
func rollover(p Plan, prevUsed int) int {
	unused := p.Limit - prevUsed
	return min(unused, p.Burst)
}

// capacity is how many units a key may spend in a window, given what it
// spent in the window before.
func capacity(p Plan, prevUsed int) int {
	return p.Limit + rollover(p, prevUsed)
}
