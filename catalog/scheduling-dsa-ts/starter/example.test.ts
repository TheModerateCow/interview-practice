// An example to copy. Run your tests with the My tests button.
import { test } from "node:test";
import assert from "node:assert/strict";
import { earliestQuorumSlot } from "./scheduler.ts";

test("one attendee in UTC with a free calendar", () => {
  const alex = { offset: 0, workStart: 540, workEnd: 1020, busy: [] as [number, number][] };
  assert.equal(earliestQuorumSlot([alex], 1, 30, 1), 540);
});
