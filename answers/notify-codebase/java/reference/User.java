import java.util.ArrayList;
import java.util.List;

/** A user's notification settings. */
public class User {
    public final String id;
    public final int offsetMin; // minutes east of UTC; fixed, no daylight saving
    public List<String> channels = new ArrayList<>(List.of(Notify.EMAIL)); // enabled, in the user's order
    public int quietFrom; // local hour quiet hours start (0-23)
    public int quietTo; // local hour quiet hours end, exclusive; equal to quietFrom means none

    public User(String id, int offsetMin) {
        this.id = id;
        this.offsetMin = offsetMin;
    }

    public String id() { return id; }
    public int offsetMin() { return offsetMin; }
    public List<String> channels() { return channels; }
    public int quietFrom() { return quietFrom; }
    public int quietTo() { return quietTo; }
}
