import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** A card issuer's authorisation service: cards with credit limits, holds that are captured, voided or expire, refunds and statements, per-category daily limits and frozen cards. Every method takes day first: today's date as an integer. */
public class Issuer {
    private static final int HOLD_DAYS = 7;

    private static final class Card {
        final int limit;
        boolean frozen;
        final Map<String, Integer> catLimits = new HashMap<>();
        final List<String> entries = new ArrayList<>();
        Card(int limit) { this.limit = limit; }
    }

    private static final class Auth {
        final String id, card, category;
        final int amount, day;
        String status = "open"; // open, captured, voided
        int captured, refunded;
        Auth(String id, String card, String category, int amount, int day) {
            this.id = id; this.card = card; this.category = category; this.amount = amount; this.day = day;
        }
    }

    private final Map<String, Card> cards = new HashMap<>();
    private final Map<String, Auth> auths = new LinkedHashMap<>(); // in approval (id) order

    public Issuer() {}

    /** open, captured, voided or expired: an open hold expires HOLD_DAYS days after approval. */
    private static String status(int day, Auth a) {
        if (a.status.equals("open") && day >= a.day + HOLD_DAYS) return "expired";
        return a.status;
    }

    private int held(int day, String cardId) {
        int total = 0;
        for (Auth a : auths.values())
            if (a.card.equals(cardId) && status(day, a).equals("open")) total += a.amount;
        return total;
    }

    private int posted(String cardId) {
        int total = 0;
        for (Auth a : auths.values())
            if (a.card.equals(cardId)) total += a.captured - a.refunded;
        return total;
    }

    /** Today's spending in a category: open holds at their amount, captures at what was captured. */
    private int spent(int day, String cardId, String category) {
        int total = 0;
        for (Auth a : auths.values()) {
            if (!a.card.equals(cardId) || !a.category.equals(category) || a.day != day) continue;
            String s = status(day, a);
            if (s.equals("open")) total += a.amount;
            else if (s.equals("captured")) total += a.captured;
        }
        return total;
    }

    // ---------------------------------------------------------------- level 1

    public boolean issueCard(int day, String cardId, int limit) {
        if (cards.containsKey(cardId) || limit <= 0) return false;
        cards.put(cardId, new Card(limit));
        return true;
    }

    public String authorize(int day, String cardId, String category, int amount) {
        Card c = cards.get(cardId);
        if (c == null || c.frozen || amount <= 0 || amount > available(day, cardId)) return "";
        Integer lim = c.catLimits.get(category);
        if (lim != null && spent(day, cardId, category) + amount > lim) return "";
        String id = "a" + (auths.size() + 1);
        auths.put(id, new Auth(id, cardId, category, amount, day));
        return id;
    }

    public boolean capture(int day, String authId, int amount) {
        Auth a = auths.get(authId);
        if (a == null || !status(day, a).equals("open") || amount <= 0 || amount > a.amount) return false;
        a.status = "captured";
        a.captured = amount;
        cards.get(a.card).entries.add(day + ":" + authId + ":charge:" + amount);
        return true;
    }

    public boolean voidAuth(int day, String authId) {
        Auth a = auths.get(authId);
        if (a == null || !status(day, a).equals("open")) return false;
        a.status = "voided";
        return true;
    }

    public int available(int day, String cardId) {
        Card c = cards.get(cardId);
        if (c == null) return -1;
        return c.limit - posted(cardId) - held(day, cardId);
    }

    // ---------------------------------------------------------------- level 2

    public List<String> holds(int day, String cardId) {
        List<String> out = new ArrayList<>();
        for (Auth a : auths.values())
            if (a.card.equals(cardId) && status(day, a).equals("open")) out.add(a.id + ":" + a.amount);
        return out;
    }

    public String authStatus(int day, String authId) {
        Auth a = auths.get(authId);
        return a == null ? "" : status(day, a);
    }

    // ---------------------------------------------------------------- level 3

    public boolean refund(int day, String authId, int amount) {
        Auth a = auths.get(authId);
        if (a == null || !a.status.equals("captured") || amount <= 0 || amount > a.captured - a.refunded) return false;
        a.refunded += amount;
        cards.get(a.card).entries.add(day + ":" + authId + ":refund:" + amount);
        return true;
    }

    public int balance(int day, String cardId) {
        return cards.containsKey(cardId) ? posted(cardId) : -1;
    }

    public List<String> statement(int day, String cardId) {
        Card c = cards.get(cardId);
        return c == null ? new ArrayList<>() : new ArrayList<>(c.entries);
    }

    // ---------------------------------------------------------------- level 4

    public boolean setCategoryLimit(int day, String cardId, String category, int limit) {
        Card c = cards.get(cardId);
        if (c == null || limit < 0) return false;
        c.catLimits.put(category, limit);
        return true;
    }

    public boolean freeze(int day, String cardId) {
        Card c = cards.get(cardId);
        if (c == null || c.frozen) return false;
        c.frozen = true;
        return true;
    }

    public boolean unfreeze(int day, String cardId) {
        Card c = cards.get(cardId);
        if (c == null || !c.frozen) return false;
        c.frozen = false;
        return true;
    }
}
