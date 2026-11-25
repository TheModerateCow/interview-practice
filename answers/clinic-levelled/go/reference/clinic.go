// Package clinic is the in-memory scheduling core of an outpatient clinic: clinicians, rooms,
// appointment types, bookings, rankings, check-ins, no-shows, waitlists, reschedules,
// hand-overs and appointment history.
package clinic

import (
	"sort"
	"strconv"
)

// grace is how long after its start a booked appointment waits before it becomes a no-show.
const grace = 10

// checkInOpens is how many minutes before its start an appointment can be checked in.
const checkInOpens = 30

type appt struct {
	id        string
	clinician string
	patient   string
	kind      string
	room      string
	start     int
	end       int
	status    string   // booked, checked-in, cancelled, no-show
	log       []string // "ts:event"
}

func (a *appt) record(ts int, event string) {
	a.log = append(a.log, strconv.Itoa(ts)+":"+event)
}

// occupied is the time the appointment holds its clinician and room.
func (a *appt) occupied() (int, int, bool) {
	switch a.status {
	case "cancelled":
		return 0, 0, false
	case "no-show":
		return a.start, a.start + grace, true
	}
	return a.start, a.end, true
}

func (a *appt) active() bool { return a.status == "booked" || a.status == "checked-in" }

type waiter struct {
	patient string
	kind    string
}

// Clinic holds the clinic's staff, rooms and appointments. Timestamps passed to its methods only ever increase.
type Clinic struct {
	clinicians map[string]bool
	rooms      []string // sorted
	types      map[string]int
	appts      []*appt // in booking order
	byID       map[string]*appt
	waitlist   map[string][]waiter
}

// NewClinic returns a clinic with no clinicians, rooms or appointment types.
func NewClinic() *Clinic {
	return &Clinic{clinicians: map[string]bool{}, types: map[string]int{}, byID: map[string]*appt{}, waitlist: map[string][]waiter{}}
}

// free reports whether nothing but skip holds the clinician (or, if room is set, the room) during [s, e).
func (c *Clinic) free(clinician, room string, s, e int, skip *appt) bool {
	for _, a := range c.appts {
		if a == skip {
			continue
		}
		as, ae, ok := a.occupied()
		if !ok || !(s < ae && as < e) {
			continue
		}
		if (room == "" && a.clinician == clinician) || (room != "" && a.room == room) {
			return false
		}
	}
	return true
}

// place returns the smallest room free during [s, e) if the clinician is free too, or "".
func (c *Clinic) place(clinician string, s, e int, skip *appt) string {
	if !c.free(clinician, "", s, e, skip) {
		return ""
	}
	for _, r := range c.rooms {
		if c.free("", r, s, e, skip) {
			return r
		}
	}
	return ""
}

// book creates an appointment at time t, or returns nil.
func (c *Clinic) book(t int, clinician, patient, kind string, start int) *appt {
	d, ok := c.types[kind]
	if !c.clinicians[clinician] || !ok || start < t {
		return nil
	}
	room := c.place(clinician, start, start+d, nil)
	if room == "" {
		return nil
	}
	a := &appt{id: "appt" + strconv.Itoa(len(c.appts)+1), clinician: clinician, patient: patient, kind: kind,
		room: room, start: start, end: start + d, status: "booked"}
	a.record(t, "booked")
	c.appts = append(c.appts, a)
	c.byID[a.id] = a
	return a
}

// fill offers a slot starting at start to the clinician's waitlist at time t, first in line first.
func (c *Clinic) fill(t int, clinician string, start int) *appt {
	q := c.waitlist[clinician]
	for i, w := range q {
		if a := c.book(t, clinician, w.patient, w.kind, start); a != nil {
			c.waitlist[clinician] = append(q[:i:i], q[i+1:]...)
			return a
		}
	}
	return nil
}

// settle turns every booked appointment whose grace period ended by ts into a no-show, in time order,
// and offers each freed slot to the waitlist at the moment it was freed.
func (c *Clinic) settle(ts int) {
	var due []*appt
	for _, a := range c.appts {
		if a.status == "booked" && a.start+grace <= ts {
			due = append(due, a)
		}
	}
	sort.SliceStable(due, func(i, j int) bool { return due[i].start < due[j].start })
	for _, a := range due {
		t := a.start + grace
		a.status = "no-show"
		a.record(t, "no-show")
		if n := c.fill(t, a.clinician, t); n != nil {
			n.status = "checked-in"
			n.record(t, "checked-in")
		}
	}
}

