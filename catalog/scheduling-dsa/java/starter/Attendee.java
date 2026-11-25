/**
 * offset: minutes east of UTC (local time = UTC + offset).
 * workStart, workEnd: local minutes of the day, [workStart, workEnd), the same every day.
 * busy: UTC minute blocks {start, end}, [start, end), in any order, may overlap.
 */
public record Attendee(int offset, int workStart, int workEnd, int[][] busy) {}
