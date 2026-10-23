// Run: node ts/parity.ts   Compares the TypeScript port with the Python reference on the golden set.
import { readFileSync } from "node:fs";
import { Index, canAnswer, type Standard } from "./retrieve.ts";

const idx = new Index(JSON.parse(readFileSync(new URL("./standards.json", import.meta.url), "utf8")) as Standard[]);
const golden = readFileSync(new URL("../eval/golden.jsonl", import.meta.url), "utf8").trim().split("\n").map((l) => JSON.parse(l));
const out = golden.map((g) => {
  const { hits } = idx.search(g.question, 5);
  return { id: g.id, codes: hits.map((h) => h.teks_code), answered: canAnswer(hits), score: hits[0]?.score ?? 0 };
});
console.log(JSON.stringify(out));
