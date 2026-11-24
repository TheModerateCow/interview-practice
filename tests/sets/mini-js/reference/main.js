import { readFileSync } from "node:fs";
import { isBalanced } from "./balanced.js";

for (const line of readFileSync(0, "utf8").split("\n")) {
  if (line !== "") console.log(isBalanced(line));
}
