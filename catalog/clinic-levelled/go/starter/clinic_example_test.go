package clinic

import "testing"

// An example to copy. Run your tests with the My tests button.
func TestExampleBookAndDescribe(t *testing.T) {
	c := NewClinic()
	c.AddClinician(1, "dr-x")
	c.AddRoom(2, "room-x")
	c.AddType(3, "flu-shot", 15)
	id, ok := c.Book(4, "dr-x", "pat-x", "flu-shot", 900)
	if !ok || id != "appt1" {
		t.Fatalf("book: got %q, %v want appt1, true", id, ok)
	}
	got, _ := c.Appointment(5, id)
	if want := "dr-x pat-x flu-shot room-x 900-915 booked"; got != want {
		t.Fatalf("appointment: got %q want %q", got, want)
	}
}
