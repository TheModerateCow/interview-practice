/** One request the limiter decided on: seconds since the epoch, the units it asked for, and the verdict. */
public record Event(long at, long cost, boolean allowed) {}
