import { test } from "node:test";
import assert from "node:assert/strict";
import { earliestQuorumSlot as f, type Attendee } from "./scheduler.ts";

const at = (offset: number, workStart: number, workEnd: number, busy: [number, number][] = []): Attendee => ({ offset, workStart, workEnd, busy });

test("test_p1_worked_example", () => {
  const team = [at(0, 540, 1020, [[540, 610], [660, 720]]), at(60, 540, 1020, [[500, 630]]), at(-120, 480, 720)];
  assert.equal(f(team, 1, 60, 2), 630);
});

test("test_p1_east_of_utc_starts_earlier", () => {
  assert.equal(f([at(330, 540, 1020)], 1, 45, 1), 210);
});

test("test_p1_west_of_utc_previous_local_day", () => {
  // local day -1 shows up as UTC [0, 360); busy leaves only 30 minutes of it
  assert.equal(f([at(-600, 480, 1200, [[0, 330]])], 1, 60, 1), 1080);
});

test("test_p1_same_people_for_whole_meeting", () => {
  const three = [at(0, 0, 1440, [[60, 1440]]), at(0, 0, 1440, [[0, 30], [90, 1440]]), at(0, 0, 1440, [[0, 60], [120, 1440]])];
  assert.equal(f(three, 1, 60, 2), -1);
  assert.equal(f(three, 1, 60, 1), 0);
});

test("test_p1_exact_fit", () => {
  assert.equal(f([at(0, 600, 660)], 1, 60, 1), 600);
  assert.equal(f([at(0, 600, 660)], 1, 61, 1), -1);
});

test("test_p1_unsorted_nested_busy_blocks", () => {
  assert.equal(f([at(0, 540, 1020, [[700, 720], [550, 560], [540, 800]])], 1, 60, 1), 800);
});

test("test_p1_busy_block_spans_days", () => {
  assert.equal(f([at(0, 540, 1020, [[500, 2040]])], 2, 400, 1), 2040);
});

test("test_p1_meeting_across_midnight", () => {
  assert.equal(f([at(0, 0, 1440, [[0, 1400]])], 2, 120, 1), 1400);
  assert.equal(f([at(60, 0, 1440, [[0, 1300]])], 2, 200, 1), 1300);
});

test("test_p1_meeting_must_end_inside_horizon", () => {
  assert.equal(f([at(-600, 480, 1200, [[0, 360]])], 1, 360, 1), 1080);
  assert.equal(f([at(-600, 480, 1200, [[0, 360]])], 1, 361, 1), -1);
});

test("test_p1_impossible", () => {
  assert.equal(f([at(0, 540, 1020)], 1, 30, 2), -1);
  assert.equal(f([at(0, 540, 1020), at(0, 540, 1020)], 3, 481, 1), -1);
});

test("test_p1_mixed_time_zones", () => {
  const team = [at(0, 540, 1020, [[600, 720]]), at(60, 480, 960, [[540, 560]]), at(-300, 540, 1020), at(330, 600, 1080, [[300, 420]]), at(540, 540, 1140, [[1000, 1200]])];
  assert.equal(f(team, 2, 30, 3), 420);
  assert.equal(f(team, 2, 30, 4), 560);
  assert.equal(f(team, 2, 90, 3), 420);
  assert.equal(f(team, 2, 30, 5), -1);
});

test("test_p1_large_org", () => {
  let seed = 12345;
  const rnd = (n: number) => { seed = (seed * 1103515245 + 12345) % 2147483648; return Math.floor(seed / 65536) % n; };
  const big: Attendee[] = [];
  for (let i = 0; i < 1000; i++) {
    const ws = 420 + rnd(180), we = ws + 420 + rnd(180);
    const busy: [number, number][] = [];
    for (let j = 0; j < 200; j++) { const s = rnd(30 * 1440 - 60); busy.push([s, s + 15 + rnd(180)]); }
    big.push(at(-300 + 15 * rnd(41), ws, we, busy));
  }
  const t0 = performance.now();
  assert.equal(f(big, 30, 45, 500), 33618);
  assert.equal(f(big, 30, 45, 800), -1);
  assert.ok(performance.now() - t0 < 2000, "too slow: aim for about O(N log N) in the total number of busy blocks");
});
