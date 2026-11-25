package feed

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleFeedShowsFollowedAccounts(t *testing.T) {
	s := New()
	for _, u := range []string{"ana", "ben", "cy"} {
		s.AddUser(u)
	}
	s.Follow("ana", "ben")
	s.Publish("b1", "ben", 1000, "hello")
	s.Publish("c1", "cy", 1100, "not followed")
	page, err := s.HomeFeed("ana", 2000, 10, "")
	if err != nil || len(page.PostIDs) != 1 || page.PostIDs[0] != "b1" || page.NextCursor != "" {
		t.Fatalf("HomeFeed: got %+v, %v; want [b1] and no cursor", page, err)
	}
}
