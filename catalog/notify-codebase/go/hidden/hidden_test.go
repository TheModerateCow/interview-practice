package notify

import (
	"errors"
	"fmt"
	"strings"
	"testing"
	"time"
)

// The app compiles one phase's tests at a time: keep every import used outside them.
var (
	_ = errors.Is
	_ = fmt.Sprint
	_ = strings.Join
	_ = time.Second
)

const hiddenHour = 3600
const hiddenDay = 24 * hiddenHour

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenErr(t *testing.T, what string, got, want error) {
	t.Helper()
	if !errors.Is(got, want) {
		t.Fatalf("%s: got error %v want %v", what, got, want)
	}
}

// hiddenUser adds a user at offsetMin (minutes east of UTC) with the given
// channels.
func hiddenUser(t *testing.T, s *Service, id string, offsetMin int, chans ...Channel) {
	t.Helper()
	if err := s.AddUser(id, offsetMin); err != nil {
		t.Fatalf("AddUser(%s): %v", id, err)
	}
	if err := s.SetChannels(id, chans); err != nil {
		t.Fatalf("SetChannels(%s): %v", id, err)
	}
}

func hiddenQuiet(t *testing.T, s *Service, id string, from, to int) {
	t.Helper()
	if err := s.SetQuietHours(id, from, to); err != nil {
		t.Fatalf("SetQuietHours(%s): %v", id, err)
	}
}

func hiddenResult(r Result) string {
	if r.Status != Sent {
		return string(r.Status)
	}
	var names []string
	for _, ch := range r.Channels {
		names = append(names, string(ch))
	}
	return "sent " + strings.Join(names, ",")
}

// hiddenSend sends a notification and renders the result as "sent push,sms",
// "held" or "duplicate".
func hiddenSend(t *testing.T, s *Service, user string, at int64, topic, key string) string {
	t.Helper()
	r, err := s.Send(Notification{User: user, Topic: topic, Key: key, Title: topic + ":" + key, At: at})
	if err != nil {
		t.Fatalf("Send(%s, %d, %s): %v", user, at, key, err)
	}
	return hiddenResult(r)
}

func hiddenUrgent(t *testing.T, s *Service, user string, at int64, topic, key string) string {
	t.Helper()
	r, err := s.Send(Notification{User: user, Topic: topic, Key: key, Title: topic + ":" + key, At: at, Urgent: true})
	if err != nil {
		t.Fatalf("Send urgent(%s, %d, %s): %v", user, at, key, err)
	}
	return hiddenResult(r)
}

func hiddenChannels(t *testing.T, s *Service, id string) string {
	t.Helper()
	u, err := s.User(id)
	if err != nil {
		t.Fatalf("User(%s): %v", id, err)
	}
	return fmt.Sprint(u.Channels)
}

func hiddenDigest(t *testing.T, s *Service, id string, now int64) string {
	t.Helper()
	lines, err := s.Digest(id, now)
	if err != nil {
		t.Fatalf("Digest(%s, %d): %v", id, now, err)
	}
	var out []string
	for _, l := range lines {
		out = append(out, fmt.Sprintf("%s:%d:%s", l.Topic, l.Count, l.Latest))
	}
	return fmt.Sprint(out)
}

// ---------------------------------------------------------------- phase 1

func Test_p1_new_user_defaults(t *testing.T) {
	s := New()
	if err := s.AddUser("ana", 0); err != nil {
		t.Fatal(err)
	}
	hiddenEq(t, "default channels", hiddenChannels(t, s, "ana"), "[email]")
	hiddenEq(t, "late night, no quiet hours", hiddenSend(t, s, "ana", 3*hiddenHour, "billing", "inv-1"), "sent email")
}

func Test_p1_fan_out_in_user_order(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0, SMS, Email, Push)
	hiddenEq(t, "all channels", hiddenSend(t, s, "ana", 1000, "security", "login-1"), "sent sms,email,push")
	hiddenUser(t, s, "ben", 0)
	hiddenEq(t, "no channels: digest", hiddenSend(t, s, "ben", 1000, "security", "login-1"), "held")
	hiddenEq(t, "no channels, urgent: digest", hiddenUrgent(t, s, "ben", 1001, "security", "login-2"), "held")
}

