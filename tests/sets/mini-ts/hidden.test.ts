import { test } from "node:test";
import assert from "node:assert/strict";
import { topK } from "./topk.ts";

test("test_p1_basic", () => {
  assert.deepEqual(topK(["a", "b", "a", "c", "a", "b"], 2), ["a", "b"]);
});

test("test_p1_tie_alphabetical", () => {
  assert.deepEqual(topK(["pear", "apple", "fig", "pear", "apple", "fig"], 2), ["apple", "fig"]);
});

test("test_p1_k_larger_than_distinct", () => {
  assert.deepEqual(topK(["x", "y", "x"], 10), ["x", "y"]);
});

test("test_p1_zero_and_empty", () => {
  assert.deepEqual(topK(["x"], 0), []);
  assert.deepEqual(topK(["x", "y"], -1), []);
  assert.deepEqual(topK([], 3), []);
});

test("test_p1_case_sensitive", () => {
  assert.deepEqual(topK(["B", "a", "a", "B"], 2), ["B", "a"]);
});
