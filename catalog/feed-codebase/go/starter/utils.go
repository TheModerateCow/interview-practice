package feed

import (
	"encoding/base64"
	"math"
	"strconv"
	"strings"
)

// DecaySeconds is the recency worth one doubling of a post's likes.
const DecaySeconds = 6 * 60 * 60

// FeedWindow is how far back the home feed looks, in seconds.
const FeedWindow = 7 * 24 * 60 * 60

// hotScore: each doubling of likes is worth DecaySeconds of recency.
func hotScore(likes int, createdAt int64) float64 {
	return math.Log2(float64(1+likes)) + float64(createdAt)/DecaySeconds
}

// ranksBefore is feed order: highest score first, then lowest post id.
func ranksBefore(scoreA float64, idA string, scoreB float64, idB string) bool {
	if scoreA != scoreB {
		return scoreA > scoreB
	}
	return idA < idB
}

// encodeCursor is the opaque token for the position just after this post.
func encodeCursor(score float64, postID string) string {
	raw := strconv.FormatFloat(score, 'f', 4, 64) + "|" + postID
	return base64.URLEncoding.EncodeToString([]byte(raw))
}

// decodeCursor inverts encodeCursor; anything it did not make is ErrBadCursor.
func decodeCursor(token string) (float64, string, error) {
	b, err := base64.URLEncoding.DecodeString(token)
	if err != nil {
		return 0, "", ErrBadCursor
	}
	score, postID, ok := strings.Cut(string(b), "|")
	if !ok {
		return 0, "", ErrBadCursor
	}
	s, err := strconv.ParseFloat(score, 64)
	if err != nil {
		return 0, "", ErrBadCursor
	}
	return s, postID, nil
}
