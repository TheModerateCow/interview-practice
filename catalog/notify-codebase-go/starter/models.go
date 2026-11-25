// Package notify is the in-memory core of the messaging platform's
// notification fan-out. Product teams hand it one notification per user;
// it applies the user's preferences and limits, decides which channels get
// it, and keeps the log that daily digests are built from.
package notify

import "errors"

// Channel is a delivery channel.
type Channel string

const (
	Email Channel = "email"
	Push  Channel = "push"
	SMS   Channel = "sms"
)

// DedupeWindow is how long, in seconds, a dedupe key blocks a repeat
// notification to the same user.
const DedupeWindow = 3600

// capWindow is the rolling span, in seconds, that hourlyCap counts over.
const capWindow = 3600

// hourlyCap is the most deliveries a user may get on a channel in any
// capWindow seconds.
var hourlyCap = map[Channel]int{Email: 6, Push: 4, SMS: 2}

// User is someone notifications can be sent to.
type User struct {
	ID        string
	OffsetMin int       // minutes east of UTC; fixed, no daylight saving
	Channels  []Channel // enabled channels, in the user's order
	QuietFrom int       // local hour quiet hours start (0-23)
	QuietTo   int       // local hour quiet hours end, exclusive; equal to QuietFrom means none
}

// Notification is one message a product team wants a user to get.
type Notification struct {
	User   string
	Topic  string // e.g. "billing", "security"
	Key    string // dedupe key chosen by the sender
	Title  string
	At     int64 // seconds since the epoch, UTC
	Urgent bool  // ignores quiet hours (but not caps)
}

// Status is what happened to a notification.
type Status string

const (
	Sent      Status = "sent"      // delivered on at least one channel
	Held      Status = "held"      // kept for the user's daily digest
	Duplicate Status = "duplicate" // dropped: same key within DedupeWindow
)

// Result is the fan-out's answer for one notification.
type Result struct {
	Status   Status
	Channels []Channel // channels it went out on, in the user's order
}

// Record is a notification together with what happened to it.
type Record struct {
	Notification
	Result
}

// DigestLine is one topic's row in a user's daily digest.
type DigestLine struct {
	Topic  string
	Count  int    // held notifications on the topic
	Latest string // title of the most recent one
}

var (
	ErrUnknownUser     = errors.New("unknown user")
	ErrDuplicateUser   = errors.New("user already exists")
	ErrBadChannel      = errors.New("channels must be email, push or sms, each at most once")
	ErrBadQuietHours   = errors.New("quiet hours must be between 0 and 23")
	ErrBadOffset       = errors.New("utc offset must be between -720 and 840 minutes")
	ErrBadNotification = errors.New("notification needs a topic and a dedupe key")
)
