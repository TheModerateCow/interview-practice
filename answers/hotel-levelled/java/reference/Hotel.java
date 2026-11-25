import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Front desk for a small hotel: rooms with nightly rates, bookings for ranges of nights, check-in and check-out, and the history of every room's rate. Every method takes day first: today's date as an integer. */
public class Hotel {
    private record RateChange(int day, int rate) {}

    private static final class Room {
        final String type;
        int rate;
        final List<RateChange> rates = new ArrayList<>();
        Room(String type, int rate) { this.type = type; this.rate = rate; }
    }

    private static final class Booking {
        final String guest, room;
        final int start, rate;
        int end;
        String status = "booked"; // booked, cancelled, in, out
        Booking(String guest, String room, int start, int end, int rate) {
            this.guest = guest; this.room = room; this.start = start; this.end = end; this.rate = rate;
        }
    }

    private final Map<String, Room> rooms = new HashMap<>();
    private final Map<String, Booking> bookings = new HashMap<>();
    private int nextId;

    public Hotel() {}

    /** True while b still holds its nights: not cancelled and not a no-show. */
    private boolean live(int day, Booking b) {
        if (b.status.equals("cancelled")) return false;
        return !(b.status.equals("booked") && day > b.start);
    }

    private boolean free(int day, String roomId, int checkIn, int checkOut) {
        for (Booking b : bookings.values())
            if (b.room.equals(roomId) && live(day, b) && checkIn < b.end && b.start < checkOut) return false;
        return true;
    }

    private boolean bookable(int day, String roomId, int checkIn, int checkOut) {
        return rooms.containsKey(roomId) && checkIn < checkOut && checkIn >= day && free(day, roomId, checkIn, checkOut);
    }

    // ---------------------------------------------------------------- level 1

    public boolean addRoom(int day, String roomId, String roomType, int rate) {
        if (rooms.containsKey(roomId) || rate <= 0) return false;
        Room r = new Room(roomType, rate);
        r.rates.add(new RateChange(day, rate));
        rooms.put(roomId, r);
        return true;
    }

    public String book(int day, String guest, String roomId, int checkIn, int checkOut) {
        if (!bookable(day, roomId, checkIn, checkOut)) return "";
        String id = "b" + (++nextId);
        bookings.put(id, new Booking(guest, roomId, checkIn, checkOut, rooms.get(roomId).rate));
        return id;
    }

    public boolean cancel(int day, String bookingId) {
        Booking b = bookings.get(bookingId);
        if (b == null || !b.status.equals("booked") || !live(day, b)) return false;
        b.status = "cancelled";
        return true;
    }

    public int cost(int day, String bookingId) {
        Booking b = bookings.get(bookingId);
        if (b == null || !live(day, b)) return -1;
        return (b.end - b.start) * b.rate;
    }

    // ---------------------------------------------------------------- level 2

    public List<String> availableRooms(int day, String roomType, int checkIn, int checkOut) {
        List<String> ids = new ArrayList<>();
        for (var e : rooms.entrySet())
            if (e.getValue().type.equals(roomType) && bookable(day, e.getKey(), checkIn, checkOut)) ids.add(e.getKey());
        ids.sort((a, b) -> {
            int c = Integer.compare(rooms.get(a).rate, rooms.get(b).rate);
            return c != 0 ? c : a.compareTo(b);
        });
        return ids;
    }

    public List<String> topGuests(int day, int n) {
        Map<String, Integer> nights = new HashMap<>();
        for (Booking b : bookings.values())
            if (live(day, b)) nights.merge(b.guest, b.end - b.start, Integer::sum);
        List<String> order = new ArrayList<>(nights.keySet());
        order.sort((a, b) -> {
            int c = Integer.compare(nights.get(b), nights.get(a));
            return c != 0 ? c : a.compareTo(b);
        });
        List<String> out = new ArrayList<>();
        for (String g : order.subList(0, Math.max(0, Math.min(n, order.size())))) out.add(g + "(" + nights.get(g) + ")");
        return out;
    }

    // ---------------------------------------------------------------- level 3

    public boolean checkIn(int day, String bookingId) {
        Booking b = bookings.get(bookingId);
        if (b == null || !b.status.equals("booked") || day != b.start) return false;
        b.status = "in";
        return true;
    }

    public int checkOut(int day, String bookingId) {
        Booking b = bookings.get(bookingId);
        if (b == null || !b.status.equals("in")) return -1;
        b.end = b.start + Math.max(1, Math.min(day, b.end) - b.start);
        b.status = "out";
        return (b.end - b.start) * b.rate;
    }

    // ---------------------------------------------------------------- level 4

    public boolean setRate(int day, String roomId, int rate) {
        Room r = rooms.get(roomId);
        if (r == null || rate <= 0) return false;
        r.rate = rate;
        r.rates.add(new RateChange(day, rate));
        return true;
    }

    public int rateAt(int day, String roomId, int atDay) {
        Room r = rooms.get(roomId);
        if (r == null) return -1;
        int rate = -1;
        for (RateChange c : r.rates) if (c.day() <= atDay) rate = c.rate();
        return rate;
    }
}
