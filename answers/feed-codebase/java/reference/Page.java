import java.util.List;

/** One page of a feed: post ids in order, and the cursor for the next page (null when there is nothing after it). */
public record Page(List<String> postIds, String nextCursor) { }
