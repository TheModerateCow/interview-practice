/** Fixed-window arithmetic and the burst rollover rule. */
final class Window {
    private Window() {}

    /** Start of the fixed window that contains now. Windows are aligned to the epoch, so every key on a plan resets together. */
    static long start(long now, long window) {
        return now - now % window;
    }

    /** Seconds remaining until the window containing now ends. */
    static long resetIn(long now, long window) {
        return start(now, window) + window - now;
    }

    /** Units that carry into a window from the one before it: whatever the key left unused there, up to the plan's burst allowance. */
    static long rollover(Plan p, long prevUsed) {
        long unused = p.limit() - prevUsed;
        return Math.min(unused, p.burst());
    }

    /** Units a key may spend in a window, given what it spent in the window before. */
    static long capacity(Plan p, long prevUsed) {
        return p.limit() + rollover(p, prevUsed);
    }
}
