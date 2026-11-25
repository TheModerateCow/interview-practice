package notify

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleSendGoesToEmail(t *testing.T) {
	s := New()
	s.AddUser("ana", 0)
	res, err := s.Send(Notification{User: "ana", Topic: "welcome", Key: "welcome-1", Title: "Hi", At: 1000})
	if err != nil || res.Status != Sent || len(res.Channels) != 1 || res.Channels[0] != Email {
		t.Fatalf("Send: got %+v, %v; want sent on email", res, err)
	}
}
