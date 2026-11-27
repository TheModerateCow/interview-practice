import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Support desk: tickets with priorities, agents and their queues, SLA due times that pause while a ticket waits on the customer, shift changes and a history of every ticket. Every method takes ts first: the time of the call in minutes. */
public class Desk {
    private static final Map<String, Integer> PRIORITY = Map.of("high", 0, "normal", 1, "low", 2);
    private static final Map<String, Integer> SLA = Map.of("high", 60, "normal", 240, "low", 1440); // minutes to resolve
    private static final Set<String> MOVES = Set.of("open>in_progress", "in_progress>open", "in_progress>resolved", "resolved>open",
            "in_progress>waiting", "waiting>in_progress");

    private static final class Ticket {
        final String id, customer, priority;
        final int num, opened;
        String status = "open", agent = "";
        int paused, waitStart;
        final List<String> history = new ArrayList<>();
        Ticket(String id, int num, String customer, String priority, int opened) {
            this.id = id; this.num = num; this.customer = customer; this.priority = priority; this.opened = opened;
        }
    }

    private final Map<String, Boolean> agents = new HashMap<>(); // agent -> on shift
    private final Map<String, Ticket> tickets = new HashMap<>();
    private int nextId;

    public Desk() {}

    private void put(int ts, Ticket t, String agent) {
        t.agent = agent;
        t.history.add(ts + ":assigned:" + agent);
    }

    /** The on-shift agent with the fewest unresolved tickets, ties by name; "" if nobody is on shift. */
    private String pick(int ts) {
        String best = "";
        int bestLoad = 0;
        for (Map.Entry<String, Boolean> e : agents.entrySet()) {
            if (!e.getValue()) continue;
            String a = e.getKey();
            int load = queue(ts, a).size();
            if (best.isEmpty() || load < bestLoad || (load == bestLoad && a.compareTo(best) < 0)) {
                best = a;
                bestLoad = load;
            }
        }
        return best;
    }

    private static int due(int ts, Ticket t) {
        int paused = t.paused;
        if (t.status.equals("waiting")) paused += ts - t.waitStart;
        return t.opened + SLA.get(t.priority) + paused;
    }

    // ---------------------------------------------------------------- level 1

    public boolean addAgent(int ts, String agent) {
        if (agents.containsKey(agent)) return false;
        agents.put(agent, true);
        return true;
    }

    public String openTicket(int ts, String customer, String priority) {
        if (!PRIORITY.containsKey(priority)) return "";
        nextId++;
        String id = "t" + nextId;
        Ticket t = new Ticket(id, nextId, customer, priority, ts);
        t.history.add(ts + ":opened");
        tickets.put(id, t);
        return id;
    }

    public boolean assign(int ts, String ticketId, String agent) {
        Ticket t = tickets.get(ticketId);
        if (t == null || !agents.getOrDefault(agent, false) || t.status.equals("resolved") || t.agent.equals(agent)) return false;
        put(ts, t, agent);
        return true;
    }

    public boolean setStatus(int ts, String ticketId, String status) {
        Ticket t = tickets.get(ticketId);
        if (t == null || !MOVES.contains(t.status + ">" + status)) return false;
        if (status.equals("in_progress") && t.agent.isEmpty()) return false;
        if (status.equals("waiting")) t.waitStart = ts;
        if (t.status.equals("waiting")) t.paused += ts - t.waitStart;
        t.status = status;
        t.history.add(ts + ":" + status);
        return true;
    }

    public String getTicket(int ts, String ticketId) {
        Ticket t = tickets.get(ticketId);
        if (t == null) return "";
        return t.customer + ":" + t.priority + ":" + t.status + ":" + (t.agent.isEmpty() ? "-" : t.agent);
    }

    // ---------------------------------------------------------------- level 2

    public List<String> queue(int ts, String agent) {
        List<Ticket> mine = new ArrayList<>();
        for (Ticket t : tickets.values())
            if (t.agent.equals(agent) && !t.status.equals("resolved")) mine.add(t);
        mine.sort(Comparator.<Ticket>comparingInt(t -> PRIORITY.get(t.priority)).thenComparingInt(t -> t.num));
        List<String> ids = new ArrayList<>();
        for (Ticket t : mine) ids.add(t.id);
        return ids;
    }

    public String autoAssign(int ts, String ticketId) {
        Ticket t = tickets.get(ticketId);
        if (t == null || !t.agent.isEmpty()) return "";
        String agent = pick(ts);
        if (!agent.isEmpty()) put(ts, t, agent);
        return agent;
    }

    // ---------------------------------------------------------------- level 3

    public int dueAt(int ts, String ticketId) {
        Ticket t = tickets.get(ticketId);
        return t == null ? -1 : due(ts, t);
    }

    public List<String> overdue(int ts) {
        List<Ticket> late = new ArrayList<>();
        for (Ticket t : tickets.values())
            if ((t.status.equals("open") || t.status.equals("in_progress")) && ts > due(ts, t)) late.add(t);
        late.sort(Comparator.<Ticket>comparingInt(t -> due(ts, t)).thenComparingInt(t -> t.num));
        List<String> ids = new ArrayList<>();
        for (Ticket t : late) ids.add(t.id);
        return ids;
    }

    // ---------------------------------------------------------------- level 4

    public List<String> endShift(int ts, String agent) {
        boolean other = false;
        for (Map.Entry<String, Boolean> e : agents.entrySet())
            if (e.getValue() && !e.getKey().equals(agent)) other = true;
        if (!agents.getOrDefault(agent, false) || !other) return new ArrayList<>();
        agents.put(agent, false);
        List<String> out = new ArrayList<>();
        for (String id : queue(ts, agent)) {
            String to = pick(ts);
            put(ts, tickets.get(id), to);
            out.add(id + ":" + to);
        }
        return out;
    }

    public boolean startShift(int ts, String agent) {
        Boolean on = agents.get(agent);
        if (on == null || on) return false;
        agents.put(agent, true);
        return true;
    }

    public List<String> history(int ts, String ticketId) {
        Ticket t = tickets.get(ticketId);
        return t == null ? new ArrayList<>() : new ArrayList<>(t.history);
    }
}
