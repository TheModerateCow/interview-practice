import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * The core of a team calendar's "find a time" feature: attendees in their own time zones, busy blocks in UTC,
 * and searches for the earliest slot that everyone, or a quorum, can make. All times are integer minutes.
 */
public class TeamCalendar {
    private static final int DAY = 1440;

    private record Block(int start, int end, int seq) {}

    private record Span(int s, int e) {}

    private static final class Attendee {
        int offset, workStart, workEnd; // local = UTC + offset
        final Map<String, Block> busy = new HashMap<>();

        Attendee(int offset, int workStart, int workEnd) {
            this.offset = offset;
            this.workStart = workStart;
            this.workEnd = workEnd;
        }

        boolean working(int minute) {
            int local = Math.floorMod(minute + offset, DAY);
            if (workStart < workEnd) return workStart <= local && local < workEnd;
            return local >= workStart || local < workEnd; // overnight shift
        }

        /** Sorted, disjoint, non-touching UTC intervals inside [lo, hi) where this attendee is free. */
        List<Span> free(int lo, int hi) {
            int length = workStart < workEnd ? workEnd - workStart : workEnd + DAY - workStart;
            List<int[]> work = new ArrayList<>();
            int d = Math.floorDiv(lo + offset, DAY) - 1; // the local day before lo's: an overnight shift can run into lo
            while (true) {
                int s = d * DAY + workStart - offset;
                if (s >= hi) break;
                int e = Math.min(s + length, hi);
                s = Math.max(s, lo);
                if (s < e) {
                    if (!work.isEmpty() && s <= work.get(work.size() - 1)[1]) {
                        int[] last = work.get(work.size() - 1);
                        last[1] = Math.max(last[1], e); // back-to-back working days join up
                    } else {
                        work.add(new int[] {s, e});
                    }
                }
                d++;
            }
            List<Span> busyIn = new ArrayList<>();
            for (Block b : busy.values()) if (b.end() > lo && b.start() < hi) busyIn.add(new Span(b.start(), b.end()));
            busyIn.sort((x, y) -> x.s() != y.s() ? Integer.compare(x.s(), y.s()) : Integer.compare(x.e(), y.e()));
            List<Span> out = new ArrayList<>();
            int i = 0;
            for (int[] w : work) {
                while (i < busyIn.size() && busyIn.get(i).e() <= w[0]) i++;
                int cur = w[0];
                for (int j = i; j < busyIn.size() && busyIn.get(j).s() < w[1]; j++) {
                    if (busyIn.get(j).s() > cur) out.add(new Span(cur, busyIn.get(j).s()));
                    cur = Math.max(cur, busyIn.get(j).e());
                }
                if (cur < w[1]) out.add(new Span(cur, w[1]));
            }
            return out;
        }
    }

    private static List<Span> intersect(List<Span> a, List<Span> b) {
        List<Span> out = new ArrayList<>();
        int i = 0, j = 0;
        while (i < a.size() && j < b.size()) {
            int s = Math.max(a.get(i).s(), b.get(j).s()), e = Math.min(a.get(i).e(), b.get(j).e());
            if (s < e) out.add(new Span(s, e));
            if (a.get(i).e() < b.get(j).e()) i++;
            else j++;
        }
        return out;
    }

    private final Map<String, Attendee> people = new HashMap<>();
    private int issued = 0;

    public TeamCalendar() {}

    public boolean addAttendee(String id, int offset, int workStart, int workEnd) {
        if (people.containsKey(id)) return false;
        people.put(id, new Attendee(offset, workStart, workEnd));
        return true;
    }

    public String addBusy(String id, int start, int end) {
        Attendee a = people.get(id);
        if (a == null || start >= end) return null;
        issued++;
        String bid = "busy" + issued;
        a.busy.put(bid, new Block(start, end, issued));
        return bid;
    }

    public boolean removeBusy(String id, String busyId) {
        Attendee a = people.get(id);
        if (a == null || !a.busy.containsKey(busyId)) return false;
        a.busy.remove(busyId);
        return true;
    }

    public boolean isFree(String id, int minute) {
        Attendee a = people.get(id);
        if (a == null || !a.working(minute)) return false;
        for (Block b : a.busy.values()) if (b.start() <= minute && minute < b.end()) return false;
        return true;
    }

    // level 2

    public boolean setOffset(String id, int offset) {
        Attendee a = people.get(id);
        if (a == null) return false;
        a.offset = offset;
        return true;
    }

    public boolean setHours(String id, int workStart, int workEnd) {
        Attendee a = people.get(id);
        if (a == null) return false;
        a.workStart = workStart;
        a.workEnd = workEnd;
        return true;
    }

    public List<String> agenda(String id, int from, int to) {
        Attendee a = people.get(id);
        List<String> out = new ArrayList<>();
        if (a == null) return out;
        List<Map.Entry<String, Block>> hits = new ArrayList<>();
        for (Map.Entry<String, Block> en : a.busy.entrySet()) {
            Block b = en.getValue();
            if (b.start() < to && b.end() > from) hits.add(en);
        }
        hits.sort((p, q) -> {
            Block x = p.getValue(), y = q.getValue();
            if (x.start() != y.start()) return Integer.compare(x.start(), y.start());
            if (x.end() != y.end()) return Integer.compare(x.end(), y.end());
            return Integer.compare(x.seq(), y.seq());
        });
        for (Map.Entry<String, Block> en : hits) out.add(en.getKey() + ":" + en.getValue().start() + "-" + en.getValue().end());
        return out;
    }

    private List<Attendee> lookup(List<String> ids) {
        List<Attendee> out = new ArrayList<>();
        for (String id : ids) {
            Attendee a = people.get(id);
            if (a == null) return null;
            out.add(a);
        }
        return out;
    }

    // level 3

    public int earliestMeeting(List<String> ids, int duration, int from, int to) {
        List<Attendee> ps = lookup(ids);
        if (ps == null) return -1;
        List<Span> common = List.of(new Span(from, to));
        for (Attendee p : ps) common = intersect(common, p.free(from, to));
        for (Span c : common) if (c.e() - c.s() >= duration) return c.s();
        return -1;
    }

    // level 4

    public int earliestQuorumMeeting(List<String> ids, int quorum, int duration, int from, int to) {
        List<Attendee> ps = lookup(ids);
        if (ps == null) return -1;
        List<int[]> events = new ArrayList<>();
        for (Attendee p : ps) {
            for (Span f : p.free(from, to)) {
                if (f.e() - f.s() >= duration) { // the meeting can start anywhere in [s, e - duration]
                    events.add(new int[] {f.s(), 1});
                    events.add(new int[] {f.e() - duration + 1, -1});
                }
            }
        }
        events.sort((x, y) -> Integer.compare(x[0], y[0]));
        int count = 0;
        for (int i = 0; i < events.size(); ) {
            int at = events.get(i)[0];
            while (i < events.size() && events.get(i)[0] == at) count += events.get(i++)[1];
            if (count >= quorum) return at;
        }
        return -1;
    }

    public List<String> freeFor(List<String> ids, int start, int duration) {
        int end = start + duration;
        List<String> out = new ArrayList<>();
        for (String id : ids) {
            Attendee a = people.get(id);
            if (a != null && a.free(start, end).equals(List.of(new Span(start, end)))) out.add(id);
        }
        Collections.sort(out);
        return out;
    }
}
