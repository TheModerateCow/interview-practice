/**
 * One line of a replenishment plan. {@code position} is available plus inbound when the plan was made,
 * {@code qty} how much to bring in, {@code from} the warehouse to transfer from or "" to buy from the supplier.
 */
public record Suggestion(String sku, int position, int qty, String from) {}
