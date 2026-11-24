import { test } from "node:test";
import assert from "node:assert/strict";
import { isBalanced } from "./balanced.js";

test("test_p1_simple", () => {
  assert.equal(isBalanced("()[]{}"), true);
  assert.equal(isBalanced(""), true);
});

test("test_p1_nested", () => {
  assert.equal(isBalanced("{[()]}"), true);
  assert.equal(isBalanced("{[(])}"), false);
});

test("test_p1_unclosed_and_extra", () => {
  assert.equal(isBalanced("(("), false);
  assert.equal(isBalanced("())"), false);
  assert.equal(isBalanced("]"), false);
});

test("test_p1_ignores_other_chars", () => {
  assert.equal(isBalanced("a(b[c]d)e"), true);
  assert.equal(isBalanced("a(b]"), false);
});

test("test_p1_wrong_type", () => {
  assert.equal(isBalanced("(]"), false);
  assert.equal(isBalanced("[)"), false);
});
