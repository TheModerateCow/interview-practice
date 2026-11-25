package clinic

import (
	"strconv"
	"testing"
)

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenSame(t *testing.T, what string, got, want []string) {
	t.Helper()
	if got == nil {
		t.Fatalf("%s: got a nil slice, want %q", what, want)
	}
	if len(got) != len(want) {
		t.Fatalf("%s: got %q want %q", what, got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("%s: got %q want %q", what, got, want)
		}
	}
}

// hiddenID turns an (id, ok) pair into the id, or "(none)" when the call failed.
func hiddenID(id string, ok bool) string {
	if !ok {
		return "(none)"
	}
	return id
}

// hiddenNum turns a (minute, ok) pair into the minute as text, or "(none)" when the call failed.
func hiddenNum(v int, ok bool) string {
	if !ok {
		return "(none)"
	}
	return strconv.Itoa(v)
}

// hiddenClinic adds the clinicians, then the rooms, then the types checkup (30 min), consult (60) and
// review (20), at timestamps 1, 2, 3, ... (never above 10 for the sizes used here).
func hiddenClinic(clinicians, rooms []string) *Clinic {
	c := NewClinic()
	ts := 1
	for _, id := range clinicians {
		c.AddClinician(ts, id)
		ts++
	}
	for _, id := range rooms {
		c.AddRoom(ts, id)
		ts++
	}
	c.AddType(ts, "checkup", 30)
	c.AddType(ts+1, "consult", 60)
	c.AddType(ts+2, "review", 20)
	return c
}

// ---------------------------------------------------------------- level 1

func Test_l1_add_and_book(t *testing.T) {
	c := NewClinic()
	hiddenEq(t, "add clinician", c.AddClinician(1, "dr-a"), true)
	hiddenEq(t, "add clinician twice", c.AddClinician(2, "dr-a"), false)
	hiddenEq(t, "ids are case-sensitive", c.AddClinician(3, "DR-A"), true)
	hiddenEq(t, "add room", c.AddRoom(4, "room-1"), true)
	hiddenEq(t, "add room twice", c.AddRoom(5, "room-1"), false)
	hiddenEq(t, "add type", c.AddType(6, "checkup", 30), true)
	hiddenEq(t, "add type twice", c.AddType(7, "checkup", 45), false)
	hiddenEq(t, "book", hiddenID(c.Book(8, "dr-a", "pat-1", "checkup", 540)), "appt1")
	hiddenEq(t, "details", hiddenID(c.Appointment(9, "appt1")), "dr-a pat-1 checkup room-1 540-570 booked")
}

func Test_l1_book_rejected(t *testing.T) {
	c := NewClinic()
	c.AddClinician(1, "dr-a")
	c.AddType(2, "checkup", 30)
	hiddenEq(t, "no rooms yet", hiddenID(c.Book(3, "dr-a", "pat-1", "checkup", 540)), "(none)")
	c.AddRoom(4, "room-1")
	hiddenEq(t, "unknown clinician", hiddenID(c.Book(5, "dr-z", "pat-1", "checkup", 540)), "(none)")
	hiddenEq(t, "unknown type", hiddenID(c.Book(6, "dr-a", "pat-1", "x-ray", 540)), "(none)")
	hiddenEq(t, "start in the past", hiddenID(c.Book(20, "dr-a", "pat-1", "checkup", 19)), "(none)")
	hiddenEq(t, "start right now", hiddenID(c.Book(21, "dr-a", "pat-1", "checkup", 21)), "appt1")
	hiddenEq(t, "failures use no ids", hiddenID(c.Book(22, "dr-a", "pat-2", "checkup", 540)), "appt2")
	hiddenEq(t, "nothing else booked", hiddenID(c.Appointment(23, "appt3")), "(none)")
}

