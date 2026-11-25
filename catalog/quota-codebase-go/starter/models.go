// Package quota is the in-memory core of the API gateway's quota service. It
// decides whether each call fits its API key's plan and keeps the request log
// that usage reports are built from.
package quota

import "errors"

// Plan is a pricing tier's rate limit: Limit units per fixed window, plus up
// to Burst units the key left unused in the window before.
type Plan struct {
	Name   string
	Limit  int   // units allowed per window
	Window int64 // window length in seconds
	Burst  int   // most unused units that roll over into the next window
}

// Key is an API key issued to an organisation.
type Key struct {
	ID      string
	Org     string
	Plan    string
	Revoked bool
}

// Event is one request the limiter decided on.
type Event struct {
	At      int64 // seconds since the epoch
	Cost    int   // units the request asked for
	Allowed bool
}

// Decision is the limiter's answer to one request.
type Decision struct {
	Allowed    bool
	Remaining  int   // units left in the current window after this request
	RetryAfter int64 // seconds until the window resets; 0 when allowed
}

// UsageLine is one key's row in an organisation's usage report.
type UsageLine struct {
	KeyID    string
	Plan     string
	Requests int // allowed requests
	Units    int // units spent by allowed requests
	Denied   int // requests the limiter rejected
}

var (
	ErrUnknownKey    = errors.New("unknown api key")
	ErrDuplicateKey  = errors.New("api key already exists")
	ErrRevoked       = errors.New("api key revoked")
	ErrUnknownPlan   = errors.New("unknown plan")
	ErrDuplicatePlan = errors.New("plan already exists")
	ErrInvalidPlan   = errors.New("plan needs a positive limit and window and a non-negative burst")
	ErrBadCost       = errors.New("request cost must be positive")
	ErrBadRange      = errors.New("report range must end after it starts")
)
