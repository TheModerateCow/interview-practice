import java.util.List;

/** What happened to a notification; channels are the ones it went out on, in the user's order. */
public record Result(String status, List<String> channels) {}