func Test_l1_clinician_clash(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1", "room-2", "room-3"})
	hiddenEq(t, "book", hiddenID(c.Book(20, "dr-a", "pat-1", "checkup", 540)), "appt1")
	hiddenEq(t, "overlaps the end", hiddenID(c.Book(21, "dr-a", "pat-2", "consult", 500)), "(none)")
	hiddenEq(t, "overlaps the start", hiddenID(c.Book(22, "dr-a", "pat-2", "review", 560)), "(none)")
	hiddenEq(t, "inside", hiddenID(c.Book(23, "dr-a", "pat-2", "review", 545)), "(none)")
	hiddenEq(t, "right after", hiddenID(c.Book(24, "dr-a", "pat-2", "review", 570)), "appt2")
	hiddenEq(t, "right before", hiddenID(c.Book(25, "dr-a", "pat-3", "review", 520)), "appt3")
	hiddenEq(t, "other clinician same time", hiddenID(c.Book(26, "dr-b", "pat-4", "checkup", 540)), "appt4")
	hiddenEq(t, "right after keeps its room", hiddenID(c.Appointment(27, "appt2")), "dr-a pat-2 review room-1 570-590 booked")
	hiddenEq(t, "other clinician gets the next room", hiddenID(c.Appointment(28, "appt4")), "dr-b pat-4 checkup room-2 540-570 booked")
}

func Test_l1_rooms_assigned(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b", "dr-c"}, []string{"room-2", "room-1"})
	c.Book(20, "dr-a", "pat-1", "consult", 600)
	c.Book(21, "dr-b", "pat-2", "checkup", 630)
	hiddenEq(t, "smallest room first", hiddenID(c.Appointment(22, "appt1")), "dr-a pat-1 consult room-1 600-660 booked")
	hiddenEq(t, "next free room", hiddenID(c.Appointment(23, "appt2")), "dr-b pat-2 checkup room-2 630-660 booked")
	hiddenEq(t, "every room taken", hiddenID(c.Book(24, "dr-c", "pat-3", "review", 640)), "(none)")
	hiddenEq(t, "room-2 free until 630", hiddenID(c.Book(25, "dr-c", "pat-3", "review", 605)), "appt3")
	hiddenEq(t, "it went to room-2", hiddenID(c.Appointment(26, "appt3")), "dr-c pat-3 review room-2 605-625 booked")
	hiddenEq(t, "rooms free again at 660", hiddenID(c.Book(27, "dr-c", "pat-4", "review", 660)), "appt4")
	hiddenEq(t, "room-1 again", hiddenID(c.Appointment(28, "appt4")), "dr-c pat-4 review room-1 660-680 booked")
}

func Test_l1_cancel(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "consult", 100)
	hiddenEq(t, "cancel", c.Cancel(21, "appt1"), true)
	hiddenEq(t, "cancelled", hiddenID(c.Appointment(22, "appt1")), "dr-a pat-1 consult room-1 100-160 cancelled")
	hiddenEq(t, "cancel twice", c.Cancel(23, "appt1"), false)
	hiddenEq(t, "cancel unknown", c.Cancel(24, "appt7"), false)
	hiddenEq(t, "slot is free again", hiddenID(c.Book(25, "dr-b", "pat-2", "checkup", 110)), "appt2")
	hiddenEq(t, "new booking gets the room", hiddenID(c.Appointment(26, "appt2")), "dr-b pat-2 checkup room-1 110-140 booked")
	hiddenEq(t, "cancel at the start is too late", c.Cancel(110, "appt2"), false)
	hiddenEq(t, "still booked", hiddenID(c.Appointment(111, "appt2")), "dr-b pat-2 checkup room-1 110-140 booked")
}

