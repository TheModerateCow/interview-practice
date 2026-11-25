// Reads a scheduling request from stdin and prints the earliest start (or -1).
// Format (whitespace-separated numbers):
//   n days duration quorum
//   then for each of the n attendees: offset workStart workEnd m, followed by m pairs "start end"
import { readFileSync } from "node:fs";
import { earliestQuorumSlot, type Attendee } from "./scheduler.ts";

const nums = readFileSync(0, "utf8").split(/\s+/).filter(Boolean).map(Number);
let p = 0;
const next = () => nums[p++];
const [n, days, duration, quorum] = [next(), next(), next(), next()];
const attendees: Attendee[] = [];
for (let i = 0; i < n; i++) {
  const offset = next(), workStart = next(), workEnd = next(), m = next();
  const busy: [number, number][] = [];
  for (let j = 0; j < m; j++) busy.push([next(), next()]);
  attendees.push({ offset, workStart, workEnd, busy });
}
console.log(earliestQuorumSlot(attendees, days, duration, quorum));