func Test_p1_quiet_hours_utc(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0, Push)
	hiddenQuiet(t, s, "ana", 22, 7)
	hiddenEq(t, "21:59", hiddenSend(t, s, "ana", 22*hiddenHour-60, "promo", "a"), "sent push")
	hiddenEq(t, "22:00", hiddenSend(t, s, "ana", 22*hiddenHour, "promo", "b"), "held")
	hiddenEq(t, "03:00 next day", hiddenSend(t, s, "ana", hiddenDay+3*hiddenHour, "promo", "c"), "held")
	hiddenEq(t, "06:59:59", hiddenSend(t, s, "ana", hiddenDay+7*hiddenHour-1, "promo", "d"), "held")
	hiddenEq(t, "07:00", hiddenSend(t, s, "ana", hiddenDay+7*hiddenHour, "promo", "e"), "sent push")
	hiddenEq(t, "urgent at 23:30", hiddenUrgent(t, s, "ana", hiddenDay+23*hiddenHour+1800, "security", "f"), "sent push")
}

func Test_p1_quiet_hours_east_of_utc(t *testing.T) {
	s := New()
	hiddenUser(t, s, "kai", 8*60, Push, SMS)
	hiddenQuiet(t, s, "kai", 22, 7)
	hiddenEq(t, "15:00 UTC is 23:00 local", hiddenSend(t, s, "kai", 15*hiddenHour, "promo", "a"), "held")
	hiddenEq(t, "22:30 UTC is 06:30 local", hiddenSend(t, s, "kai", 22*hiddenHour+1800, "promo", "b"), "held")
	hiddenEq(t, "23:00 UTC is 07:00 local", hiddenSend(t, s, "kai", 23*hiddenHour, "promo", "c"), "sent push,sms")
	hiddenEq(t, "13:00 UTC is 21:00 local", hiddenSend(t, s, "kai", hiddenDay+13*hiddenHour, "promo", "d"), "sent push,sms")
}

func Test_p1_quiet_hours_west_and_half_hour_offsets(t *testing.T) {
	s := New()
	hiddenUser(t, s, "lee", -5*60, Email)
	hiddenQuiet(t, s, "lee", 22, 7)
	hiddenEq(t, "03:00 UTC is 22:00 local", hiddenSend(t, s, "lee", hiddenDay+3*hiddenHour, "promo", "a"), "held")
	hiddenEq(t, "11:59 UTC is 06:59 local", hiddenSend(t, s, "lee", hiddenDay+12*hiddenHour-60, "promo", "b"), "held")
	hiddenEq(t, "12:00 UTC is 07:00 local", hiddenSend(t, s, "lee", hiddenDay+12*hiddenHour, "promo", "c"), "sent email")
	hiddenUser(t, s, "ria", 5*60+30, Email)
	hiddenQuiet(t, s, "ria", 9, 17)
	hiddenEq(t, "03:30 UTC is 09:00 local", hiddenSend(t, s, "ria", 3*hiddenHour+1800, "promo", "a"), "held")
	hiddenEq(t, "03:29 UTC is 08:59 local", hiddenSend(t, s, "ria", hiddenDay+3*hiddenHour+1740, "promo", "b"), "sent email")
	hiddenEq(t, "11:30 UTC is 17:00 local", hiddenSend(t, s, "ria", hiddenDay+11*hiddenHour+1800, "promo", "c"), "sent email")
}

func Test_p1_dedupe_window(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0, Email)
	hiddenEq(t, "first", hiddenSend(t, s, "ana", 0, "billing", "pay-due"), "sent email")
	hiddenEq(t, "retry after 30 min", hiddenSend(t, s, "ana", 1800, "billing", "pay-due"), "duplicate")
	hiddenEq(t, "retry just inside the hour", hiddenSend(t, s, "ana", 3599, "billing", "pay-due"), "duplicate")
	hiddenEq(t, "an hour after the first", hiddenSend(t, s, "ana", 3600, "billing", "pay-due"), "sent email")
	hiddenEq(t, "other key", hiddenSend(t, s, "ana", 3601, "billing", "pay-late"), "sent email")
	hiddenEq(t, "an hour after the second", hiddenSend(t, s, "ana", 7200, "billing", "pay-due"), "sent email")
}

