import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/** In-memory scheduling core of an outpatient clinic. Timestamps passed to its methods only ever increase. */
public class Clinic {
    /** Minutes after its start that a booked appointment waits before it becomes a no-show. */
    private static final int GRACE = 10;
    /** Minutes before its start that an appointment can be checked in. */
    private static final int CHECK_IN_OPENS = 30;

    private static final class Appt {
        final String id;
        String clinician;
        final String patient, kind;
        String room;
        int start, end;
        String status = "booked"; // booked, checked-in, cancelled, no-show
        final List<String> log = new ArrayList<>();

        Appt(String id, String clinician, String patient, String kind, String room, int start, int end) {
            this.id = id; this.clinician = clinician; this.patient = patient; this.kind = kind;
            this.room = room; this.start = start; this.end = end;
        }

        void record(int ts, String event) { log.add(ts + ":" + event); }

        /** The [start, end) the appointment holds its clinician and room, or null. */
        int[] occupied() {
            if (status.equals("cancelled")) return null;
            if (status.equals("no-show")) return new int[] {start, start + GRACE};
            return new int[] {start, end};
        }

        boolean active() { return status.equals("booked") || status.equals("checked-in"); }
    }

    private record Waiter(String patient, String kind) {}

    private final Set<String> clinicians = new HashSet<>();
    private final TreeSet<String> rooms = new TreeSet<>();
    private final Map<String, Integer> types = new HashMap<>();
    private final List<Appt> appts = new ArrayList<>();
    private final Map<String, Appt> byId = new HashMap<>();
    private final Map<String, List<Waiter>> waitlist = new HashMap<>();

    public Clinic() {}

    /** Whether nothing but skip holds the clinician (or, if room is not null, the room) during [s, e). */
    private boolean free(String clinician, String room, int s, int e, Appt skip) {
        for (Appt a : appts) {
            if (a == skip) continue;
            int[] o = a.occupied();
            if (o == null || !(s < o[1] && o[0] < e)) continue;
            if ((room == null && a.clinician.equals(clinician)) || (room != null && room.equals(a.room))) return false;
        }
        return true;
    }

    /** The smallest room free during [s, e) if the clinician is free too, or null. */
    private String place(String clinician, int s, int e, Appt skip) {
        if (!free(clinician, null, s, e, skip)) return null;
        for (String r : rooms) {
            if (free(null, r, s, e, skip)) return r;
        }
        return null;
    }

    private Appt makeBooking(int t, String clinician, String patient, String kind, int start) {
        Integer d = types.get(kind);
        if (!clinicians.contains(clinician) || d == null || start < t) return null;
        String room = place(clinician, start, start + d, null);
        if (room == null) return null;
        Appt a = new Appt("appt" + (appts.size() + 1), clinician, patient, kind, room, start, start + d);
        a.record(t, "booked");
        appts.add(a);
        byId.put(a.id, a);
        return a;
    }

    /** Offers a slot starting at start to the clinician's waitlist at time t, first in line first. */
    private Appt fill(int t, String clinician, int start) {
        List<Waiter> q = waitlist.get(clinician);
        if (q == null) return null;
        for (int i = 0; i < q.size(); i++) {
            Waiter w = q.get(i);
            Appt a = makeBooking(t, clinician, w.patient(), w.kind(), start);
            if (a != null) {
                q.remove(i);
                return a;
            }
        }
        return null;
    }

    /** Turns every booked appointment whose grace period ended by ts into a no-show, in time order. */
    private void settle(int ts) {
        List<Appt> due = new ArrayList<>();
        for (Appt a : appts) {
            if (a.status.equals("booked") && a.start + GRACE <= ts) due.add(a);
        }
        due.sort(Comparator.comparingInt(a -> a.start)); // stable
        for (Appt a : due) {
            int t = a.start + GRACE;
            a.status = "no-show";
            a.record(t, "no-show");
            Appt n = fill(t, a.clinician, t);
            if (n != null) {
                n.status = "checked-in";
                n.record(t, "checked-in");
            }
        }
    }

    // ---------------------------------------------------------------- level 1

    public boolean addClinician(int ts, String id) {
        settle(ts);
        return clinicians.add(id);
    }

    public boolean addRoom(int ts, String id) {
        settle(ts);
        return rooms.add(id);
    }

    public boolean addType(int ts, String name, int minutes) {
        settle(ts);
        if (types.containsKey(name)) return false;
        types.put(name, minutes);
        return true;
    }

    public String book(int ts, String clinician, String patient, String kind, int start) {
        settle(ts);
        Appt a = makeBooking(ts, clinician, patient, kind, start);
        return a == null ? null : a.id;
    }

    public boolean cancel(int ts, String id) {
        settle(ts);
        Appt a = byId.get(id);
        if (a == null || !a.status.equals("booked") || ts >= a.start) return false;
        a.status = "cancelled";
        a.record(ts, "cancelled");
        fill(ts, a.clinician, a.start);
        return true;
    }

