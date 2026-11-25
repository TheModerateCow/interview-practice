def run_book(events):
    """Replay ask-book events in order.

    events: tuples ("add", price, qty), ("cancel", price, qty), ("quote", qty) or ("buy", qty).
    Returns one int per "quote" and "buy" event, in order (see problem.md).
    """
    raise NotImplementedError