func Test_p1_dedupe_keys_are_per_user(t *testing.T) {
	s := New()
	for _, id := range []string{"ana", "ben", "cy"} {
		hiddenUser(t, s, id, 0, Push)
	}
	hiddenEq(t, "ana gets the launch", hiddenSend(t, s, "ana", 100, "news", "launch-2026"), "sent push")
	hiddenEq(t, "ben gets the launch", hiddenSend(t, s, "ben", 101, "news", "launch-2026"), "sent push")
	hiddenEq(t, "cy gets the launch", hiddenSend(t, s, "cy", 102, "news", "launch-2026"), "sent push")
	hiddenEq(t, "ana's retry is a duplicate", hiddenSend(t, s, "ana", 200, "news", "launch-2026"), "duplicate")
}

func Test_p1_held_notification_still_dedupes(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0, Push)
	hiddenQuiet(t, s, "ana", 0, 6)
	hiddenEq(t, "held at 05:30", hiddenSend(t, s, "ana", 5*hiddenHour+1800, "social", "like-9"), "held")
	hiddenEq(t, "resent at 06:10", hiddenSend(t, s, "ana", 6*hiddenHour+600, "social", "like-9"), "duplicate")
	hiddenEq(t, "resent at 06:30", hiddenSend(t, s, "ana", 6*hiddenHour+1800, "social", "like-9"), "sent push")
}

func Test_p1_hourly_caps(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0, Push, SMS)
	var got []string
	for i := int64(0); i < 6; i++ {
		got = append(got, hiddenSend(t, s, "ana", 600*i, "chat", fmt.Sprint("m", i)))
	}
	hiddenEq(t, "six messages in an hour", fmt.Sprint(got), "[sent push,sms sent push,sms sent push sent push held held]")
	hiddenEq(t, "first push leaves the window", hiddenSend(t, s, "ana", 3600, "chat", "m6"), "sent push,sms")
	hiddenEq(t, "second slot frees", hiddenSend(t, s, "ana", 4200, "chat", "m7"), "sent push,sms")
	hiddenEq(t, "an hour later all clear", hiddenSend(t, s, "ana", 7800, "chat", "m8"), "sent push,sms")
}

func Test_p1_caps_are_per_user(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0, SMS)
	hiddenUser(t, s, "ben", 0, SMS)
	hiddenSend(t, s, "ana", 0, "otp", "1")
	hiddenSend(t, s, "ana", 1, "otp", "2")
	hiddenEq(t, "ana capped", hiddenUrgent(t, s, "ana", 2, "otp", "3"), "held")
	hiddenEq(t, "ben unaffected", hiddenSend(t, s, "ben", 3, "otp", "1"), "sent sms")
}

func Test_p1_channels_are_not_shared_between_users(t *testing.T) {
	s := New()
	if err := s.AddUser("ana", 0); err != nil {
		t.Fatal(err)
	}
	if err := s.AddUser("ben", 0); err != nil {
		t.Fatal(err)
	}
	row := []Channel{Push, SMS}
	hiddenEq(t, "ana", s.SetChannels("ana", row), nil)
	row[0], row[1] = Email, Push // the import tool reuses its row buffer
	hiddenEq(t, "ben", s.SetChannels("ben", row), nil)
	hiddenEq(t, "ana's channels", hiddenChannels(t, s, "ana"), "[push sms]")
	hiddenEq(t, "ana's send", hiddenSend(t, s, "ana", 10, "security", "new-device"), "sent push,sms")
	hiddenEq(t, "ben's send", hiddenSend(t, s, "ben", 10, "security", "new-device"), "sent email,push")
}

