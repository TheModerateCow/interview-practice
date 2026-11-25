package quota

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleAllowWithinLimit(t *testing.T) {
	s := New()
	s.AddPlan(Plan{Name: "starter", Limit: 5, Window: 60, Burst: 0})
	s.IssueKey("key-1", "org-1", "starter")
	d, err := s.Allow("key-1", 30, 2)
	if err != nil || !d.Allowed || d.Remaining != 3 {
		t.Fatalf("Allow: got %+v, %v; want allowed with 3 remaining", d, err)
	}
}
