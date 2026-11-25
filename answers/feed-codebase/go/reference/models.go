package feed

import (
	"errors"
	"math"
)

// Errors the feed service returns; test them with errors.Is.
var (
	ErrUnknownUser   = errors.New("no such user")
	ErrUnknownPost   = errors.New("no such post")
	ErrDuplicatePost = errors.New("post already exists")
	ErrBadCursor     = errors.New("bad cursor")
	ErrBadLimit      = errors.New("limit must be at least 1")
	ErrSelfFollow    = errors.New("cannot follow yourself")
)

// Post is one published post. Times are whole seconds since the epoch.
type Post struct {
	ID        string
	Author    string
	CreatedAt int64
	Text      string
	Likes     int
}

// Page is one page of a feed: post ids in order, and the cursor for the next
// page ("" when there is nothing after this page).
type Page struct {
	PostIDs    []string
	NextCursor string
}

// mute is a viewer's mute of one account. Forever mutes have until == nil.
type mute struct {
	target string
	until  *int64
}

// startMute is a mute set at now lasting hours hours.
func startMute(target string, now int64, hours float64) mute {
	until := now + int64(math.Round(hours*60*60))
	return mute{target, &until}
}

// foreverMute is a mute with no end.
func foreverMute(target string) mute { return mute{target: target} }

func (m mute) active(now int64) bool {
	return m.until == nil || now < *m.until
}