func Test_p1_errors(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 60, Push)
	hiddenQuiet(t, s, "ana", 23, 6)
	hiddenErr(t, "duplicate user", s.AddUser("ana", 0), ErrDuplicateUser)
	hiddenErr(t, "offset too far east", s.AddUser("x", 841), ErrBadOffset)
	hiddenErr(t, "offset too far west", s.AddUser("x", -721), ErrBadOffset)
	hiddenEq(t, "edge offsets", fmt.Sprint(s.AddUser("e", 840), s.AddUser("w", -720)), "<nil> <nil>")
	hiddenErr(t, "unknown channel", s.SetChannels("ana", []Channel{Push, "fax"}), ErrBadChannel)
	hiddenErr(t, "repeated channel", s.SetChannels("ana", []Channel{SMS, SMS}), ErrBadChannel)
	hiddenErr(t, "channels of unknown user", s.SetChannels("nope", nil), ErrUnknownUser)
	hiddenErr(t, "quiet hour 24", s.SetQuietHours("ana", 22, 24), ErrBadQuietHours)
	hiddenErr(t, "quiet hour -1", s.SetQuietHours("ana", -1, 6), ErrBadQuietHours)
	hiddenErr(t, "quiet hours of unknown user", s.SetQuietHours("nope", 1, 2), ErrUnknownUser)
	_, err := s.Send(Notification{User: "nope", Topic: "t", Key: "k", At: 1})
	hiddenErr(t, "send to unknown user", err, ErrUnknownUser)
	_, err = s.Send(Notification{User: "ana", Topic: "", Key: "k", At: 1})
	hiddenErr(t, "no topic", err, ErrBadNotification)
	_, err = s.Send(Notification{User: "ana", Topic: "t", Key: "", At: 1})
	hiddenErr(t, "no key", err, ErrBadNotification)
	_, err = s.User("nope")
	hiddenErr(t, "unknown user", err, ErrUnknownUser)
	u, _ := s.User("ana")
	hiddenEq(t, "ana after failed calls", fmt.Sprintf("%+v", u), "{ID:ana OffsetMin:60 Channels:[push] QuietFrom:23 QuietTo:6}")
}

// ---------------------------------------------------------------- phase 2

func Test_p2_digest_groups_by_topic(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0)
	hiddenSend(t, s, "ana", 100, "billing", "b1")
	hiddenSend(t, s, "ana", 200, "promo", "p1")
	hiddenSend(t, s, "ana", 300, "security", "s1")
	hiddenSend(t, s, "ana", 400, "promo", "p2")
	hiddenSend(t, s, "ana", 500, "billing", "b2")
	hiddenSend(t, s, "ana", 600, "promo", "p3")
	hiddenEq(t, "digest", hiddenDigest(t, s, "ana", hiddenDay+9*hiddenHour), "[promo:3:promo:p3 billing:2:billing:b2 security:1:security:s1]")
}

func Test_p2_digest_covers_only_the_day_before(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0)
	hiddenSend(t, s, "ana", 10, "news", "d0")
	hiddenSend(t, s, "ana", hiddenDay-1, "news", "d0-late")
	hiddenSend(t, s, "ana", hiddenDay, "news", "d1")
	hiddenSend(t, s, "ana", 2*hiddenDay-1, "social", "d1-late")
	hiddenSend(t, s, "ana", 2*hiddenDay, "news", "d2")
	hiddenEq(t, "digest on day 1", hiddenDigest(t, s, "ana", hiddenDay+5), "[news:2:news:d0-late]")
	hiddenEq(t, "digest on day 2", hiddenDigest(t, s, "ana", 2*hiddenDay+20*hiddenHour), "[news:1:news:d1 social:1:social:d1-late]")
	hiddenEq(t, "asked again", hiddenDigest(t, s, "ana", 2*hiddenDay), "[news:1:news:d1 social:1:social:d1-late]")
	hiddenEq(t, "digest on day 0", hiddenDigest(t, s, "ana", 50), "[]")
	hiddenEq(t, "digest on day 4", hiddenDigest(t, s, "ana", 4*hiddenDay), "[]")
}

func Test_p2_digest_uses_the_users_local_day(t *testing.T) {
	s := New()
	hiddenUser(t, s, "kai", 9*60)
	hiddenUser(t, s, "lee", -7*60)
	for _, id := range []string{"kai", "lee"} {
		hiddenSend(t, s, id, hiddenDay+14*hiddenHour, "news", id+"-a")
		hiddenSend(t, s, id, hiddenDay+16*hiddenHour, "news", id+"-b")
		hiddenSend(t, s, id, 2*hiddenDay+6*hiddenHour, "news", id+"-c")
		hiddenSend(t, s, id, 2*hiddenDay+8*hiddenHour, "news", id+"-d")
	}
	hiddenEq(t, "kai at 10:00 UTC day 2", hiddenDigest(t, s, "kai", 2*hiddenDay+10*hiddenHour), "[news:1:news:kai-a]")
	hiddenEq(t, "kai at 16:00 UTC day 2", hiddenDigest(t, s, "kai", 2*hiddenDay+16*hiddenHour), "[news:3:news:kai-d]")
	hiddenEq(t, "lee at 10:00 UTC day 3", hiddenDigest(t, s, "lee", 3*hiddenDay+10*hiddenHour), "[news:1:news:lee-d]")
	hiddenEq(t, "lee at 06:00 UTC day 3", hiddenDigest(t, s, "lee", 3*hiddenDay+6*hiddenHour), "[news:3:news:lee-c]")
}

