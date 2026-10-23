// Run: node ts/parity.ts   Compares the TypeScript port with the Python reference on the golden set.
import { readFileSync } from "node:fs";
import { Index, canAnswer, type Standard } from "./retrieve.ts";

const idx = new Index(JSON.parse(readFileSync(new URL("./standards.json", import.meta.url), "utf8")) as Standard[]);
const golden = readFileSync(new URL("../eval/golden.jsonl", import.meta.url), "utf8").trim().split("\n").map((l) => JSON.parse(l));
const out = golden.map((g) => {
  const { hits } = idx.search(g.question, 5);
  return { id: g.id, codes: hits.map((h) => h.teks_code), answered: canAnswer(hits), score: hits[0]?.score ?? 0 };
});
const phr = readFileSync(new URL("../eval/phrasing.jsonl", import.meta.url), "utf8").trim().split("\n").map((l) => JSON.parse(l));
const phrasing = phr.map((p) => { const r = idx.search(p.q, 5); return { q: p.q, codes: r.hits.map((h) => h.teks_code), grade: r.understood.grade, code: r.understood.code }; });
console.log(JSON.stringify({ golden: out, phrasing }));