    public String appointment(int ts, String id) {
        settle(ts);
        Appt a = byId.get(id);
        if (a == null) return null;
        String st = a.status;
        if (st.equals("checked-in") && ts >= a.end) st = "completed";
        return a.clinician + " " + a.patient + " " + a.kind + " " + a.room + " " + a.start + "-" + a.end + " " + st;
    }

    // ---------------------------------------------------------------- level 2

    public List<String> schedule(int ts, String clinician) {
        settle(ts);
        List<Appt> mine = new ArrayList<>();
        for (Appt a : appts) {
            if (a.clinician.equals(clinician) && a.active()) mine.add(a);
        }
        mine.sort(Comparator.comparingInt(a -> a.start));
        List<String> out = new ArrayList<>();
        for (Appt a : mine) out.add(a.id + "@" + a.start + "-" + a.end);
        return out;
    }

    public List<String> busiestClinicians(int ts, int n) {
        settle(ts);
        Map<String, Integer> mins = new HashMap<>();
        for (Appt a : appts) {
            if (a.active()) mins.merge(a.clinician, a.end - a.start, Integer::sum);
        }
        List<String> ids = new ArrayList<>(clinicians);
        ids.sort((x, y) -> {
            int mx = mins.getOrDefault(x, 0), my = mins.getOrDefault(y, 0);
            return mx != my ? Integer.compare(my, mx) : x.compareTo(y);
        });
        List<String> out = new ArrayList<>();
        for (String id : ids) {
            if (out.size() == n) break;
            out.add(id + ":" + mins.getOrDefault(id, 0));
        }
        return out;
    }

    public Integer nextFree(int ts, String clinician, String kind, int after) {
        settle(ts);
        Integer d = types.get(kind);
        if (!clinicians.contains(clinician) || d == null || rooms.isEmpty()) return null;
        int lb = Math.max(after, ts);
        TreeSet<Integer> cands = new TreeSet<>();
        cands.add(lb);
        for (Appt a : appts) {
            int[] o = a.occupied();
            if (o != null && o[1] > lb) cands.add(o[1]);
        }
        for (int s : cands) {
            if (place(clinician, s, s + d, null) != null) return s;
        }
        return null; // unreachable: the last end always fits
    }

    // ---------------------------------------------------------------- level 3

    public boolean checkIn(int ts, String id) {
        settle(ts);
        Appt a = byId.get(id);
        if (a == null || !a.status.equals("booked") || ts < a.start - CHECK_IN_OPENS) return false;
        a.status = "checked-in";
        a.record(ts, "checked-in");
        return true;
    }

    public boolean joinWaitlist(int ts, String patient, String clinician, String kind) {
        settle(ts);
        if (!types.containsKey(kind) || !clinicians.contains(clinician)) return false;
        List<Waiter> q = waitlist.computeIfAbsent(clinician, k -> new ArrayList<>());
        for (Waiter w : q) {
            if (w.patient().equals(patient)) return false;
        }
        q.add(new Waiter(patient, kind));
        return true;
    }

    public List<String> waitlist(int ts, String clinician) {
        settle(ts);
        List<String> out = new ArrayList<>();
        for (Waiter w : waitlist.getOrDefault(clinician, List.of())) out.add(w.patient() + ":" + w.kind());
        return out;
    }

    // ---------------------------------------------------------------- level 4

    public boolean reschedule(int ts, String id, int newStart) {
        settle(ts);
        Appt a = byId.get(id);
        if (a == null || !a.status.equals("booked") || ts >= a.start || newStart < ts) return false;
        int d = a.end - a.start;
        String room = place(a.clinician, newStart, newStart + d, a);
        if (room == null) return false;
        int old = a.start;
        a.end = newStart + d;
        a.start = newStart;
        a.room = room;
        a.record(ts, "rescheduled:" + newStart);
        fill(ts, a.clinician, old);
        return true;
    }

    public List<String> handOver(int ts, String fromClinician, String toClinician) {
        settle(ts);
        if (!clinicians.contains(fromClinician) || !clinicians.contains(toClinician) || fromClinician.equals(toClinician)) {
            return null;
        }
        List<Appt> moving = new ArrayList<>();
        for (Appt a : appts) {
            if (a.clinician.equals(fromClinician) && a.status.equals("booked")) moving.add(a);
        }
        moving.sort(Comparator.comparingInt(a -> a.start));
        List<String> clashed = new ArrayList<>();
        for (Appt a : moving) {
            if (free(toClinician, null, a.start, a.end, a)) {
                a.clinician = toClinician;
                a.record(ts, "handed-over:" + toClinician);
                continue;
            }
            a.status = "cancelled";
            a.record(ts, "cancelled");
            clashed.add(a.id);
        }
        List<Waiter> dest = waitlist.computeIfAbsent(toClinician, k -> new ArrayList<>());
        for (Waiter w : waitlist.getOrDefault(fromClinician, List.of())) {
            boolean dup = false;
            for (Waiter x : dest) dup = dup || x.patient().equals(w.patient());
            if (!dup) dest.add(w);
        }
        waitlist.remove(fromClinician);
        return clashed;
    }

    public List<String> history(int ts, String id) {
        settle(ts);
        Appt a = byId.get(id);
        return a == null ? new ArrayList<>() : new ArrayList<>(a.log);
    }
}