func Test_p2_digest_has_only_held_notifications(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0, SMS)
	hiddenSend(t, s, "ana", 100, "otp", "c1")
	hiddenSend(t, s, "ana", 200, "otp", "c2")
	hiddenSend(t, s, "ana", 300, "otp", "c3")
	hiddenSend(t, s, "ana", 400, "otp", "c3")
	hiddenSend(t, s, "ana", 500, "alerts", "a1")
	hiddenUrgent(t, s, "ana", 600, "alerts", "a2")
	hiddenSend(t, s, "ana", 3700, "alerts", "a3")
	hiddenEq(t, "capped sends only, no duplicates", hiddenDigest(t, s, "ana", hiddenDay), "[alerts:2:alerts:a2 otp:1:otp:c3]")
}

func Test_p2_digest_latest_title_and_ties(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 60)
	for i, topic := range []string{"zeta", "alpha", "mid", "alpha", "zeta", "mid"} {
		hiddenSend(t, s, "ana", int64(1000+i), topic, fmt.Sprint("k", i))
	}
	_, err := s.Send(Notification{User: "ana", Topic: "mid", Key: "same-second", Title: "last in", At: 1005})
	hiddenEq(t, "send", err, nil)
	hiddenEq(t, "ties by topic, latest title", hiddenDigest(t, s, "ana", hiddenDay), "[mid:3:last in alpha:2:alpha:k3 zeta:2:zeta:k4]")
}

func Test_p2_digest_empty_and_unknown(t *testing.T) {
	s := New()
	hiddenUser(t, s, "ana", 0, Email)
	hiddenSend(t, s, "ana", 100, "billing", "b1")
	got, err := s.Digest("ana", hiddenDay)
	hiddenEq(t, "error", err, nil)
	if got == nil || len(got) != 0 {
		t.Fatalf("nothing held: got %#v want an empty slice", got)
	}
	_, err = s.Digest("nope", hiddenDay)
	hiddenErr(t, "unknown user", err, ErrUnknownUser)
}

// ---------------------------------------------------------------- phase 3

// hiddenChattyUsers replays days of traffic for n users on every channel,
// with quiet hours 23 -> 6 UTC: each sends a notification every 5 seconds
// and every key is sent twice in a row. It returns the count of each status
// and the total number of channel deliveries.
func hiddenChattyUsers(t *testing.T, s *Service, n int, days int64) string {
	t.Helper()
	count := map[Status]int{}
	deliveries := 0
	for u := 0; u < n; u++ {
		id := fmt.Sprint("u", u)
		hiddenUser(t, s, id, 0, Push, Email, SMS)
		hiddenQuiet(t, s, id, 23, 6)
	}
	topics := []string{"chat", "social", "billing", "security", "promo"}
	for i := int64(0); i < days*hiddenDay/5; i++ {
		for u := 0; u < n; u++ {
			id := fmt.Sprint("u", u)
			r, err := s.Send(Notification{User: id, Topic: topics[(i/2)%5], Key: fmt.Sprint(id, "-", i/2), At: i * 5, Urgent: i%97 == 0})
			if err != nil {
				t.Fatalf("Send(%s, %d): %v", id, i*5, err)
			}
			count[r.Status]++
			deliveries += len(r.Channels)
		}
	}
	return fmt.Sprintf("sent %d held %d duplicate %d deliveries %d", count[Sent], count[Held], count[Duplicate], deliveries)
}

func Test_p3_chatty_user_four_days(t *testing.T) {
	s := New()
	start := time.Now()
	got := hiddenChattyUsers(t, s, 1, 4)
	elapsed := time.Since(start)
	hiddenEq(t, "totals", got, "sent 513 held 34047 duplicate 34560 deliveries 1079")
	if elapsed > 500*time.Millisecond {
		t.Fatalf("69,120 sends took %v, budget 500ms", elapsed)
	}
}
