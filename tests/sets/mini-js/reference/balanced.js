const PAIRS = { ")": "(", "]": "[", "}": "{" };

/** True when every bracket ()[]{} is closed in the right order; other characters are ignored. */
export function isBalanced(s) {
  const st = [];
  for (const c of s) {
    if ("([{".includes(c)) st.push(c);
    else if (c in PAIRS && st.pop() !== PAIRS[c]) return false;
  }
  return st.length === 0;
}
