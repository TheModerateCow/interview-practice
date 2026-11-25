// Package clinic is the in-memory scheduling core of an outpatient clinic.
package clinic

// Clinic holds clinicians, rooms, appointment types and appointments.
// Timestamps passed to its methods only ever increase.
type Clinic struct {
	// your state here
}

// NewClinic returns a clinic with no clinicians, rooms or appointment types.
func NewClinic() *Clinic {
	return &Clinic{}
}

// AddClinician adds a clinician. False if the id is already taken.
func (c *Clinic) AddClinician(ts int, id string) bool {
	panic("not implemented")
}

// AddRoom adds a consulting room. False if the id is already taken.
func (c *Clinic) AddRoom(ts int, id string) bool {
	panic("not implemented")
}

// AddType adds an appointment type lasting minutes. False if the name is already taken.
func (c *Clinic) AddType(ts int, name string, minutes int) bool {
	panic("not implemented")
}

// Book books patient with clinician for an appointment of type kind starting at start.
func (c *Clinic) Book(ts int, clinician, patient, kind string, start int) (string, bool) {
	panic("not implemented")
}

// Cancel cancels a booked appointment that hasn't started.
func (c *Clinic) Cancel(ts int, id string) bool {
	panic("not implemented")
}

// Appointment describes an appointment as "clinician patient type room start-end status".
func (c *Clinic) Appointment(ts int, id string) (string, bool) {
	panic("not implemented")
}
