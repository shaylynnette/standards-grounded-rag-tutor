// Run: node --test ts/*.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Index, ask, detectGrade, tokens, type Standard } from "./retrieve.ts";
import { porter } from "./porter.ts";

const idx = new Index(JSON.parse(readFileSync(new URL("./standards.json", import.meta.url), "utf8")) as Standard[]);
const golden = readFileSync(new URL("../eval/golden.jsonl", import.meta.url), "utf8").trim().split("\n").map((l) => JSON.parse(l));

test("porter stems the way SQLite's porter does for our vocabulary", () => {
  assert.equal(porter("fractions"), "fraction");
  assert.equal(porter("rounding"), "round");
  assert.equal(porter("multiplication"), "multipl");
  assert.equal(porter("denominators"), "denomin");
});

test("grade detection", () => {
  assert.equal(detectGrade("fifth grade rounding"), "5");
  assert.equal(detectGrade("grade 3 area"), "3");
  assert.equal(detectGrade("kindergarteners counting"), "K");
  assert.equal(detectGrade("rounding"), null);
});

test("stop words dropped, digits kept", () => {
  assert.deepEqual(tokens("What do third graders learn about 10 by 10?"), ["10", "10"]);
  assert.deepEqual(tokens("what is the"), []);
});

test("held-out test split: correct answer rate and decline rate", () => {
  const rows = golden.filter((g) => g.split === "test");
  const ans = rows.filter((g) => g.expected);
  const no = rows.filter((g) => !g.expected);
  const right = ans.filter((g) => { const a = ask(idx, g.question); return a.answered && g.expected.includes(a.matches[0].teks_code); }).length;
  const declined = no.filter((g) => !ask(idx, g.question).answered).length;
  assert.ok(right / ans.length >= 0.7, `correct ${right}/${ans.length}`);
  assert.equal(declined, no.length);
});

test("citations present and off-topic declines", () => {
  const a = ask(idx, "fifth grade rounding decimals");
  assert.ok(a.answered && a.citations[0].startsWith("19 TAC §111."));
  assert.equal(a.matches[0].teks_code, "5.2C");
  assert.equal(ask(idx, "What is the capital of Texas?").answered, false);
  assert.equal(ask(idx, "").answered, false);
});