func Test_l1_many_bookings(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1", "room-2"})
	ts := 20
	want := []string{}
	for i := 0; i < 6; i++ {
		who := []string{"dr-a", "dr-b"}[i%2]
		id := hiddenID(c.Book(ts, who, "pat-"+strconv.Itoa(i), "review", 600+(i/2)*20))
		want = append(want, id)
		ts++
	}
	hiddenEq(t, "ids in booking order", want[5], "appt6")
	hiddenEq(t, "third for dr-a", hiddenID(c.Appointment(ts, "appt5")), "dr-a pat-4 review room-1 640-660 booked")
	hiddenEq(t, "third for dr-b", hiddenID(c.Appointment(ts+1, "appt6")), "dr-b pat-5 review room-2 640-660 booked")
	hiddenEq(t, "cancel the middle one", c.Cancel(ts+2, "appt3"), true)
	hiddenEq(t, "dr-b is busy then", hiddenID(c.Book(ts+3, "dr-b", "pat-9", "review", 610)), "(none)")
	hiddenEq(t, "dr-a fills it", hiddenID(c.Book(ts+4, "dr-a", "pat-9", "review", 620)), "appt7")
	hiddenEq(t, "in room-1", hiddenID(c.Appointment(ts+5, "appt7")), "dr-a pat-9 review room-1 620-640 booked")
}

// ---------------------------------------------------------------- level 2

func Test_l2_schedule(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1", "room-2"})
	c.Book(20, "dr-a", "pat-1", "consult", 700)
	c.Book(21, "dr-a", "pat-2", "checkup", 540)
	c.Book(22, "dr-b", "pat-3", "review", 600)
	c.Book(23, "dr-a", "pat-4", "review", 600)
	hiddenSame(t, "earliest first", c.Schedule(24, "dr-a"), []string{"appt2@540-570", "appt4@600-620", "appt1@700-760"})
	c.Cancel(25, "appt4")
	hiddenSame(t, "cancelled left out", c.Schedule(26, "dr-a"), []string{"appt2@540-570", "appt1@700-760"})
	hiddenSame(t, "other clinician", c.Schedule(27, "dr-b"), []string{"appt3@600-620"})
	hiddenSame(t, "unknown clinician", c.Schedule(28, "dr-z"), []string{})
}

func Test_l2_busiest_order(t *testing.T) {
	c := hiddenClinic([]string{"dr-c", "dr-b", "dr-a", "dr-d"}, []string{"room-1", "room-2", "room-3"})
	c.Book(20, "dr-a", "pat-1", "checkup", 600)
	c.Book(21, "dr-a", "pat-2", "review", 630)
	c.Book(22, "dr-b", "pat-3", "consult", 600)
	c.Book(23, "dr-c", "pat-4", "checkup", 600)
	c.Book(24, "dr-c", "pat-5", "review", 700)
	hiddenSame(t, "most minutes first, ties by id", c.BusiestClinicians(25, 4), []string{"dr-b:60", "dr-a:50", "dr-c:50", "dr-d:0"})
	hiddenSame(t, "limited", c.BusiestClinicians(26, 2), []string{"dr-b:60", "dr-a:50"})
	hiddenSame(t, "more than there are", c.BusiestClinicians(27, 9), []string{"dr-b:60", "dr-a:50", "dr-c:50", "dr-d:0"})
	hiddenSame(t, "none asked", c.BusiestClinicians(28, 0), []string{})
}

func Test_l2_busiest_counts_only_bookings(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "consult", 600)
	c.Book(21, "dr-b", "pat-2", "checkup", 600)
	c.Book(22, "dr-b", "pat-2", "checkup", 660)
	c.Book(23, "dr-b", "pat-3", "consult", 700)
	hiddenSame(t, "before the cancel", c.BusiestClinicians(24, 2), []string{"dr-b:90", "dr-a:60"})
	c.Cancel(25, "appt3")
	hiddenSame(t, "failed and cancelled bookings add nothing", c.BusiestClinicians(26, 2), []string{"dr-a:60", "dr-b:30"})
}

