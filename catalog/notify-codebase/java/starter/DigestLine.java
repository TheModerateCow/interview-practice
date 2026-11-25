/** One topic of a digest: how many held notifications it has and the title of the most recent. */
public class DigestLine {
    final String topic;
    int count;
    String latest = "";

    DigestLine(String topic) {
        this.topic = topic;
    }

    public String topic() { return topic; }
    public int count() { return count; }
    public String latest() { return latest; }
}
