import { readFileSync } from "node:fs";
import { topK } from "./topk.ts";

const [first, ...rest] = readFileSync(0, "utf8").split("\n");
const words = rest.join(" ").split(/\s+/).filter(Boolean);
console.log(topK(words, Number(first)).join(" "));