func Test_l2_next_free_own_schedule(t *testing.T) {
	c := hiddenClinic([]string{"dr-a"}, []string{"room-1", "room-2"})
	hiddenEq(t, "empty diary", hiddenNum(c.NextFree(20, "dr-a", "checkup", 600)), "600")
	hiddenEq(t, "never before now", hiddenNum(c.NextFree(21, "dr-a", "checkup", 5)), "21")
	c.Book(22, "dr-a", "pat-1", "checkup", 600)
	c.Book(23, "dr-a", "pat-2", "checkup", 650)
	hiddenEq(t, "after the first", hiddenNum(c.NextFree(24, "dr-a", "review", 610)), "630")
	hiddenEq(t, "gap too short for a consult", hiddenNum(c.NextFree(25, "dr-a", "consult", 590)), "680")
	hiddenEq(t, "fits before", hiddenNum(c.NextFree(26, "dr-a", "checkup", 560)), "560")
	hiddenEq(t, "touching is fine", hiddenNum(c.NextFree(27, "dr-a", "review", 630)), "630")
}

func Test_l2_next_free_rooms(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b", "dr-c"}, []string{"room-1", "room-2"})
	c.Book(20, "dr-b", "pat-1", "consult", 600)
	c.Book(21, "dr-c", "pat-2", "checkup", 620)
	hiddenEq(t, "waits for a room", hiddenNum(c.NextFree(22, "dr-a", "review", 625)), "650")
	hiddenEq(t, "the slot is bookable", hiddenID(c.Book(23, "dr-a", "pat-3", "review", 650)), "appt3")
	hiddenEq(t, "before the rooms fill", hiddenNum(c.NextFree(24, "dr-a", "review", 595)), "595")
	hiddenEq(t, "too long to fit before", hiddenNum(c.NextFree(25, "dr-a", "consult", 570)), "670")
}

func Test_l2_next_free_rejected(t *testing.T) {
	c := hiddenClinic([]string{"dr-a"}, nil)
	hiddenEq(t, "no rooms", hiddenNum(c.NextFree(20, "dr-a", "checkup", 600)), "(none)")
	c.AddRoom(21, "room-1")
	hiddenEq(t, "unknown clinician", hiddenNum(c.NextFree(22, "dr-z", "checkup", 600)), "(none)")
	hiddenEq(t, "unknown type", hiddenNum(c.NextFree(23, "dr-a", "x-ray", 600)), "(none)")
	c.Book(24, "dr-a", "pat-1", "checkup", 600)
	c.Cancel(25, "appt1")
	hiddenEq(t, "cancelled slot is free", hiddenNum(c.NextFree(26, "dr-a", "checkup", 600)), "600")
}

// ---------------------------------------------------------------- level 3

