package configstore

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleSetGet(t *testing.T) {
	s := NewStore()
	if !s.Set(1, "svc-api", "replicas", "3") {
		t.Fatal("first set should be new")
	}
	v, ok := s.Get(2, "svc-api", "replicas")
	if !ok || v != "3" {
		t.Fatalf("get: got %q, %v want \"3\", true", v, ok)
	}
}