// ---------------------------------------------------------------- level 1

// AddClinician adds a clinician. False if the id is already taken.
func (c *Clinic) AddClinician(ts int, id string) bool {
	c.settle(ts)
	if c.clinicians[id] {
		return false
	}
	c.clinicians[id] = true
	return true
}

// AddRoom adds a consulting room. False if the id is already taken.
func (c *Clinic) AddRoom(ts int, id string) bool {
	c.settle(ts)
	i := sort.SearchStrings(c.rooms, id)
	if i < len(c.rooms) && c.rooms[i] == id {
		return false
	}
	c.rooms = append(c.rooms, "")
	copy(c.rooms[i+1:], c.rooms[i:])
	c.rooms[i] = id
	return true
}

// AddType adds an appointment type lasting minutes. False if the name is already taken.
func (c *Clinic) AddType(ts int, name string, minutes int) bool {
	c.settle(ts)
	if _, ok := c.types[name]; ok {
		return false
	}
	c.types[name] = minutes
	return true
}

// Book books patient with clinician for an appointment of type kind starting at start.
func (c *Clinic) Book(ts int, clinician, patient, kind string, start int) (string, bool) {
	c.settle(ts)
	a := c.book(ts, clinician, patient, kind, start)
	if a == nil {
		return "", false
	}
	return a.id, true
}

// Cancel cancels a booked appointment that hasn't started.
func (c *Clinic) Cancel(ts int, id string) bool {
	c.settle(ts)
	a, ok := c.byID[id]
	if !ok || a.status != "booked" || ts >= a.start {
		return false
	}
	a.status = "cancelled"
	a.record(ts, "cancelled")
	c.fill(ts, a.clinician, a.start)
	return true
}

// Appointment describes an appointment as "clinician patient type room start-end status".
func (c *Clinic) Appointment(ts int, id string) (string, bool) {
	c.settle(ts)
	a, ok := c.byID[id]
	if !ok {
		return "", false
	}
	st := a.status
	if st == "checked-in" && ts >= a.end {
		st = "completed"
	}
	return a.clinician + " " + a.patient + " " + a.kind + " " + a.room + " " +
		strconv.Itoa(a.start) + "-" + strconv.Itoa(a.end) + " " + st, true
}

// ---------------------------------------------------------------- level 2

// Schedule lists the clinician's active appointments as "id@start-end", earliest first.
func (c *Clinic) Schedule(ts int, clinician string) []string {
	c.settle(ts)
	var mine []*appt
	for _, a := range c.appts {
		if a.clinician == clinician && a.active() {
			mine = append(mine, a)
		}
	}
	sort.SliceStable(mine, func(i, j int) bool { return mine[i].start < mine[j].start })
	out := []string{}
	for _, a := range mine {
		out = append(out, a.id+"@"+strconv.Itoa(a.start)+"-"+strconv.Itoa(a.end))
	}
	return out
}

// BusiestClinicians lists up to n clinicians as "id:minutes", most booked minutes first, ties by id.
func (c *Clinic) BusiestClinicians(ts int, n int) []string {
	c.settle(ts)
	mins := map[string]int{}
	ids := []string{}
	for id := range c.clinicians {
		ids = append(ids, id)
	}
	for _, a := range c.appts {
		if a.active() {
			mins[a.clinician] += a.end - a.start
		}
	}
	sort.Slice(ids, func(i, j int) bool {
		if mins[ids[i]] != mins[ids[j]] {
			return mins[ids[i]] > mins[ids[j]]
		}
		return ids[i] < ids[j]
	})
	out := []string{}
	for _, id := range ids {
		if len(out) == n {
			break
		}
		out = append(out, id+":"+strconv.Itoa(mins[id]))
	}
	return out
}