func Test_l3_no_show_after_grace(t *testing.T) {
	c := hiddenClinic([]string{"dr-a"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "checkup", 100)
	hiddenEq(t, "late but not yet", hiddenID(c.Appointment(109, "appt1")), "dr-a pat-1 checkup room-1 100-130 booked")
	hiddenEq(t, "no-show at start+10", hiddenID(c.Appointment(110, "appt1")), "dr-a pat-1 checkup room-1 100-130 no-show")
	hiddenEq(t, "too late to check in", c.CheckIn(111, "appt1"), false)
	hiddenEq(t, "too late to cancel", c.Cancel(112, "appt1"), false)
	hiddenSame(t, "left out of the schedule", c.Schedule(113, "dr-a"), []string{})
	hiddenSame(t, "and the minutes", c.BusiestClinicians(114, 1), []string{"dr-a:0"})
}

func Test_l3_check_in(t *testing.T) {
	c := hiddenClinic([]string{"dr-a"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "checkup", 100)
	c.Book(21, "dr-a", "pat-2", "checkup", 200)
	hiddenEq(t, "too early", c.CheckIn(69, "appt1"), false)
	hiddenEq(t, "opens 30 minutes before", c.CheckIn(70, "appt1"), true)
	hiddenEq(t, "check in twice", c.CheckIn(71, "appt1"), false)
	hiddenEq(t, "can't cancel once here", c.Cancel(72, "appt1"), false)
	hiddenEq(t, "checked in", hiddenID(c.Appointment(129, "appt1")), "dr-a pat-1 checkup room-1 100-130 checked-in")
	hiddenEq(t, "completed at its end", hiddenID(c.Appointment(130, "appt1")), "dr-a pat-1 checkup room-1 100-130 completed")
	hiddenEq(t, "late arrival within grace", c.CheckIn(209, "appt2"), true)
	hiddenSame(t, "both still count", c.Schedule(300, "dr-a"), []string{"appt1@100-130", "appt2@200-230"})
	hiddenEq(t, "unknown", c.CheckIn(301, "appt9"), false)
}

func Test_l3_no_show_frees_the_rest(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "consult", 100)
	hiddenEq(t, "busy while booked", hiddenNum(c.NextFree(21, "dr-b", "review", 95)), "160")
	hiddenEq(t, "freed from start+10", hiddenNum(c.NextFree(105, "dr-b", "review", 95)), "160")
	hiddenEq(t, "after the no-show", hiddenNum(c.NextFree(111, "dr-b", "review", 95)), "111")
	hiddenEq(t, "room taken again", hiddenID(c.Book(112, "dr-b", "pat-2", "checkup", 120)), "appt2")
	hiddenEq(t, "clinician free again", hiddenID(c.Book(113, "dr-a", "pat-3", "review", 150)), "appt3")
	hiddenEq(t, "but not the room yet", hiddenID(c.Book(114, "dr-a", "pat-4", "review", 130)), "(none)")
}

func Test_l3_waitlist_fills_cancellation(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1", "room-2"})
	c.Book(20, "dr-a", "pat-1", "checkup", 100)
	c.Book(21, "dr-a", "pat-2", "checkup", 130)
	hiddenEq(t, "join", c.JoinWaitlist(22, "pat-x", "dr-a", "consult"), true)
	hiddenEq(t, "join", c.JoinWaitlist(23, "pat-y", "dr-a", "checkup"), true)
	hiddenEq(t, "join", c.JoinWaitlist(24, "pat-z", "dr-a", "review"), true)
	hiddenEq(t, "already waiting", c.JoinWaitlist(25, "pat-x", "dr-a", "review"), false)
	hiddenEq(t, "unknown clinician", c.JoinWaitlist(26, "pat-x", "dr-z", "review"), false)
	hiddenEq(t, "unknown type", c.JoinWaitlist(27, "pat-x", "dr-b", "x-ray"), false)
	hiddenSame(t, "in order", c.Waitlist(28, "dr-a"), []string{"pat-x:consult", "pat-y:checkup", "pat-z:review"})
	hiddenEq(t, "cancel", c.Cancel(29, "appt1"), true)
	hiddenEq(t, "consult doesn't fit, checkup does", hiddenID(c.Appointment(30, "appt3")), "dr-a pat-y checkup room-1 100-130 booked")
	hiddenSame(t, "pat-y left the list", c.Waitlist(31, "dr-a"), []string{"pat-x:consult", "pat-z:review"})
	hiddenSame(t, "other lists untouched", c.Waitlist(32, "dr-b"), []string{})
}

func Test_l3_waitlist_fills_no_show(t *testing.T) {
	c := hiddenClinic([]string{"dr-a"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "consult", 100)
	c.JoinWaitlist(21, "pat-w", "dr-a", "checkup")
	hiddenEq(t, "noticed much later", hiddenID(c.Appointment(200, "appt2")), "dr-a pat-w checkup room-1 110-140 completed")
	hiddenSame(t, "list empty", c.Waitlist(201, "dr-a"), []string{})
	hiddenSame(t, "in the schedule", c.Schedule(202, "dr-a"), []string{"appt2@110-140"})
	hiddenSame(t, "counts its minutes", c.BusiestClinicians(203, 1), []string{"dr-a:30"})
}

func Test_l3_no_shows_in_time_order(t *testing.T) {
	c := hiddenClinic([]string{"dr-a"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "checkup", 200)
	c.Book(21, "dr-a", "pat-2", "checkup", 150)
	c.JoinWaitlist(22, "pat-w", "dr-a", "checkup")
	c.JoinWaitlist(23, "pat-v", "dr-a", "consult")
	hiddenEq(t, "earliest no-show filled first", hiddenID(c.Appointment(400, "appt3")), "dr-a pat-w checkup room-1 160-190 completed")
	hiddenEq(t, "consult waits for the later slot", hiddenID(c.Appointment(401, "appt4")), "dr-a pat-v consult room-1 210-270 completed")
	hiddenEq(t, "first booking", hiddenID(c.Appointment(402, "appt1")), "dr-a pat-1 checkup room-1 200-230 no-show")
}

// ---------------------------------------------------------------- level 4

func Test_l4_reschedule(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1", "room-2"})
	c.Book(20, "dr-a", "pat-1", "checkup", 100)
	c.Book(21, "dr-b", "pat-2", "consult", 200)
	c.Book(22, "dr-a", "pat-3", "checkup", 300)
	hiddenEq(t, "move by 10 overlaps itself", c.Reschedule(23, "appt1", 110), true)
	hiddenEq(t, "moved", hiddenID(c.Appointment(24, "appt1")), "dr-a pat-1 checkup room-1 110-140 booked")
	hiddenEq(t, "into the clinician's other slot", c.Reschedule(25, "appt1", 290), false)
	hiddenEq(t, "into the past", c.Reschedule(26, "appt1", 25), false)
	hiddenEq(t, "next to another clinician", c.Reschedule(27, "appt1", 210), true)
	hiddenEq(t, "takes the free room", hiddenID(c.Appointment(28, "appt1")), "dr-a pat-1 checkup room-2 210-240 booked")
	hiddenEq(t, "unknown", c.Reschedule(29, "appt9", 400), false)
	hiddenEq(t, "started", c.Reschedule(205, "appt2", 500), false)
	c.CheckIn(280, "appt3")
	hiddenEq(t, "checked in", c.Reschedule(281, "appt3", 500), false)
}

func Test_l4_reschedule_offers_old_slot(t *testing.T) {
	c := hiddenClinic([]string{"dr-a"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "checkup", 100)
	c.JoinWaitlist(21, "pat-w", "dr-a", "review")
	hiddenEq(t, "move later", c.Reschedule(22, "appt1", 300), true)
	hiddenEq(t, "old slot goes to the list", hiddenID(c.Appointment(23, "appt2")), "dr-a pat-w review room-1 100-120 booked")
	hiddenSame(t, "schedule", c.Schedule(24, "dr-a"), []string{"appt2@100-120", "appt1@300-330"})
	hiddenEq(t, "cancel", c.Cancel(25, "appt2"), true)
	hiddenEq(t, "cancelled can't move", c.Reschedule(26, "appt2", 400), false)
}

func Test_l4_hand_over(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1", "room-2", "room-3"})
	c.Book(20, "dr-a", "pat-1", "checkup", 300)
	c.Book(21, "dr-a", "pat-2", "checkup", 100)
	c.Book(22, "dr-a", "pat-3", "review", 200)
	c.Book(23, "dr-a", "pat-4", "review", 150)
	c.Book(24, "dr-b", "pat-5", "consult", 290)
	c.Book(25, "dr-b", "pat-6", "review", 205)
	c.CheckIn(90, "appt2")
	clashed, ok := c.HandOver(91, "dr-a", "dr-b")
	hiddenEq(t, "ok", ok, true)
	hiddenSame(t, "clashes, earliest first", clashed, []string{"appt3", "appt1"})
	hiddenSame(t, "dr-b now", c.Schedule(92, "dr-b"), []string{"appt4@150-170", "appt6@205-225", "appt5@290-350"})
	hiddenSame(t, "dr-a keeps the patient already here", c.Schedule(93, "dr-a"), []string{"appt2@100-130"})
	hiddenEq(t, "moved keeps its room", hiddenID(c.Appointment(94, "appt4")), "dr-b pat-4 review room-1 150-170 booked")
	hiddenEq(t, "clash cancelled", hiddenID(c.Appointment(95, "appt1")), "dr-a pat-1 checkup room-1 300-330 cancelled")
	hiddenSame(t, "minutes follow", c.BusiestClinicians(96, 2), []string{"dr-b:100", "dr-a:30"})
}

func Test_l4_hand_over_waitlist(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b", "dr-c"}, []string{"room-1"})
	c.JoinWaitlist(20, "pat-1", "dr-b", "review")
	c.JoinWaitlist(21, "pat-2", "dr-a", "checkup")
	c.JoinWaitlist(22, "pat-1", "dr-a", "consult")
	c.JoinWaitlist(23, "pat-3", "dr-a", "review")
	clashed, ok := c.HandOver(24, "dr-a", "dr-b")
	hiddenEq(t, "ok", ok, true)
	hiddenSame(t, "nothing to clash", clashed, []string{})
	hiddenSame(t, "joined the back, no duplicates", c.Waitlist(25, "dr-b"), []string{"pat-1:review", "pat-2:checkup", "pat-3:review"})
	hiddenSame(t, "old list empty", c.Waitlist(26, "dr-a"), []string{})
	hiddenEq(t, "dr-a can take new waiters", c.JoinWaitlist(27, "pat-2", "dr-a", "review"), true)
	_, ok = c.HandOver(28, "dr-a", "dr-a")
	hiddenEq(t, "to itself", ok, false)
	_, ok = c.HandOver(29, "dr-a", "dr-z")
	hiddenEq(t, "unknown", ok, false)
	hiddenSame(t, "failed hand-over moves nothing", c.Waitlist(30, "dr-a"), []string{"pat-2:review"})
}

func Test_l4_history(t *testing.T) {
	c := hiddenClinic([]string{"dr-a", "dr-b"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "checkup", 100)
	c.Reschedule(30, "appt1", 200)
	c.HandOver(40, "dr-a", "dr-b")
	c.CheckIn(185, "appt1")
	hiddenSame(t, "every event", c.History(300, "appt1"), []string{"20:booked", "30:rescheduled:200", "40:handed-over:dr-b", "185:checked-in"})
	c.Book(301, "dr-a", "pat-2", "review", 400)
	c.Cancel(302, "appt2")
	hiddenSame(t, "cancelled", c.History(303, "appt2"), []string{"301:booked", "302:cancelled"})
	hiddenSame(t, "unknown", c.History(304, "appt9"), []string{})
}

func Test_l4_history_event_times(t *testing.T) {
	c := hiddenClinic([]string{"dr-a"}, []string{"room-1"})
	c.Book(20, "dr-a", "pat-1", "consult", 100)
	c.JoinWaitlist(21, "pat-w", "dr-a", "review")
	hiddenSame(t, "no-show dated at start+10", c.History(500, "appt1"), []string{"20:booked", "110:no-show"})
	hiddenSame(t, "fill dated at the no-show", c.History(501, "appt2"), []string{"110:booked", "110:checked-in"})
	c.Book(502, "dr-a", "pat-2", "checkup", 600)
	c.JoinWaitlist(503, "pat-v", "dr-a", "checkup")
	c.Cancel(504, "appt3")
	hiddenSame(t, "cancel fill dated at the cancel", c.History(505, "appt4"), []string{"504:booked"})
}
