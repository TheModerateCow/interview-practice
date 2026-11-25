const DAY = 1440;

export interface Attendee {
  offset: number; // minutes east of UTC: local time = UTC + offset
  workStart: number; // local minute of the day the working hours start
  workEnd: number; // local minute of the day they end (exclusive)
  busy: [number, number][]; // UTC minutes [start, end), any order, may overlap
}

/** Earliest UTC start t with t + duration <= days * 1440 such that at least `quorum`
 *  attendees are free for the whole of [t, t + duration); -1 if there is none. */
export function earliestQuorumSlot(attendees: Attendee[], days: number, duration: number, quorum: number): number {
  throw new Error("not implemented");
}