// NextFree returns the earliest start at or after max(after, ts) at which Book would succeed.
func (c *Clinic) NextFree(ts int, clinician, kind string, after int) (int, bool) {
	c.settle(ts)
	d, ok := c.types[kind]
	if !c.clinicians[clinician] || !ok || len(c.rooms) == 0 {
		return 0, false
	}
	lb := max(after, ts)
	cands := []int{lb}
	for _, a := range c.appts {
		if _, e, ok := a.occupied(); ok && e > lb {
			cands = append(cands, e)
		}
	}
	sort.Ints(cands)
	for _, s := range cands {
		if c.place(clinician, s, s+d, nil) != "" {
			return s, true
		}
	}
	return 0, false // unreachable: the last end always fits
}

// ---------------------------------------------------------------- level 3

// CheckIn marks the patient as arrived, from checkInOpens minutes before the start until the no-show.
func (c *Clinic) CheckIn(ts int, id string) bool {
	c.settle(ts)
	a, ok := c.byID[id]
	if !ok || a.status != "booked" || ts < a.start-checkInOpens {
		return false
	}
	a.status = "checked-in"
	a.record(ts, "checked-in")
	return true
}

// JoinWaitlist puts patient at the back of clinician's waitlist for an appointment of type kind.
func (c *Clinic) JoinWaitlist(ts int, patient, clinician, kind string) bool {
	c.settle(ts)
	if _, ok := c.types[kind]; !ok || !c.clinicians[clinician] {
		return false
	}
	for _, w := range c.waitlist[clinician] {
		if w.patient == patient {
			return false
		}
	}
	c.waitlist[clinician] = append(c.waitlist[clinician], waiter{patient, kind})
	return true
}

// Waitlist lists clinician's waitlist as "patient:type", first in line first.
func (c *Clinic) Waitlist(ts int, clinician string) []string {
	c.settle(ts)
	out := []string{}
	for _, w := range c.waitlist[clinician] {
		out = append(out, w.patient+":"+w.kind)
	}
	return out
}

// ---------------------------------------------------------------- level 4

// Reschedule moves a booked appointment that hasn't started to newStart, then offers the old slot to the waitlist.
func (c *Clinic) Reschedule(ts int, id string, newStart int) bool {
	c.settle(ts)
	a, ok := c.byID[id]
	if !ok || a.status != "booked" || ts >= a.start || newStart < ts {
		return false
	}
	room := c.place(a.clinician, newStart, newStart+a.end-a.start, a)
	if room == "" {
		return false
	}
	old := a.start
	a.end, a.start, a.room = newStart+a.end-a.start, newStart, room
	a.record(ts, "rescheduled:"+strconv.Itoa(newStart))
	c.fill(ts, a.clinician, old)
	return true
}

// HandOver moves every booked appointment of from to to, earliest first; those that clash are cancelled.
// It returns the cancelled ids in that order. from's waitlist joins the back of to's.
func (c *Clinic) HandOver(ts int, from, to string) ([]string, bool) {
	c.settle(ts)
	if !c.clinicians[from] || !c.clinicians[to] || from == to {
		return nil, false
	}
	var moving []*appt
	for _, a := range c.appts {
		if a.clinician == from && a.status == "booked" {
			moving = append(moving, a)
		}
	}
	sort.SliceStable(moving, func(i, j int) bool { return moving[i].start < moving[j].start })
	clashed := []string{}
	for _, a := range moving {
		if c.free(to, "", a.start, a.end, a) {
			a.clinician = to
			a.record(ts, "handed-over:"+to)
			continue
		}
		a.status = "cancelled"
		a.record(ts, "cancelled")
		clashed = append(clashed, a.id)
	}
	for _, w := range c.waitlist[from] {
		dup := false
		for _, x := range c.waitlist[to] {
			dup = dup || x.patient == w.patient
		}
		if !dup {
			c.waitlist[to] = append(c.waitlist[to], w)
		}
	}
	delete(c.waitlist, from)
	return clashed, true
}

// History lists what happened to an appointment as "ts:event", oldest first.
func (c *Clinic) History(ts int, id string) []string {
	c.settle(ts)
	a, ok := c.byID[id]
	if !ok {
		return []string{}
	}
	return append([]string{}, a.log...)
}
